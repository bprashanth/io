#!/usr/bin/env python3
"""Open a URL with Playwright and retain basic visual/browser evidence."""

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
    parser.add_argument("--network-mode", choices=("online", "offline"), default="online")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    events: dict[str, object] = {
        "url": args.url,
        "console": [],
        "page_errors": [],
        "failed_requests": [],
        "external_requests": [],
        "blocked_external_requests": [],
        "network_mode": args.network_mode,
    }
    parsed = urlsplit(args.url)
    allowed_origin = f"{parsed.scheme}://{parsed.netloc}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on(
            "request",
            lambda request: events["external_requests"].append(request.url)
            if not request.url.startswith(allowed_origin)
            and not request.url.startswith(("data:", "blob:"))
            else None,
        )
        def restrict_network(route, request) -> None:
            if request.url.startswith(allowed_origin) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                events["blocked_external_requests"].append(request.url)
                route.abort("blockedbyclient")

        if args.network_mode == "offline":
            page.route("**/*", restrict_network)
        page.on("console", lambda msg: events["console"].append({"type": msg.type, "text": msg.text}))
        page.on("pageerror", lambda error: events["page_errors"].append(str(error)))
        page.on(
            "requestfailed",
            lambda request: events["failed_requests"].append(
                {"url": request.url, "failure": request.failure}
            ),
        )
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        events["status"] = response.status if response else None
        events["title"] = page.title()
        events["body_text_length"] = len(page.locator("body").inner_text())
        page.screenshot(path=args.output / "desktop.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=args.output / "narrow.png", full_page=True)
        browser.close()

    (args.output / "events.json").write_text(json.dumps(events, indent=2) + "\n")
    print(json.dumps(events, indent=2))
    return 0 if events.get("status") == 200 and not events["page_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
