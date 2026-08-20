#!/usr/bin/env python3
"""Exercise the partial Antigravity irregular-workbook page after a failed run."""

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
    result: dict[str, object] = {"case_id": "dev-xlsx-headers-001", "surface": "Antigravity partial turn-1 workspace"}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        console: list[dict[str, str]] = []
        blocked: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda message: console.append({"type": message.type, "text": message.text}))
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def route_request(route, request) -> None:
            if request.url.startswith(origin) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                blocked.append(request.url); route.abort("blockedbyclient")

        page.route("**/*", route_request)
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        initial = page.locator("body").inner_text()
        page.screenshot(path=args.output / "desktop-primary.png", full_page=True)
        page.locator("#select-level").select_option("secondary")
        page.locator("#select-year").select_option("2023")
        page.locator("#select-indicator").select_option("girls")
        page.wait_for_timeout(200)
        secondary = page.locator("body").inner_text()
        page.screenshot(path=args.output / "desktop-secondary-girls-2023.png", full_page=True)
        with page.expect_download(timeout=5_000) as download_info:
            page.locator("#btn-export-csv").click()
        download = download_info.value
        download_path = args.output / download.suggested_filename
        await_path = download.path()
        if await_path:
            download.save_as(download_path)
        headers = page.locator("#attendance-table thead").inner_text()
        rows = page.locator("#attendance-table tbody tr").count()
        selects = page.locator("#select-block option").all_text_contents()
        width = page.evaluate("() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})")
        result.update({
            "http_status": response.status if response else None,
            "initial_primary_values_present": all(value in initial for value in ("82%", "80%", "76%", "74%", "73%", "71%")),
            "secondary_2023_girls_values_present": all(value in secondary for value in ("73%", "66%", "63%")),
            "secondary_table_rows": rows,
            "secondary_table_headers": headers,
            "block_options": selects,
            "supports_two-block_selection": False,
            "download_filename": download.suggested_filename,
            "download_path": str(download_path),
            "download_preview": download_path.read_text(errors="replace")[:1200] if download_path.exists() else None,
            "horizontal_page_overflow_px": max(0, width["scroll"] - width["client"]),
            "blocked_external_requests": sorted(set(blocked)),
            "console": console,
            "page_errors": page_errors,
        })
        browser.close()
    (args.output / "inspection.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
