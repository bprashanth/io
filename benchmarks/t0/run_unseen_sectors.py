#!/usr/bin/env python3
"""End-to-end check on sectors and sheet shapes the T0 stack was not built against.

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
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNSEEN = ROOT / "benchmarks" / "t0" / "unseen"

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
    if s.casefold() in ("never repaired", "never", "none", "na", "n/a", "-"):
        return None
    try:
        return round(float(s.replace(",", "")), 2)
    except ValueError:
        return s.casefold()


def rows_match(got: list[dict], expected: list[list], order_matters: bool) -> tuple[bool, str]:
    g = [[norm(x) for x in r.values()] for r in got]
    e = [[norm(x) for x in r] for r in expected]
    if not g:
        return False, "no rows"
    # allow extra columns on the left/right: compare on the expected width by best alignment
    width = len(e[0]) if e else 0

    def project(row):
        # keep the columns whose values best match the expected row types: take first text and last numerics
        return row

    def fits(gr, er):
        # every expected value must appear somewhere in the answer row (extra columns and any order allowed);
        # numbers are matched with a small tolerance, text exactly (casefolded)
        pool = list(gr)
        for v in er:
            hit = None
            for i, x in enumerate(pool):
                if isinstance(v, float) and isinstance(x, float) and abs(x - v) <= max(0.011, abs(v) * 1e-6):
                    hit = i
                    break
                if not isinstance(v, float) and x == v:
                    hit = i
                    break
            if hit is None:
                return False
            pool.pop(hit)
        return True

    # gold may list only the top-k of a longer ranking; the answer may carry extra columns
    if order_matters:
        ok = len(g) >= len(e) and all(fits(gr, er) for gr, er in zip(g[:len(e)], e))
    else:
        ok = all(any(fits(gr, er) for gr in g) for er in e) and (len(g) == len(e) or len(e) <= 3)
    return ok, f"{len(g)} rows got, {len(e)} expected"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="http://127.0.0.1:8791")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    gold = json.loads((UNSEEN / "gold.json").read_text())
    from playwright.sync_api import sync_playwright
    records = []
    sectors = sorted({g["sector"] for g in gold})
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for sector in sectors:
            folder = UNSEEN / sector
            st = api(args.service, "/api/folder", {"path": str(folder)})
            tables = [(t.get("table"), t.get("rows"), t.get("columns"), t.get("error")) for t in st["tables"]]
            print(f"== {sector}: " + "; ".join(f"{t[0]} {t[1]}x{len(t[2] or [])}" if not t[3] else f"{t[0]} ERROR {t[3]}" for t in tables), flush=True)
            (out / f"{sector}-tables.json").write_text(json.dumps(st["tables"], indent=1, default=str))
            for item in [g for g in gold if g["sector"] == sector]:
                api(args.service, "/api/reset", {})
                started = time.monotonic()
                try:
                    r = api(args.service, "/api/ask", {"text": item["question"], "lane": "ask"})
                except Exception as exc:  # noqa: BLE001
                    r = {"error": str(exc)[:200]}
                rec = {"sector": sector, "question": item["question"], "seconds": round(time.monotonic() - started, 1)}
                if r.get("error"):
                    rec.update({"passed": False, "why": r["error"][:200]})
                else:
                    got_rows = r.get("rows", [])
                    if r.get("rowcount", 0) > len(got_rows) and r.get("id"):
                        import csv, io
                        raw = urllib.request.urlopen(f"{args.service}/api/csv/{r['id']}/a1", timeout=60).read().decode()
                        got_rows = list(csv.DictReader(io.StringIO(raw)))
                    ok, why = rows_match(got_rows, item["expected_rows"], item.get("order_matters", False))
                    rec.update({"passed": ok, "why": why, "sql": r.get("sql"), "got": r.get("rows", [])[:5], "expected": item["expected_rows"][:5]})
                records.append(rec)
                print(f"  {'PASS' if rec['passed'] else 'FAIL'} {item['question'][:70]:<70} {rec['why'][:40]}", flush=True)
            if args.skip_build:
                continue
            for i, req in enumerate(BUILD_REQUESTS.get(sector, []), 1):
                api(args.service, "/api/reset", {})
                started = time.monotonic()
                try:
                    r = api(args.service, "/api/ask", {"text": req, "lane": "build"})
                except Exception as exc:  # noqa: BLE001
                    r = {"error": str(exc)[:200]}
                rec = {"sector": sector, "build": req, "seconds": round(time.monotonic() - started, 1), "panels": r.get("panels"), "panels_failed": r.get("panels_failed"), "error": r.get("error")}
                if r.get("id"):
                    page = browser.new_page(viewport={"width": 1366, "height": 900})
                    page.goto(f"{args.service}/api/page/{r['id']}")
                    page.wait_for_timeout(400)
                    shot = out / f"{sector}-build-{i}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    (out / f"{sector}-build-{i}.html").write_text(page.content())
                    page.close()
                    rec["screenshot"] = str(shot.relative_to(ROOT))
                records.append(rec)
                print(f"  BUILD {req[:60]:<60} panels={rec['panels']} failed={rec['panels_failed']} {rec['error'] or ''}", flush=True)
        browser.close()
    asks = [r for r in records if "question" in r]
    summary = {"label": args.label, "ask_passed": sum(r["passed"] for r in asks), "ask_total": len(asks),
               "builds": [(r["sector"], r["panels"], len(r["panels_failed"] or [])) for r in records if "build" in r]}
    (out / "results.json").write_text(json.dumps({"summary": summary, "records": records}, indent=1, default=str))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
