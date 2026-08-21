#!/usr/bin/env python3
"""Inspect the rescued Antigravity side-by-side workbook dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    origin = f"{urlsplit(args.url).scheme}://{urlsplit(args.url).netloc}"
    result: dict[str, object] = {"case_id": "dev-xlsx-regions-002", "surface": "Antigravity rescued final workspace"}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        console: list[dict[str, str]] = []
        page_errors: list[str] = []
        requests: list[str] = []
        page.on("console", lambda message: console.append({"type": message.type, "text": message.text}))
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(300)
        body = page.locator("body").inner_text()
        page.screenshot(path=args.output / "desktop-final-online.png", full_page=True)
        width = page.evaluate("() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})")
        with page.expect_download(timeout=5_000) as info:
            page.locator("#exportCsvBtn").click()
        csv_download = info.value
        csv_path = args.output / csv_download.suggested_filename
        csv_download.save_as(csv_path)
        with page.expect_download(timeout=5_000) as info:
            page.locator("#downloadExcelBtn").click()
        xlsx_download = info.value
        xlsx_path = args.output / xlsx_download.suggested_filename
        xlsx_download.save_as(xlsx_path)

        offline = browser.new_page(viewport={"width": 1440, "height": 1000})
        blocked: list[str] = []
        offline_errors: list[str] = []
        offline.on("pageerror", lambda error: offline_errors.append(str(error)))

        def route_request(route, request) -> None:
            if request.url.startswith(origin) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                blocked.append(request.url); route.abort("blockedbyclient")

        offline.route("**/*", route_request)
        offline.goto(args.url, wait_until="networkidle", timeout=30_000)
        offline.wait_for_timeout(300)
        offline_body = offline.locator("body").inner_text()
        offline.screenshot(path=args.output / "desktop-final-offline.png", full_page=True)
        result.update({
            "http_status": response.status if response else None,
            "body_text": body,
            "exact_2023_values_visible": all(value in body for value in ("68", "76", "150", "160")),
            "exact_gaps_visible": "8.0 percentage points" in body and "+10" in body,
            "invented_70_percent_target_visible": "Target: ≥70%" in body,
            "selected_year": page.locator("#yearSelectorGroup .active").get_attribute("data-year"),
            "selected_block": page.locator("#blockFilter").input_value(),
            "csv_filename": csv_download.suggested_filename,
            "csv_preview": csv_path.read_text(errors="replace")[:2000],
            "xlsx_filename": xlsx_download.suggested_filename,
            "horizontal_page_overflow_px": max(0, width["scroll"] - width["client"]),
            "external_requests": sorted({url for url in requests if not url.startswith(origin)}),
            "console": console,
            "page_errors": page_errors,
            "offline_blocked_requests": sorted(set(blocked)),
            "offline_page_errors": offline_errors,
            "offline_exact_values_visible": all(value in offline_body for value in ("68", "76", "150", "160")),
            "offline_canvas_count": offline.locator("canvas").count(),
        })
        browser.close()
    (args.output / "inspection.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
