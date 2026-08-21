#!/usr/bin/env python3
"""Ask a remote model for a dashboard under two privacy envelopes, then hydrate locally.

schema   : the model sees column names/types/roles, a value-free intent, and THREE
           synthetic example rows generated locally from the column types. It must
           return one self-contained HTML file that renders from `const DATA = __DATA__;`
           Local code replaces the placeholder with the real rows. Nothing real leaves.
redacted : the model sees the pseudonymised rows (tokens instead of identifiers) and
           returns a finished HTML page with data embedded. Local code rehydrates tokens.
full     : (control, synthetic/public fixtures only) the model sees the real rows.

Every page is opened offline in Chromium at 1440x1000, screenshotted, and checked
for console errors and external requests.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "scripts"))
sys.path.insert(0, str(ROOT / "benchmarks" / "pii"))
from run_v2_query_gate import endpoint_json, write_json  # noqa: E402
from pseudonymize import PseudonymMap, pseudonymise_frame  # noqa: E402

RULES = (
    "Return ONE complete self-contained HTML document and nothing else. No external scripts, stylesheets, fonts, "
    "images or fetches: the page must work offline. Draw charts with inline SVG or canvas written by your own JavaScript. "
    "Desktop layout at 1440px wide; no horizontal overflow. Include: a title, KPI cards, at least two different charts, "
    "a sortable/filterable table, a 'Download CSV' button that builds the CSV from the in-page data, and a visible source line. "
    "Never invent numbers: every displayed value must be computed in JavaScript from DATA. "
    "Show units honestly. Percent vs percentage-point must be correct."
)


def synthetic_rows(frame: pd.DataFrame, n: int = 3) -> list[dict[str, Any]]:
    rows = []
    for i in range(n):
        row = {}
        for column in frame.columns:
            series = frame[column]
            if pd.api.types.is_numeric_dtype(series):
                row[column] = float(i + 1) * 10 if series.dtype.kind == "f" else (i + 1) * 10
            else:
                row[column] = f"{re.sub(r'[^A-Za-z]+', '_', str(column)).strip('_').upper()}_{i + 1}"
        rows.append(row)
    return rows


def call(model: str, prompt: str, key: str, max_tokens: int = 40000) -> tuple[str, dict[str, Any]]:
    started = time.monotonic()
    raw = endpoint_json("https://openrouter.ai/api/v1/chat/completions", {
        "model": model, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": max_tokens, "usage": {"include": True}, "reasoning": {"effort": "low"},
    }, 600, key)
    text = raw["choices"][0]["message"].get("content") or ""
    return text, {"model": raw.get("model"), "usage": raw.get("usage"), "seconds": round(time.monotonic() - started, 1),
                  "finish_reason": raw["choices"][0].get("finish_reason")}


def extract_html(text: str) -> str:
    fenced = re.search(r"```(?:html)?\s*(<!DOCTYPE.*?|<html.*?)```", text, flags=re.S | re.I)
    if fenced:
        return fenced.group(1)
    start = re.search(r"<!DOCTYPE|<html", text, flags=re.I)
    return text[start.start():] if start else text


def browser_check(html_path: Path, shot: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright
    report: dict[str, Any] = {"console_errors": [], "page_errors": [], "external_requests": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: report["console_errors"].append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
        def route(r):
            if r.request.url.startswith("file://"):
                r.continue_()
            else:
                report["external_requests"].append(r.request.url)
                r.abort()
        page.route("**/*", route)
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(1500)
        report["overflow_px"] = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        report["svg_count"] = page.evaluate("document.querySelectorAll('svg').length")
        report["canvas_count"] = page.evaluate("document.querySelectorAll('canvas').length")
        report["body_text_head"] = page.evaluate("document.body.innerText.slice(0, 1500)")
        report["table_rows"] = page.evaluate("document.querySelectorAll('tbody tr').length")
        page.screenshot(path=str(shot), full_page=True)
        browser.close()
    report["passed"] = (not report["console_errors"] and not report["page_errors"] and not report["external_requests"]
                        and report["overflow_px"] <= 0 and report["table_rows"] > 0
                        and (report["svg_count"] + report["canvas_count"]) > 0)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--mode", choices=("schema", "redacted", "redacted-sample", "full"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--column-classes", type=Path, help="JSON {column: class} for redacted mode")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, default=400)
    args = parser.parse_args()
    key = json.loads(Path("~/.config/idlisseus/openrouter.json").expanduser().read_text())["api_key"]
    args.output.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(args.data) if args.data.suffix == ".csv" else pd.read_excel(args.data)
    frame = frame.head(args.max_rows)
    schema = [{"name": str(c), "type": "number" if pd.api.types.is_numeric_dtype(frame[c]) else "string"} for c in frame.columns]
    pmap = PseudonymMap(args.output / "pseudonym-map-local-only.json")

    if args.mode == "redacted-sample":
        classes = json.loads(args.column_classes.read_text())
        sample = pseudonymise_frame(frame, classes, pmap).sample(n=min(20, len(frame)), random_state=7)
        pmap.save()
        prompt = (
            f"{RULES}\n\nYou will NOT see the full data. Write the page so that it renders entirely from a JavaScript "
            f"array assigned exactly as `const DATA = __DATA__;` (keep that literal placeholder; local code will replace it "
            f"with the full array of row objects). Column schema: {json.dumps(schema)}. A 20-row SAMPLE in the same shape "
            f"follows; values like NAME_004 or PLACE_011 are placeholders for private fields and will look like that in the "
            f"full data too, so treat them as ordinary labels.\n\nSAMPLE (CSV):\n{sample.to_csv(index=False)}\n\n"
            f"USER REQUEST: {args.question}"
        )
        sent_rows = len(sample)
    elif args.mode == "schema":
        prompt = (
            f"{RULES}\n\nYou will NOT see the real data. Write the page so that it renders entirely from a JavaScript "
            f"array assigned exactly as `const DATA = __DATA__;` (keep that literal placeholder; local code will replace it "
            f"with an array of row objects). Column schema: {json.dumps(schema)}. Three SYNTHETIC example rows showing the "
            f"shape only (values are placeholders, not real): {json.dumps(synthetic_rows(frame))}.\n\n"
            f"Intent outline from the user (no values): {args.question}"
        )
        sent_rows = 0
    else:
        if args.mode == "redacted":
            classes = json.loads(args.column_classes.read_text())
            sent = pseudonymise_frame(frame, classes, pmap)
            pmap.save()
        else:
            sent = frame
        csv_text = sent.to_csv(index=False)
        prompt = (
            f"{RULES}\n\nEmbed the data below in the page as a JavaScript array and compute everything from it. "
            f"Values like NAME_004 or PHONE_011 are placeholders for private fields; treat them as ordinary labels.\n\n"
            f"USER REQUEST: {args.question}\n\nDATA (CSV, {len(sent)} rows):\n{csv_text}"
        )
        sent_rows = len(sent)
    (args.output / "prompt-sent.txt").write_text(prompt)
    text, api = call(args.model, prompt, key)
    (args.output / "raw-response.txt").write_text(text)
    html = extract_html(text)
    if args.mode in ("schema", "redacted-sample"):
        records = json.loads(frame.to_json(orient="records"))
        html = html.replace("__DATA__", json.dumps(records, ensure_ascii=False))
    elif args.mode == "redacted":
        html = pmap.rehydrate(html)
    page_path = args.output / "index.html"
    page_path.write_text(html)
    report = browser_check(page_path, args.output / "desktop.png")
    if api.get("finish_reason") != "stop":
        report["passed"] = False
        report["truncated"] = api.get("finish_reason")
    write_json(args.output / "result.json", {
        "mode": args.mode, "model": args.model, "data": str(args.data), "question": args.question,
        "rows_sent_to_model": sent_rows, "api": api, "browser": report, "html_bytes": len(html),
    })
    print(json.dumps({"mode": args.mode, "model": api["model"], "seconds": api["seconds"],
                      "cost": (api.get("usage") or {}).get("cost"), "passed": report["passed"],
                      "console": report["console_errors"][:2], "external": report["external_requests"][:2],
                      "overflow": report["overflow_px"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
