#!/usr/bin/env python3
"""Deterministic final-page checks for dev-csv-health-001."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--network-mode", choices=("online", "offline"), default="online")
    args = parser.parse_args()

    result: dict[str, object] = {
        "case_id": "dev-csv-health-001",
        "checks": [],
        "failures": [],
        "interpretation_warnings": [],
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        parsed = urlsplit(args.url)
        allowed_origin = f"{parsed.scheme}://{parsed.netloc}"
        blocked_external: list[str] = []
        def restrict_network(route, request) -> None:
            if request.url.startswith(allowed_origin) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                blocked_external.append(request.url)
                route.abort("blockedbyclient")

        if args.network_mode == "offline":
            page.route("**/*", restrict_network)
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        opened = response is not None and response.status == 200
        result["checks"].append({"name": "page-opens", "passed": opened})
        if not opened:
            result["failures"].append("Dashboard did not return HTTP 200")

        body = page.locator("body").inner_text()
        result["network_mode"] = args.network_mode
        result["blocked_external_requests"] = sorted(set(blocked_external))
        source_passed = "synthetic Bihar ANC fixture".lower() in body.lower()
        result["checks"].append({"name": "source-label", "passed": source_passed})
        if not source_passed:
            result["failures"].append("Synthetic Bihar ANC fixture label is not visible")

        year_control = page.locator("select").filter(
            has=page.locator("option[value='2021']")
        ).first
        expected_by_year = {
            "2021": {"Gaya": 66.0, "Nalanda": 73.0},
            "2023": {"Gaya": 74.0, "Nalanda": 80.0},
        }
        for year, expected in expected_by_year.items():
            if year_control.count() == 1:
                year_control.select_option(year, force=True)
                page.wait_for_timeout(200)
            else:
                year_button = page.get_by_role(
                    "button", name=re.compile(rf"^\s*{year}\s*$")
                ).first
                if year_button.count() == 1:
                    year_button.click(force=True)
                    page.wait_for_timeout(200)
            year_body = page.locator("body").inner_text()
            passed = all(
                re.search(
                    rf"{re.escape(district)}[\s\S]{{0,1200}}{value:g}(?:\.0+)?\s*%",
                    year_body,
                    re.I,
                )
                is not None
                for district, value in expected.items()
            )
            result["checks"].append({"name": f"year-{year}-control-values", "passed": passed})
            if not passed:
                result["failures"].append(
                    f"Year {year} control does not show the expected Gaya/Nalanda rates"
                )

        if year_control.count() == 1:
            year_control.select_option("2023", force=True)
            page.wait_for_timeout(200)
        body = page.locator("body").inner_text()

        pp_checks = {
            "Gaya": re.compile(r"Gaya[\s\S]{0,600}(?:\+?8(?:\.0+)?\s*(?:pp|percentage point))", re.I),
            "Nalanda": re.compile(r"Nalanda[\s\S]{0,600}(?:\+?7(?:\.0+)?\s*(?:pp|percentage point))", re.I),
        }
        for district, pattern in pp_checks.items():
            passed = bool(pattern.search(body))
            result["checks"].append(
                {"name": f"{district.lower()}-percentage-point-change", "passed": passed}
            )
            if not passed:
                result["failures"].append(
                    f"Final page does not show {district}'s change in percentage points"
                )

        visible_2020 = len(re.findall(r"\b2020\b", body))
        result["visible_2020_mentions"] = visible_2020
        result["checks"].append({"name": "2020-not-visible", "passed": visible_2020 == 0})
        if visible_2020:
            result["failures"].append("2020 remains visible after filtering to 2021-2023")

        download_control = page.get_by_role(
            "button",
            name=re.compile(
                r"(?:download|export).*(?:csv|table)|(?:csv|table).*(?:download|export)",
                re.I,
            ),
        ).first
        download_passed = False
        download_preview = ""
        download_rows: list[dict[str, str]] = []
        if download_control.count() == 1:
            try:
                with page.expect_download(timeout=5_000) as download_info:
                    download_control.click()
                saved_path = download_info.value.path()
                if saved_path:
                    download_preview = Path(saved_path).read_text()
                    download_rows = list(csv.DictReader(io.StringIO(download_preview)))
                    years = {row.get("year", "") for row in download_rows}
                    districts = {row.get("district", "") for row in download_rows}
                    download_passed = (
                        len(download_rows) == 6
                        and years == {"2021", "2022", "2023"}
                        and districts == {"Gaya", "Nalanda"}
                    )
            except Exception as error:
                result["download_error"] = f"{type(error).__name__}: {error}"
        result["checks"].append(
            {"name": "page-download-filtered-comparison", "passed": download_passed}
        )
        result["download_preview"] = download_preview[:1000]

        artifact_candidates: list[dict[str, object]] = []
        artifact_passed = False
        expected_rates = {
            "Gaya": {"2021": "66.0", "2022": "69.0", "2023": "74.0"},
            "Nalanda": {"2021": "73.0", "2022": "77.0", "2023": "80.0"},
        }
        if args.workspace:
            for path in sorted(args.workspace.glob("*.csv")):
                if path.name == "anc4_coverage.csv":
                    continue
                try:
                    text = path.read_text()
                    rows = list(csv.DictReader(io.StringIO(text)))
                    fields = [field or "" for field in (rows[0].keys() if rows else [])]
                    lower = {field.lower(): field for field in fields}
                    shape = "unrecognised"
                    passed = False
                    if "district" in lower and "year" in lower:
                        shape = "long"
                        passed = all(
                            any(
                                row.get(lower["district"]) == district
                                and row.get(lower["year"]) == year
                                and any(rate in str(value) for value in row.values())
                                for row in rows
                            )
                            for district, years in expected_rates.items()
                            for year, rate in years.items()
                        )
                    elif "district" in lower:
                        shape = "wide-by-district"
                        passed = all(
                            any(
                                row.get(lower["district"]) == district
                                and all(
                                    any(year in field and "rate" in field.lower() and rate in str(row.get(field))
                                        for field in fields)
                                    for year, rate in years.items()
                                )
                                for row in rows
                            )
                            for district, years in expected_rates.items()
                        )
                    elif "year" in lower:
                        shape = "wide-by-year"
                        passed = all(
                            any(
                                row.get(lower["year"]) == year
                                and all(
                                    any(district.lower() in field.lower() and "rate" in field.lower()
                                        and rate in str(row.get(field)) for field in fields)
                                    for district, rate in ((name, values[year]) for name, values in expected_rates.items())
                                )
                                for row in rows
                            )
                            for year in ("2021", "2022", "2023")
                        )
                    artifact_candidates.append(
                        {"file": path.name, "shape": shape, "passed": passed, "preview": text[:500]}
                    )
                    artifact_passed = artifact_passed or passed
                except Exception as error:
                    artifact_candidates.append(
                        {"file": path.name, "passed": False, "error": f"{type(error).__name__}: {error}"}
                    )
        result["artifact_download_candidates"] = artifact_candidates
        delivered_download = download_passed or artifact_passed
        result["checks"].append(
            {"name": "correct-comparison-download-delivered", "passed": delivered_download}
        )
        if not delivered_download:
            result["failures"].append(
                "No delivered CSV preserves all six Gaya/Nalanda observations for 2021-2023"
            )
        elif artifact_passed and not download_passed:
            result["interpretation_warnings"].append(
                "A correct CSV artifact was delivered through the conversation, but the page's own download did not export the requested final comparison"
            )

        unsupported_bands = [
            pattern
            for pattern in (
                r"High\s*(?:\(|:)?\s*(?:≥|>=)\s*\d+\s*%",
                r"Moderate\s*(?:\(|:)?\s*\d+\s*[-–]\s*\d+\s*%",
                r"(?:Focus|Priority)\s*(?:\(|:)?\s*(?:<|≤|<=)\s*\d+\s*%",
                r"(?:≥|>=)\s*\d+\s*%\s*High",
                r"\d+\s*[-–]\s*\d+\s*%\s*(?:Mod|Moderate)",
                r"(?:<|≤|<=)\s*\d+\s*%\s*(?:Low|Focus)",
                r"Benchmark\s*:\s*\d+\s*%?\s*\+",
                r"Needs\s+Focus\s*/\s*Priority",
            )
            if re.search(pattern, body, re.IGNORECASE)
        ]
        result["unsupported_performance_band_patterns"] = unsupported_bands
        if unsupported_bands:
            result["interpretation_warnings"].append(
                "Page adds performance bands that the supplied file does not define"
            )

        page.set_viewport_size({"width": 390, "height": 844})
        page_width = page.evaluate(
            "() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})"
        )
        no_page_overflow = page_width["scroll"] <= page_width["client"] + 1
        result["narrow_page_width"] = page_width
        result["checks"].append(
            {"name": "no-narrow-page-overflow", "passed": no_page_overflow}
        )
        if not no_page_overflow:
            result["failures"].append(
                f"Narrow page is {page_width['scroll'] - page_width['client']} px wider than the viewport"
            )
        browser.close()

    result["passed"] = not result["failures"]
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
