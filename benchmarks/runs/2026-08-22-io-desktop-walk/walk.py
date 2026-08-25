"""Drive the io desktop UI like a participant: type questions, wait, screenshot."""
import sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]; qs = sys.argv[2:]
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1380, "height": 900})
    pg.goto("http://127.0.0.1:8791/"); pg.wait_for_timeout(500)
    for i, q in enumerate(qs, 1):
        pg.fill("#q", q); pg.press("#q", "Enter")
        pg.wait_for_function("() => !document.querySelector('#send').disabled", timeout=300000)
        pg.wait_for_timeout(800)
        a = pg.locator(".turn").last
        print(f"[{i}] {q}\n    ", a.locator(".meta").inner_text().replace("\n", " | ") if a.locator(".meta").count() else a.locator(".a").inner_text()[:300])
        pg.screenshot(path=f"{out}/{i:02d}.png", full_page=False)
        if a.locator("iframe.page").count():
            url = a.locator("iframe.page").get_attribute("src")
            p2 = b.new_page(viewport={"width": 1366, "height": 900}); p2.goto("http://127.0.0.1:8791" + url); p2.wait_for_timeout(300)
            p2.screenshot(path=f"{out}/{i:02d}-page.png", full_page=True); p2.close()
    b.close()
