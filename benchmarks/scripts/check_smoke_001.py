#!/usr/bin/env python3
"""Deterministic browser checks for the smoke-001 dashboard."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


EXPECTED = {
    "2022": {"Gaya": "78.0%", "Nalanda": "85.0%", "Purnia": "70.0%"},
    "2023": {"Gaya": "85.0%", "Nalanda": "90.0%", "Purnia": "76.0%"},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--expect-download", action="store_true")
    parser.add_argument(
        "--phase",
        choices=("turn-1", "final"),
        default="final",
        help="turn-1 requires both year controls; final evaluates the requested 2023 view",
    )
    args = parser.parse_args()

    result: dict[str, object] = {
        "case_id": "smoke-001",
        "checks": [],
        "failures": [],
        "interpretation_warnings": [],
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(args.url, wait_until="networkidle", timeout=30_000)

        year_select = page.locator("select").filter(
            has=page.locator("option[value='2022']")
        ).first
        result["year_selector_found"] = year_select.count() == 1
        if args.phase == "turn-1" and not result["year_selector_found"]:
            result["failures"].append("No year selector with a 2022 option was found")

        expected_years = ("2023", "2022") if args.phase == "turn-1" else ("2023",)
        for year in expected_years:
            expected = EXPECTED[year]
            if args.phase == "turn-1" and not result["year_selector_found"]:
                result["checks"].append({"name": f"year-{year}-values", "passed": False})
                continue
            # Some dashboards expose year buttons on desktop and retain the
            # equivalent select only for narrow screens. Force the semantic
            # control so the check remains independent of that layout choice.
            if result["year_selector_found"]:
                year_select.select_option(year, force=True)
                page.wait_for_timeout(250)
            row_texts = page.locator("table tbody tr:visible").all_inner_texts()
            passed = all(
                any(district in row and value in row for row in row_texts)
                for district, value in expected.items()
            )
            result["checks"].append({"name": f"year-{year}-values", "passed": passed})
            if not passed:
                result["failures"].append(
                    f"Expected district coverage values were not visible in table rows for {year}"
                )

        body = page.locator("body").inner_text()
        source_passed = "synthetic smoke fixture" in body
        result["checks"].append({"name": "source-label", "passed": source_passed})
        if not source_passed:
            result["failures"].append("Synthetic source label was not visible")

        if args.phase == "final":
            result["visible_2022_mentions"] = len(re.findall(r"\b2022\b", body))
            if result["visible_2022_mentions"]:
                result["interpretation_warnings"].append(
                    "The final page still visibly discusses 2022 after the request to show only 2023"
                )
            unsupported_bands = [
                pattern
                for pattern in (r"High\s*\(≥?85%", r"Moderate\s*\(75[-–]84%", r"Priority\s*\(<75%")
                if re.search(pattern, body, re.IGNORECASE)
            ]
            result["unsupported_performance_band_patterns"] = unsupported_bands
            if unsupported_bands:
                result["interpretation_warnings"].append(
                    "The page adds performance bands that are not defined in the supplied fixture"
                )

        if args.expect_download:
            if result["year_selector_found"]:
                year_select.select_option("2023", force=True)
                page.wait_for_timeout(250)
            download_control = page.get_by_role(
                "button", name=re.compile(r"download.*csv", re.IGNORECASE)
            ).first
            download_passed = False
            download_text = ""
            if download_control.count() == 1:
                with page.expect_download(timeout=5_000) as download_info:
                    download_control.click()
                download = download_info.value
                saved_path = download.path()
                if saved_path:
                    download_text = Path(saved_path).read_text()
                    download_passed = (
                        all(district in download_text for district in EXPECTED["2023"])
                        and "2023" in download_text
                        and "2022" not in download_text
                    )
            result["checks"].append({"name": "download-2023-table", "passed": download_passed})
            result["download_preview"] = download_text[:500]
            if not download_passed:
                result["failures"].append("A correct 2023 CSV download was not produced")

        page.set_viewport_size({"width": 390, "height": 844})
        overflow = page.evaluate(
            """() => [...document.querySelectorAll('body *')]
              .filter(el => {
                const rect = el.getBoundingClientRect();
                return rect.right > window.innerWidth + 1 || rect.left < -1;
              })
              .map(el => ({tag: el.tagName, id: el.id || null, right: Math.round(el.getBoundingClientRect().right)}))
              .slice(0, 20)"""
        )
        page_width = page.evaluate(
            "() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})"
        )
        no_page_overflow = page_width["scroll"] <= page_width["client"] + 1
        result["narrow_page_width"] = page_width
        result["narrow_overflow_elements"] = overflow
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
