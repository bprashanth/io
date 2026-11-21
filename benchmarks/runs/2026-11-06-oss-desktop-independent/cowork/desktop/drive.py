#!/usr/bin/env python3
"""Look at and drive the laptop's Paseo desktop app over its Chrome DevTools port (via the tunnel).

  drive.py shot NAME                      screenshot the app window + print its visible text
  drive.py goto WORKSPACE_ID              open a workspace in the app (shows its latest chat)
  drive.py click "Visible text"           click a button/link by its visible text (last match)
  drive.py clickxy X Y                    click at window coordinates (e.g. a tab header)
  drive.py tabs                           list the app page and its workspace-browser webviews

Env: PASEO_CDP (default http://127.0.0.1:49333), PASEO_SERVER (server id, read from the app URL),
SHOTS (output folder, default ./shots). Needs Python Playwright (no browser download: it attaches).
Read-only by default: it never types into the user's Gmail/Docs pages.
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

CDP = os.environ.get("PASEO_CDP", "http://127.0.0.1:49333")
SHOTS = os.environ.get("SHOTS", "shots")


def app_page(browser):
    pages = [p for c in browser.contexts for p in c.pages]
    return next(p for p in pages if p.url.startswith("paseo://app"))


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp(CDP)
        if cmd == "tabs":
            for c in b.contexts:
                for p in c.pages:
                    print("page", p.url)
            import json, urllib.request
            for t in json.load(urllib.request.urlopen(CDP + "/json/list")):
                print(t["type"], t["url"][:150])
            return
        page = app_page(b)
        if cmd == "goto":
            server = os.environ.get("PASEO_SERVER") or re.search(r"/h/([^/]+)/", page.url).group(1)
            url = f"paseo://app/h/{server}/workspace/{args[0]}"
            page.goto(url)
            page.wait_for_timeout(4000)
            print("at", page.url)
        elif cmd == "click":
            page.get_by_text(args[0]).last.click(timeout=15000)
            page.wait_for_timeout(4000)
            print("clicked", args[0])
        elif cmd == "clickxy":
            page.mouse.click(float(args[0]), float(args[1]))
            page.wait_for_timeout(3000)
            print("clicked at", args)
        elif cmd == "shot":
            os.makedirs(SHOTS, exist_ok=True)
            path = os.path.join(SHOTS, args[0] + ".png")
            page.screenshot(path=path)
            print("saved", path, "| url", page.url)
            print(page.inner_text("body")[:3000])
        else:
            sys.exit(__doc__)


if __name__ == "__main__":
    main()
