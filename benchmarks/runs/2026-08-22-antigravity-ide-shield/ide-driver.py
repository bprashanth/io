"""Tiny CDP driver for the Antigravity workbench."""
import json, os, sys, time
from playwright.sync_api import sync_playwright

def workbench(pw):
    b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    for ctx in b.contexts:
        for pg in ctx.pages:
            if " - Antigravity" in pg.title():
                return b, pg
    return b, b.contexts[0].pages[0]

def status_items(pg):
    return pg.evaluate("""() => Array.from(document.querySelectorAll('.statusbar-item')).map(e => e.innerText.trim()).filter(Boolean)""")

if __name__ == "__main__":
    cmd = sys.argv[1]
    with sync_playwright() as pw:
        b, pg = workbench(pw)
        if cmd == "shot":
            pg.screenshot(path=sys.argv[2]); print(pg.title()); print(status_items(pg))
        elif cmd == "palette":
            pg.keyboard.press("F1"); time.sleep(1); pg.keyboard.type(sys.argv[2]); time.sleep(1.5); pg.keyboard.press("Enter"); time.sleep(float(sys.argv[3]) if len(sys.argv)>3 else 2)
            pg.screenshot(path=sys.argv[4] if len(sys.argv)>4 else "/tmp/p.png"); print(status_items(pg))
        elif cmd == "text":
            print(pg.evaluate("document.body.innerText").strip()[:int(sys.argv[2]) if len(sys.argv)>2 else 3000])
        elif cmd == "eval":
            print(pg.evaluate(sys.argv[2]))

def chat_text(pg):
    """Visible text of the agent panel (right sidebar)."""
    return pg.evaluate("""() => { const el = document.querySelector('.auxiliarybar, #workbench\\\\.parts\\\\.auxiliarybar, .part.auxiliarybar'); return el ? el.innerText : document.body.innerText; }""")

def send(pg, text):
    box = pg.locator("[aria-label='Message input']").last
    box.scroll_into_view_if_needed(); bb = box.bounding_box(); pg.mouse.click(bb['x'] + bb['width']/2, bb['y'] + bb['height']/2)
    time.sleep(0.5); pg.keyboard.type(text); time.sleep(0.5); pg.keyboard.press("Enter")

def wait_idle(pg, secs=300, settle=12):
    last = None; stable = 0; t0 = time.time()
    while time.time() - t0 < secs:
        time.sleep(3); cur = chat_text(pg)
        if cur == last: stable += 3
        else: stable = 0; last = cur
        if stable >= settle and len(cur) > 50: return cur
    return chat_text(pg)


def done():
    sys.stdout.flush(); os._exit(0)   # never let playwright tear down the IDE's contexts
