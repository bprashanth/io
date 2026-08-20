#!/usr/bin/env python3
"""Deterministic final-page checks for dev-pdf-health-001."""

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
    "Purnia": {"2022": 61.0, "2023": 66.0},
    "Kishanganj": {"2022": 56.0, "2023": 60.0},
}


def artifact_ok(path: Path) -> bool:
    text = path.read_text(errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    normalized = "\n".join(
        " | ".join(f"{key}={value}" for key, value in row.items()) for row in rows
    )
    observations = all(
        district.lower() in normalized.lower()
        and year in normalized
        and re.search(rf"(?<!\d){value:g}(?:\.0+)?(?:%|\b)", normalized)
        for district, years in EXPECTED.items()
        for year, value in years.items()
    )
    source_page = re.search(r"(?:page|source_page)[^\n|=]*[= :]+2\b", normalized, re.I)
    return observations and source_page is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--network-mode", choices=("online", "offline"), default="online")
    args = parser.parse_args()
    result: dict[str, object] = {
        "case_id": "dev-pdf-health-001",
        "network_mode": args.network_mode,
        "checks": [],
        "failures": [],
    }

    def check(name: str, passed: bool, failure: str) -> None:
        result["checks"].append({"name": name, "passed": passed})
        if not passed:
            result["failures"].append(failure)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        parsed = urlsplit(args.url)
        allowed = f"{parsed.scheme}://{parsed.netloc}"
        blocked: list[str] = []

        def route_request(route, request) -> None:
            if request.url.startswith(allowed) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                blocked.append(request.url)
                route.abort("blockedbyclient")

        if args.network_mode == "offline":
            page.route("**/*", route_request)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        check("page-opens", bool(response and response.status == 200), "Dashboard did not return HTTP 200")
        body = page.locator("body").inner_text()
        check(
            "source-label",
            "synthetic facility-delivery pdf fixture" in body.lower(),
            "Synthetic PDF source label is not visible",
        )
        check(
            "page-and-table-citation",
            re.search(r"page\s*2", body, re.I) is not None and re.search(r"table\s*1", body, re.I) is not None,
            "Page 2 and Table 1 are not both visibly cited",
        )

        for year in ("2022", "2023"):
            selected = False
            button = page.get_by_role("button", name=re.compile(rf"^\s*(?:Year\s*)?{year}\s*$", re.I)).first
            if button.count() == 1:
                button.click(force=True)
                selected = True
            if not selected:
                for index in range(page.locator("select").count()):
                    select = page.locator("select").nth(index)
                    label = (select.get_attribute("aria-label") or "") + " " + (select.get_attribute("id") or "")
                    if re.search(r"year", label, re.I) and not re.search(r"compare", label, re.I) and select.locator(f"option[value='{year}']").count():
                        select.select_option(year, force=True)
                        selected = True
                        break
            page.wait_for_timeout(200)
            year_body = page.locator("body").inner_text()
            passed = all(
                re.search(
                    rf"{district}[\s\S]{{0,1200}}{values[year]:g}(?:\.0+)?\s*%",
                    year_body,
                    re.I,
                )
                for district, values in EXPECTED.items()
            )
            check(
                f"{year}-control-values",
                passed,
                f"Year {year} view does not expose expected Purnia/Kishanganj values",
            )

        body = page.locator("body").inner_text()
        selectable_2021 = page.get_by_role("button", name=re.compile(r"^\s*(?:Year\s*)?2021\s*$", re.I)).count() > 0
        selectable_2021 = selectable_2021 or any(
            page.locator("select").nth(index).locator("option[value='2021']").count() > 0
            for index in range(page.locator("select").count())
        )
        check("2021-not-selectable", not selectable_2021, "2021 remains selectable after the 2022-2023 filter")

        candidates: list[dict[str, object]] = []
        delivered = False
        artifact_gap = False
        if args.workspace:
            for path in sorted(args.workspace.glob("*.csv")):
                passed = artifact_ok(path)
                artifact_text = path.read_text(errors="replace")
                artifact_gap = artifact_gap or (
                    re.search(r"difference[^\n]*2023[^\n]*6(?:\.0+)?", artifact_text, re.I) is not None
                )
                candidates.append({"file": path.name, "passed": passed, "preview": artifact_text[:600]})
                delivered = delivered or passed
        result["artifact_download_candidates"] = candidates
        gap_ok = re.search(
            r"(?:Purnia[\s\S]{0,700}Kishanganj|Kishanganj[\s\S]{0,700}Purnia)[\s\S]{0,700}\b6(?:\.0+)?\s*(?:pp|pts?|percentage point)",
            body,
            re.I,
        ) is not None or artifact_gap
        check("2023-six-point-gap", gap_ok, "Neither the final page nor delivered comparison shows the six-point 2023 gap")
        check(
            "correct-comparison-download-delivered",
            delivered,
            "No delivered CSV preserves all four observations and source page 2",
        )

        page.set_viewport_size({"width": 390, "height": 844})
        width = page.evaluate("() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})")
        result["narrow_page_width"] = width
        check(
            "no-narrow-page-overflow",
            width["scroll"] <= width["client"] + 1,
            f"Narrow page is {width['scroll'] - width['client']} px wider than the viewport",
        )
        result["page_errors"] = errors
        result["blocked_external_requests"] = sorted(set(blocked))
        if errors:
            result["failures"].append("Browser page errors occurred")
        browser.close()

    result["passed"] = not result["failures"]
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
