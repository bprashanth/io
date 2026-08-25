#!/usr/bin/env python3
"""Generic Build gate: can a small model produce a working page / form / PWA from a plain request?

Unlike the data Build gate (plans + SQL), here the model writes the HTML itself.
Two modes:
  free      : "return one self-contained HTML file"
  template  : the model fills a skeleton we supply (inline stylesheet, storage helper,
              service-worker stub) — the "cheat with a template" path for T0.

Each page is loaded in headless Chromium; we record console errors, count
interactive elements, click the first button and see whether the DOM changed,
check request-specific must-haves (regex on the HTML / DOM text), and screenshot.
For the hybrid data request the laptop injects `window.data` before load and
checks that a value from the data shows up on screen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "scripts"))
from run_v2_query_gate import call_model  # noqa: E402

REQUESTS = [
    {"id": "attendance-pwa", "request": "build me a PWA to mark daily attendance for our 25 tuition kids that works offline on a phone; names typed once, then tick present/absent each day, and a monthly summary",
     "must": [r"manifest", r"serviceWorker|service-worker|sw\.js", r"localStorage|indexedDB"], "interactive": True},
    {"id": "ngo-homepage", "request": "make a simple website homepage for Jagruti Foundation - what we do, our three programmes, a photo strip (placeholders are fine), contact section",
     "must": [r"(?i)jagruti", r"(?i)contact", r"<img|<svg|placeholder"], "interactive": False},
    {"id": "registration-form", "request": "a beneficiary registration form: name, age, village, phone, category dropdown, with validation, saved in the browser and a button to download all entries as CSV",
     "must": [r"<form|<input", r"(?i)csv", r"localStorage"], "interactive": True},
    {"id": "expense-tracker", "request": "a small expense tracker page for our field team - add expense with date, head, amount; show running total and totals by head",
     "must": [r"(?i)total", r"<input", r"localStorage|let |const "], "interactive": True},
    {"id": "event-signup", "request": "an event signup page for our 14 September health camp with a countdown, a signup form and a list of who has signed up",
     "must": [r"(?i)countdown|setInterval|Date", r"<form|<input"], "interactive": True},
    {"id": "quiz", "request": "a 5 question quiz page on hand washing for school kids with a score at the end and a try again button",
     "must": [r"(?i)score", r"(?i)try again|restart"], "interactive": True},
    {"id": "data-website", "request": "make a website page showing our scholarship scheme progress district wise with pending cases; the data will be available at runtime as window.data (an array of row objects with these columns: District, Taluka, Status, Marks %, Family Income, Name of scheme) - do not hardcode numbers",
     "must": [r"window\.data"], "interactive": False, "inject": True},
    {"id": "survey-collector", "request": "a mobile friendly survey form for a water point survey (habitation, pump type, working yes/no, users, GPS from the phone) that stores responses offline and exports JSON",
     "must": [r"geolocation", r"localStorage|indexedDB", r"(?i)json"], "interactive": True},
]

FREE_PROMPT = """You build small, self-contained web pages for a social-sector NGO. Return ONE complete HTML document and nothing else (no prose, no code fences). Rules: everything inline (CSS and JS in the file; no external URLs, no CDNs, no frameworks); must work offline from a file; must not throw console errors; clean readable layout; plain English labels. If the request needs a service worker, register it from an inline Blob URL so the single file is enough. If data is promised at runtime as window.data, read it from there and never hardcode numbers.

REQUEST:
{request}
"""

TEMPLATE_PROMPT = """You build small web pages for a social-sector NGO by FILLING A SKELETON. Return ONE complete HTML document and nothing else (no prose, no code fences). Keep the skeleton's <style> and the helper script exactly; add your markup inside <main> and your code inside the marked script block. No external URLs. Must not throw console errors. If data is promised as window.data, read it from there and never hardcode numbers.

SKELETON:
{skeleton}

REQUEST:
{request}
"""

SKELETON = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PAGE TITLE</title>
<link rel="manifest" href='data:application/manifest+json,{"name":"PAGE TITLE","short_name":"PAGE","start_url":".","display":"standalone","background_color":"#f6f7fb","theme_color":"#2563eb"}'>
<style>
:root{--ink:#111827;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--bg:#f6f7fb}*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 20px}h1{font-size:22px;margin:0}main{max-width:900px;margin:0 auto;padding:20px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}label{display:block;font-size:13px;color:var(--muted);margin:8px 0 2px}
input,select,textarea{font:inherit;width:100%;padding:8px;border:1px solid var(--line);border-radius:8px}button{font:inherit;padding:8px 14px;border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:8px;cursor:pointer}button.secondary{background:#fff;color:var(--accent)}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}.muted{color:var(--muted)}.row{display:flex;gap:10px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
</style></head><body>
<header><h1>PAGE TITLE</h1></header>
<main>
<!-- YOUR MARKUP HERE -->
</main>
<script>
// helper: offline storage and CSV/JSON export (keep as is)
const store = { get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } }, set: (k, v) => localStorage.setItem(k, JSON.stringify(v)) };
function download(name, text, type) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {type: type || 'text/plain'})); a.download = name; a.click(); }
function toCSV(rows) { if (!rows.length) return ''; const cols = Object.keys(rows[0]); const esc = v => { const s = v == null ? '' : String(v); return /[",\\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }; return [cols.join(',')].concat(rows.map(r => cols.map(c => esc(r[c])).join(','))).join('\\n'); }
function offlineReady() { if (!('serviceWorker' in navigator)) return; const sw = "self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('fetch',e=>{});"; try { navigator.serviceWorker.register(URL.createObjectURL(new Blob([sw], {type: 'text/javascript'}))).catch(()=>{}); } catch (e) {} }
offlineReady();
// YOUR CODE HERE
</script>
</body></html>"""

SAMPLE_DATA = [
    {"District": "Gaya", "Taluka": "Wazirganj", "Status": "Pending", "Marks %": 71.2, "Family Income": 120000, "Name of scheme": "Post-Matric Scholarship"},
    {"District": "Gaya", "Taluka": "Belaganj", "Status": "Approved", "Marks %": 82.0, "Family Income": 90000, "Name of scheme": "Post-Matric Scholarship"},
    {"District": "Pune", "Taluka": "Khed", "Status": "Pending", "Marks %": 64.5, "Family Income": 150000, "Name of scheme": "Rajarshi Shahu"},
    {"District": "Pune", "Taluka": "Junnar", "Status": "Rejected", "Marks %": 55.0, "Family Income": 210000, "Name of scheme": "EBC Scholarship"},
    {"District": "Muzaffarpur", "Taluka": "Kanti", "Status": "Disbursed", "Marks %": 77.7, "Family Income": 80000, "Name of scheme": "Post-Matric Scholarship"},
    {"District": "Muzaffarpur", "Taluka": "Sakra", "Status": "Pending", "Marks %": 69.0, "Family Income": 110000, "Name of scheme": "Minority Welfare"},
]


def extract_html(text: str) -> str:
    fenced = re.search(r"```(?:html)?\s*(<!doctype.*?|<html.*?)```", text, flags=re.I | re.S)
    cand = fenced.group(1) if fenced else text
    i = cand.lower().find("<!doctype")
    if i < 0:
        i = cand.lower().find("<html")
    if i < 0:
        raise ValueError("no HTML document in answer")
    j = cand.lower().rfind("</html>")
    return cand[i:(j + 7) if j > 0 else None]


def check_page(path: Path, req: dict, pw) -> dict:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1100, "height": 800})
    page = ctx.new_page()
    page.on("dialog", lambda d: d.dismiss())
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    page.on("console", lambda m: errors.append(m.text[:200]) if m.type == "error" else None)
    if req.get("inject"):
        page.add_init_script(f"window.data = {json.dumps(SAMPLE_DATA)};")
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(700)
    html = path.read_text(errors="replace")
    text = page.inner_text("body")
    must = [(m, bool(re.search(m, html))) for m in req["must"]]
    buttons = page.locator("button, input[type=submit], a[href^='#']").count()
    inputs = page.locator("input, select, textarea").count()
    dom_changed = None
    if req.get("interactive") and buttons:
        before = page.content()
        try:
            # fill any text inputs first so validation does not block the click
            for inp in page.locator("input:not([type=checkbox]):not([type=radio]):not([type=submit]):not([type=hidden])").all()[:6]:
                t = (inp.get_attribute("type") or "text").lower()
                try:
                    if t == "number":
                        inp.fill("12")
                    elif t == "date":
                        inp.fill("2026-09-14")
                    elif t in ("text", "tel", "email", "search", ""):
                        inp.fill("Asha Test" if t != "tel" else "9876543210")
                except Exception:  # noqa: BLE001
                    pass
            for sel in page.locator("select").all()[:6]:
                try:
                    opts = sel.locator("option").all()
                    vals = [o.get_attribute("value") for o in opts]
                    pick = next((v for v in vals if v), None)
                    if pick is not None:
                        sel.select_option(pick, timeout=1000)
                except Exception:  # noqa: BLE001
                    pass
            for cb in page.locator("input[type=checkbox], input[type=radio]").all()[:3]:
                try:
                    cb.check(timeout=500)
                except Exception:  # noqa: BLE001
                    pass
            dom_changed = False
            for b in page.locator("button, input[type=submit]").all()[:6]:
                try:
                    b.click(timeout=1500)
                    page.wait_for_timeout(300)
                except Exception:  # noqa: BLE001
                    continue
                if page.content() != before:
                    dom_changed = True
                    break
        except Exception as exc:  # noqa: BLE001
            dom_changed = False
            errors.append(f"click failed: {str(exc)[:120]}")
    data_shown = None
    if req.get("inject"):
        data_shown = any(v in text for v in ("Gaya", "Muzaffarpur", "Wazirganj", "Rajarshi"))
    page.screenshot(path=str(path.with_suffix(".png")), full_page=True)
    browser.close()
    return {"console_errors": errors[:5], "must": must, "buttons": buttons, "inputs": inputs, "dom_changed_on_click": dom_changed, "data_shown": data_shown,
            "bytes": len(html), "text_chars": len(text)}


def score(chk: dict, req: dict) -> tuple[bool, str]:
    if chk["console_errors"]:
        return False, "console errors"
    if not all(ok for _, ok in chk["must"]):
        return False, "missing: " + ", ".join(m for m, ok in chk["must"] if not ok)
    if req.get("interactive") and not chk["dom_changed_on_click"]:
        return False, "nothing happened on click"
    if req.get("inject") and not chk["data_shown"]:
        return False, "injected data not shown"
    if chk["text_chars"] < 80:
        return False, "almost empty page"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--endpoint", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key-file", type=Path)
    ap.add_argument("--mode", choices=("free", "template"), default="free")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--reasoning-effort", choices=("none", "low", "medium", "high"))
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--timeout-seconds", type=int, default=300)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--recheck", action="store_true", help="re-score the HTML already in --output without calling the model")
    args = ap.parse_args()
    key = None
    if args.api_key_file:
        key = json.loads(args.api_key_file.expanduser().read_text())["api_key"]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    records = []
    with sync_playwright() as pw:
        for req in REQUESTS:
            if args.only and req["id"] not in args.only:
                continue
            prompt = FREE_PROMPT.format(request=req["request"]) if args.mode == "free" else TEMPLATE_PROMPT.format(skeleton=SKELETON, request=req["request"])
            rec = {"id": req["id"], "request": req["request"], "mode": args.mode}
            started = time.monotonic()
            try:
                path = out / f"{req['id']}.html"
                if args.recheck:
                    if not path.exists():
                        raise FileNotFoundError("no page from the model")
                else:
                    text, meta = call_model(args.endpoint, args.model, prompt, args.timeout_seconds, key, args.max_tokens, args.reasoning_effort, 0.0)
                    rec["meta"] = meta
                    html = extract_html(text)
                    path.write_text(html)
                chk = check_page(path, req, pw)
                ok, why = score(chk, req)
                rec.update({"check": chk, "passed": ok, "why": why, "page": str(path.relative_to(ROOT))})
            except Exception as exc:  # noqa: BLE001
                rec.update({"passed": False, "why": f"{type(exc).__name__}: {str(exc)[:200]}"})
            rec["seconds"] = round(time.monotonic() - started, 1)
            records.append(rec)
            print(f"{req['id']:<20} {'PASS' if rec['passed'] else 'FAIL':<5} {rec['why'][:60]:<60} {rec['seconds']:>6}s", flush=True)
    summary = {"model": args.model, "mode": args.mode, "passed": sum(r["passed"] for r in records), "total": len(records),
               "mean_seconds": round(sum(r["seconds"] for r in records) / max(len(records), 1), 1)}
    (out / "results.json").write_text(json.dumps({"summary": summary, "records": records}, indent=1, default=str))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
