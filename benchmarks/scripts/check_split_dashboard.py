#!/usr/bin/env python3
"""Open, exercise and capture a split-pipeline dashboard with Chromium."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--select-column")
    parser.add_argument("--select-value")
    parser.add_argument("--expected-filtered-rows", type=int)
    parser.add_argument("--expected-current-rows", type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    console_errors: list[str] = []
    page_errors: list[str] = []
    requests: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        response = await page.goto(args.url, wait_until="networkidle")
        await page.screenshot(path=args.output / "desktop-initial.png", full_page=True)
        initial_rows = await page.locator("#tbody tr").count()
        initial = await page.evaluate("""() => ({
          title: document.title,
          heading: document.querySelector('h1')?.textContent,
          chartSvg: document.querySelectorAll('#chart svg').length,
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          bodyText: document.body.innerText
        })""")

        selected_rows = None
        if args.select_column and args.select_value:
            select = page.locator(f'select[data-col="{args.select_column}"]')
            if await select.count() != 1:
                raise AssertionError(f"missing unique {args.select_column} control")
            await select.select_option(label=args.select_value)
            await page.wait_for_timeout(100)
            selected_rows = await page.locator("#tbody tr").count()
            await page.screenshot(path=args.output / "desktop-filtered.png", full_page=True)

        async with page.expect_download() as download_info:
            await page.locator("#download").click()
        download = await download_info.value
        download_path = args.output / "downloads" / download.suggested_filename
        download_path.parent.mkdir(exist_ok=True)
        await download.save_as(download_path)
        with download_path.open(newline="") as handle:
            downloaded = list(csv.DictReader(handle))

        await browser.close()

    target_host = urlparse(args.url).netloc
    external = [url for url in requests if urlparse(url).netloc not in ("", target_host)]
    checks = {
        "http_status": response.status if response else None,
        "title_present": bool(initial["title"]),
        "heading_present": bool(initial["heading"]),
        "chart_svg_count": initial["chartSvg"],
        "initial_table_rows": initial_rows,
        "selected_table_rows": selected_rows,
        "expected_filtered_rows": args.expected_filtered_rows,
        "downloaded_rows": len(downloaded),
        "download_columns": list(downloaded[0]) if downloaded else [],
        "horizontal_page_overflow_px": max(0, initial["scrollWidth"] - initial["clientWidth"]),
        "console_errors": console_errors,
        "page_errors": page_errors,
        "external_requests": external,
    }
    failures = []
    if checks["http_status"] != 200: failures.append("page did not return 200")
    if checks["chart_svg_count"] != 1: failures.append("chart SVG missing")
    if checks["horizontal_page_overflow_px"]: failures.append("desktop page overflows horizontally")
    if console_errors or page_errors: failures.append("browser errors present")
    if external: failures.append("page made external requests")
    if args.expected_filtered_rows is not None:
        if selected_rows != args.expected_filtered_rows: failures.append("filtered table row count is wrong")
        if len(downloaded) != args.expected_filtered_rows: failures.append("download row count is wrong")
    if args.expected_current_rows is not None:
        if initial_rows != args.expected_current_rows: failures.append("initial table row count is wrong")
        if len(downloaded) != args.expected_current_rows: failures.append("download row count is wrong")
    for required in ("year", "source"):
        if required not in checks["download_columns"]: failures.append(f"download omits {required}")
    checks["failures"] = failures
    checks["passed"] = not failures
    (args.output / "browser-check.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
