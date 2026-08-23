#!/usr/bin/env python3
"""End-to-end run of benchmarks/t0/ngo-corpus/cases.json through the io service (ask, build and page lanes).

Drives the real io service (loader with header/footer detection, typed dates,
normalised columns; Ask lane; Build lane) over the messy fixtures in
benchmarks/t0/unseen/<sector>/ and compares Ask answers with pandas-computed
gold in benchmarks/t0/unseen/gold.json. Build requests are rendered and
screenshotted for human grading.

Usage: run_unseen_sectors.py --service http://127.0.0.1:8791 --output <dir> [--model-label x]
(the service must already be running with its model configured)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks" / "t0" / "ngo-corpus"

BUILD_REQUESTS = {
    "agri": ["build me a dashboard of the kharif yields - crops, villages, irrigated vs not",
             "write a short note for the FPO board on this season's yield and input costs"],
    "wash": ["dashboard of the handpump survey - functionality by block, water quality, repairs",
             "make a page listing the pumps that need attention"],
    "mfi": ["build a dashboard of SHG repayments month by month and by block",
            "write me a summary of repayment performance for the bank"],
}


def api(base: str, path: str, body: dict | None = None, timeout: int = 600):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


RANK_WORDS = re.compile(r"\b(most|highest|lowest|top|largest|least|rank|biggest|best|worst|fewest|smallest|first|last)\b", re.I)
DATE_RX = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$|^(\d{4})-(\d{2})-(\d{2})")


def norm_date(s: str):
    m = DATE_RX.match(s.strip())
    if not m:
        return None
    if m.group(4):
        return (int(m.group(4)), int(m.group(5)), int(m.group(6)))
    y = int(m.group(3))
    y = y + 2000 if y < 100 else y
    return (y, int(m.group(2)), int(m.group(1)))


def norm(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and not math.isfinite(v):
            return None
        return round(float(v), 2)
    if v is None:
        return None
    s = str(v).strip()
    if s.casefold() in ("never repaired", "never", "none", "na", "n/a", "-", ""):
        return None
    d = norm_date(s)
    if d:
        return ("date", d)
    try:
        return round(float(s.replace(",", "").replace("₹", "").replace("Rs.", "").strip()), 2)
    except ValueError:
        return s.casefold()


def cell_has(gr: list, v) -> bool:
    """An expected value is present in an answer row if it matches a cell, or is contained in a
    text cell (camp titles, messages), or a date matches a date cell in any format."""
    if v is None:
        return True
    for x in gr:
        if isinstance(v, float):
            if isinstance(x, float) and abs(x - v) <= max(0.011, abs(v) * 1e-6):
                return True
            if isinstance(x, str):
                for tok in re.findall(r"-?\d+(?:\.\d+)?", x.replace(",", "")):
                    try:
                        if abs(float(tok) - v) <= max(0.011, abs(v) * 1e-6):
                            return True
                    except ValueError:
                        pass
        elif isinstance(v, tuple):
            if x == v:
                return True
            if isinstance(x, str):
                d = None
                for tok in re.findall(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}", x):
                    d = norm_date(tok)
                    if d == v[1]:
                        return True
        elif isinstance(v, str):
            if x == v or (isinstance(x, str) and v and v in x):
                return True
    return False


def rows_match(got: list[dict], expected: list[list], order_matters: bool, prompt: str = "") -> tuple[bool, str]:
    """Judge what was asked, not how the gold author laid it out: every expected NUMBER must be
    in the answer row; expected TEXT values are required only if the question does not already
    state them and at least one text key must match; extra columns and the full ranking are
    allowed when the gold lists the top-k; ties may reorder neighbours."""
    g = [[norm(x) for x in r.values()] for r in got]
    e = [[norm(x) for x in r] for r in expected]
    if not g:
        return False, "no rows"
    said = prompt.casefold()
    order_matters = order_matters and bool(RANK_WORDS.search(prompt))

    def fits(gr, er):
        nums = [v for v in er if isinstance(v, float)]
        texts = [v for v in er if isinstance(v, (str, tuple)) and not (isinstance(v, str) and v in said)]
        if any(not cell_has(gr, v) for v in nums):
            # a listing answer may omit the measure; accept when every text key is present
            if not texts or not all(cell_has(gr, v) for v in texts):
                return False
            return not any(isinstance(x, float) for x in gr) or len(texts) >= 2
        if texts and not any(cell_has(gr, v) for v in texts):
            return False
        return True

    if len(e) == 1 and len(g) == 1 and any(isinstance(v, float) for v in e[0]):
        nums = [v for v in e[0] if isinstance(v, float)]
        return all(cell_has(g[0], v) for v in nums), "single value"
    if order_matters:
        k = len(e)
        window = g[: k + 2]
        hits = [any(fits(gr, er) for gr in window) for er in e]
        if len(g) < k:  # "which X has the most" answered with one (possibly tied) row
            hits = [any(fits(gr, er) for er in e) for gr in g]
        ok = all(hits)
    else:
        ok = all(any(fits(gr, er) for gr in g) for er in e) and (len(g) == len(e) or len(e) <= 3)
    return ok, f"{len(g)} rows got, {len(e)} expected"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="http://127.0.0.1:8791")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--lanes", default="ask,build,page")
    ap.add_argument("--only", action="append", default=[])
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((CORPUS / "cases.json").read_text())["cases"]
    lanes = set(args.lanes.split(","))
    from playwright.sync_api import sync_playwright
    records = []
    loaded = None
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for case in cases:
            if case["lane"] not in lanes or (args.only and case["id"] not in args.only):
                continue
            if loaded != case["org"]:
                st = api(args.service, "/api/folder", {"path": str(CORPUS / case["org"])})
                loaded = case["org"]
                (out / f"{case['org']}-tables.json").write_text(json.dumps(st["tables"], indent=1, default=str))
            api(args.service, "/api/reset", {})
            started = time.monotonic()
            try:
                r = api(args.service, "/api/ask", {"text": case["prompt"], "lane": case["lane"]}, timeout=900)
            except Exception as exc:  # noqa: BLE001
                r = {"error": str(exc)[:200]}
            rec = {"id": case["id"], "lane": case["lane"], "org": case["org"], "prompt": case["prompt"], "expect": case.get("expect", ""), "seconds": round(time.monotonic() - started, 1),
                   "model_seconds": (r.get("egress") or {}).get("seconds"), "calls": (r.get("egress") or {}).get("calls", 1)}
            if r.get("error"):
                rec.update({"passed": False, "why": r["error"][:200]})
            elif case["lane"] == "ask":
                got_rows = r.get("rows", [])
                if r.get("rowcount", 0) > len(got_rows) and r.get("id"):
                    import csv, io
                    raw = urllib.request.urlopen(f"{args.service}/api/csv/{r['id']}/a1", timeout=60).read().decode()
                    got_rows = list(csv.DictReader(io.StringIO(raw)))
                expected = [list(x.values()) for x in case.get("expected_rows") or []]
                ok, why = rows_match(got_rows, expected, case.get("order_matters", False), case["prompt"]) if expected else (None, "no gold")
                rec.update({"passed": ok, "why": why, "sql": r.get("sql"), "got": got_rows[:60], "expected": expected[:5], "scope_note": r.get("scope_note")})
            else:
                rec.update({"panels": r.get("panels"), "panels_failed": r.get("panels_failed"), "lint_removed": r.get("lint_removed"), "script_errors": r.get("script_errors"), "bytes": r.get("bytes")})
                if r.get("id"):
                    page = browser.new_page(viewport={"width": 1366, "height": 900})
                    errs = []
                    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
                    page.goto(f"{args.service}/api/page/{r['id']}")
                    page.wait_for_timeout(800)
                    shot = out / f"{case['id']}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    (out / f"{case['id']}.html").write_text(page.content())
                    rec["runtime_errors"] = errs[:3]
                    rec["text_chars"] = len(page.inner_text("body"))
                    page.close()
                    rec["screenshot"] = str(shot.relative_to(ROOT))
                rec["passed"] = None
            records.append(rec)
            status = "PASS" if rec.get("passed") else ("FAIL" if rec.get("passed") is False else "----")
            print(f"  {status} {case['id']} {case['prompt'][:70]:<70} {str(rec.get('why') or rec.get('panels') or rec.get('bytes'))[:40]} {rec['seconds']}s", flush=True)
        browser.close()
    asks = [r for r in records if r["lane"] == "ask" and r.get("passed") is not None]
    summary = {"label": args.label, "ask_passed": sum(1 for r in asks if r["passed"]), "ask_total": len(asks),
               "builds": [(r["id"], r.get("panels"), len(r.get("panels_failed") or []), r.get("runtime_errors")) for r in records if r["lane"] == "build"],
               "pages": [(r["id"], r.get("bytes"), r.get("script_errors"), r.get("runtime_errors"), r.get("text_chars")) for r in records if r["lane"] == "page"],
               "mean_seconds": round(sum(r["seconds"] for r in records) / max(len(records), 1), 1)}
    (out / "results.json").write_text(json.dumps({"summary": summary, "records": records}, indent=1, default=str))
    print(json.dumps(summary, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
