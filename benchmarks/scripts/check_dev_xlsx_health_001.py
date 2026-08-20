#!/usr/bin/env python3
"""Deterministic final-page checks for dev-xlsx-health-001."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


EXPECTED = {
    "Gaya": {"2022": 63.0, "2023": 68.0},
    "Nalanda": {"2022": 72.0, "2023": 75.0},
}


def number_near(text: str, label: str, number: float, distance: int = 1200) -> bool:
    return re.search(
        rf"{re.escape(label)}[\s\S]{{0,{distance}}}{number:g}(?:\.0+)?\s*%",
        text,
        re.I,
    ) is not None


def artifact_has_observations(path: Path) -> bool:
    text = path.read_text(errors="replace")
    if not all(year in text for year in ("2022", "2023")):
        return False
    return all(
        re.search(
            rf"^{district},[^\n]*{years['2022']:g}(?:\.0+)?[^\n]*{years['2023']:g}(?:\.0+)?",
            text,
            re.I | re.M,
        )
        or all(
            re.search(
                rf"{district}[^\n]*{year}[^\n]*{value:g}(?:\.0+)?",
                text,
                re.I,
            )
            for year, value in years.items()
        )
        for district, years in EXPECTED.items()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--network-mode", choices=("online", "offline"), default="online")
    args = parser.parse_args()
    result: dict[str, object] = {
        "case_id": "dev-xlsx-health-001",
        "network_mode": args.network_mode,
        "checks": [],
        "failures": [],
        "interpretation_warnings": [],
    }

    def check(name: str, passed: bool, failure: str) -> None:
        result["checks"].append({"name": name, "passed": passed})
        if not passed:
            result["failures"].append(failure)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        allowed = f"{urlsplit(args.url).scheme}://{urlsplit(args.url).netloc}"
        blocked: list[str] = []

        def route_request(route, request) -> None:
            if request.url.startswith(allowed) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                blocked.append(request.url)
                route.abort("blockedbyclient")

        if args.network_mode == "offline":
            page.route("**/*", route_request)
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        check("page-opens", bool(response and response.status == 200), "Dashboard did not return HTTP 200")
        body = page.locator("body").inner_text()
        source_ok = "synthetic maternal-health workbook fixture" in body.lower()
        check("source-label", source_ok, "Synthetic workbook source label is not visible")
        sheets_ok = "district data" in body.lower() and "indicator notes" in body.lower()
        check("source-sheets", sheets_ok, "Both workbook source-sheet names are not visible")

        for select_index in range(page.locator("select").count()):
            select = page.locator("select").nth(select_index)
            options = select.locator("option")
            for option_index in range(options.count()):
                option = options.nth(option_index)
                if "postnatal" in option.inner_text().lower():
                    select.select_option(option.get_attribute("value"), force=True)
                    page.wait_for_timeout(150)
                    break
        postnatal_button = page.get_by_role("button", name=re.compile("postnatal", re.I)).first
        if postnatal_button.count() == 1:
            postnatal_button.click(force=True)
            page.wait_for_timeout(150)

        for year in ("2022", "2023"):
            selected = False
            for select_index in range(page.locator("select").count()):
                select = page.locator("select").nth(select_index)
                if select.locator(f"option[value='{year}']").count():
                    select.select_option(year, force=True)
                    selected = True
                    break
            if not selected:
                button = page.get_by_role("button", name=re.compile(rf"^\s*(?:Year\s*)?{year}\s*$", re.I)).first
                if button.count() == 1:
                    button.click(force=True)
            page.wait_for_timeout(200)
            year_body = page.locator("body").inner_text()
            passed = all(number_near(year_body, district, values[year]) for district, values in EXPECTED.items())
            check(
                f"postnatal-{year}-control-values",
                passed,
                f"Postnatal {year} view does not expose expected Gaya/Nalanda values",
            )

        body = page.locator("body").inner_text()
        check("2021-not-visible", not re.search(r"\b2021\b", body), "2021 remains visible after 2022-2023 filter")
        for district, change in (("Gaya", 5.0), ("Nalanda", 3.0)):
            passed = re.search(
                rf"{district}[\s\S]{{0,700}}\+?{change:g}(?:\.0+)?\s*(?:pp|pts?|percentage point)",
                body,
                re.I,
            ) is not None
            check(
                f"{district.lower()}-change",
                passed,
                f"Final page does not show {district}'s 2022-2023 percentage-point change",
            )

        # Restore the multi-year comparison before exercising the download.
        # Earlier checks intentionally leave the page on 2023.
        for select_index in range(page.locator("select").count()):
            select = page.locator("select").nth(select_index)
            options = select.locator("option")
            for option_index in range(options.count()):
                option = options.nth(option_index)
                if "all years" in option.inner_text().lower():
                    select.select_option(option.get_attribute("value"), force=True)
                    page.wait_for_timeout(150)
                    break

        candidates: list[dict[str, object]] = []
        artifact_ok = False
        download_button = page.get_by_role(
            "button", name=re.compile(r"download.*csv|csv.*download", re.I)
        ).first
        if download_button.count() == 1:
            try:
                with page.expect_download(timeout=5_000) as download_info:
                    download_button.click(force=True)
                download_path = download_info.value.path()
                if download_path:
                    downloaded = Path(download_path)
                    passed = artifact_has_observations(downloaded)
                    candidates.append(
                        {
                            "file": download_info.value.suggested_filename,
                            "origin": "page-download",
                            "passed": passed,
                            "preview": downloaded.read_text(errors="replace")[:600],
                        }
                    )
                    artifact_ok = artifact_ok or passed
            except Exception as error:
                result["page_download_error"] = f"{type(error).__name__}: {error}"
        if args.workspace:
            for path in sorted(args.workspace.glob("*.csv")):
                passed = artifact_has_observations(path)
                candidates.append({"file": path.name, "passed": passed, "preview": path.read_text(errors="replace")[:600]})
                artifact_ok = artifact_ok or passed
        result["artifact_download_candidates"] = candidates
        check(
            "correct-comparison-download-delivered",
            artifact_ok,
            "No delivered CSV preserves all four Gaya/Nalanda postnatal observations for 2022-2023",
        )

        page.set_viewport_size({"width": 390, "height": 844})
        width = page.evaluate("() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})")
        result["narrow_page_width"] = width
        check(
            "no-narrow-page-overflow",
            width["scroll"] <= width["client"] + 1,
            f"Narrow page is {width['scroll'] - width['client']} px wider than the viewport",
        )
        result["page_errors"] = page_errors
        result["blocked_external_requests"] = sorted(set(blocked))
        if page_errors:
            result["failures"].append("Browser page errors occurred")
        browser.close()

    result["passed"] = not result["failures"]
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
