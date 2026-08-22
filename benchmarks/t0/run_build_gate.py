#!/usr/bin/env python3
"""Build/Report lane gate for T0 candidates.

The model gets schema + known categories + the plan contract and must return a
JSON plan (see render_plan.py). The laptop executes every panel with DuckDB,
lints the narrative for numbers the model typed itself, renders the page and
screenshots it. Nothing the model says is shown unless it came from a query.

Scores per request:
  plan_valid       JSON parsed, >=1 panel with id/kind/sql
  panels           total / executed / non-empty / kind-consistent
  repair_used      failed panels re-asked once with the DuckDB error
  lint_literals    numbers typed by the model in the narrative (should be 0)
  lint_unresolved  {{refs}} that point to no panel
  duration_seconds model time

Usage:
  run_build_gate.py --manifest benchmarks/t0/build-suite-v1.json --model qwen/qwen3.5-9b \
      --endpoint https://openrouter.ai/api/v1 --api-key-file ~/.config/idlisseus/openrouter.json \
      --output benchmarks/runs/<stamp>/<model> --reasoning-effort none --screenshot
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sqlglot  # noqa: E402
from sqlglot import exp  # noqa: E402

import render_plan  # noqa: E402
from run_v2_query_gate import call_model, create_database, ddl, known_categories, clean  # noqa: E402

KINDS = {"kpi", "bar", "stacked_bar", "line", "scatter", "pie", "table"}

CONTRACT = """You design a small, honest data page. You never see rows and you never state a number.
You return ONE JSON object and nothing else (no prose, no code fences):
{
  "title": "short page title",
  "subtitle": "one line on what the page answers",
  "panels": [
    {"id": "p1", "kind": "kpi", "title": "Total children", "sql": "SELECT COUNT(*) AS n FROM ...", "unit": ""},
    {"id": "p2", "kind": "bar", "title": "Average score by site", "sql": "SELECT site, AVG(score) AS avg_score FROM ... GROUP BY 1 ORDER BY 2 DESC", "x": "site", "y": ["avg_score"]},
    {"id": "p3", "kind": "line", "title": "Monthly trend", "sql": "SELECT month, SUM(amount) AS total FROM ... GROUP BY 1 ORDER BY 1", "x": "month", "y": ["total"]},
    {"id": "p4", "kind": "table", "title": "Top 10 ...", "sql": "SELECT ... LIMIT 10"}
  ],
  "narrative": "optional: 2-5 short paragraphs. Every number or ranked item MUST be a placeholder: {{p1}} = the number of a one-row panel; {{p5}} = first row of a multi-row panel shown as 'label (value)'; {{p5[2]}} = second row; {{p5.city}} / {{p5[2].total}} = a named column of that row. Never type a digit or a top-ranked name yourself."
}
Rules:
- kinds: kpi (one row, one numeric), bar, stacked_bar (x = category, y = list of numeric columns), line (x = period, y = one numeric, optional "series" column), scatter (x,y numeric), pie (x = category, y = numeric, <= 8 slices), table.
- 3 to 7 panels for a dashboard; 1 to 4 KPIs first. A report adds a narrative with placeholders. For a table-heavy request, prefer tables.
- SQL: one read-only DuckDB SELECT/WITH per panel over ONLY the schema below; quote column names with double quotes when they contain spaces or odd characters; use NULLIF for denominators; group + order + LIMIT so charts stay readable (<= 20 bars). Missing values stay NULL, not zero.
- Column aliases in SQL must match the x / y names you give. Keep aliases snake_case.
- When two tables describe the same thing with different column names, UNION ALL them with aligned aliases.
- Percentages: multiply by 100 and set unit "%".
"""


def make_prompt(request: str, schema: str, categories: dict[str, Any], repair: str | None = None) -> str:
    parts = [CONTRACT, f"SCHEMA:\n{schema}", f"KNOWN CATEGORICAL VALUES:\n{json.dumps(categories, ensure_ascii=False)}", f"REQUEST:\n{request}"]
    if repair:
        parts.append(f"PREVIOUS ATTEMPT PROBLEMS:\n{repair}\nReturn the complete corrected JSON plan.")
    return "\n\n".join(parts)


def extract_json(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    candidate = fenced.group(1) if fenced else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in response")
    return json.loads(candidate[start:end + 1])


def safe_sql(query: str) -> str:
    parsed = sqlglot.parse(query, read="duckdb")
    if len(parsed) != 1 or not isinstance(parsed[0], exp.Query):
        raise ValueError("not exactly one read-only query")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command, exp.Copy)
    if any(isinstance(node, forbidden) for node in parsed[0].walk()):
        raise ValueError("forbidden operation")
    return parsed[0].sql(dialect="duckdb")


def execute_panel(db, panel: dict) -> dict:
    try:
        query = safe_sql(panel["sql"])
        cur = db.execute(query)
        cols = [d[0] for d in cur.description]
        data = cur.fetchall()
        rows = [{c: clean(v) for c, v in zip(cols, r)} for r in data]
        return {"columns": cols, "rows": rows, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"columns": [], "rows": [], "error": f"{type(exc).__name__}: {exc}"[:300]}


def kind_consistent(panel: dict, result: dict) -> tuple[bool, str]:
    kind = panel.get("kind")
    rows, cols = result["rows"], result["columns"]
    if result["error"]:
        return False, "error"
    if kind not in KINDS:
        return False, "unknown kind"
    if not rows:
        return False, "empty"
    first = rows[0]
    numeric = [c for c in cols if isinstance(first.get(c), (int, float)) and not isinstance(first.get(c), bool)]
    if kind == "kpi":
        return (len(rows) == 1 and bool(numeric)), "kpi needs one row with a number"
    if kind in ("bar", "stacked_bar", "line", "pie", "scatter"):
        x = panel.get("x") or cols[0]
        ys = panel.get("y") or numeric
        ys = [ys] if isinstance(ys, str) else ys
        ok = x in cols and all(y in cols for y in ys) and bool(ys) and (kind != "scatter" or x in numeric)
        if ok and kind in ("bar", "pie") and len(rows) > 25:
            return False, f"{len(rows)} categories is unreadable"
        return ok, "x/y not in result columns"
    return True, ""


def validate_plan(plan: dict) -> list[str]:
    problems = []
    panels = plan.get("panels")
    if not isinstance(panels, list) or not panels:
        return ["plan has no panels list"]
    seen = set()
    for i, p in enumerate(panels):
        if not isinstance(p, dict):
            problems.append(f"panel {i} is not an object")
            continue
        pid = p.get("id") or f"p{i + 1}"
        p["id"] = pid
        if pid in seen:
            problems.append(f"duplicate panel id {pid}")
        seen.add(pid)
        if p.get("kind") not in KINDS:
            problems.append(f"{pid}: unknown kind {p.get('kind')!r}")
        if not isinstance(p.get("sql"), str) or not p["sql"].strip():
            problems.append(f"{pid}: missing sql")
    return problems


def run_request(args, db, schema, categories, req: dict, out_dir: Path) -> dict:
    record: dict[str, Any] = {"id": req["id"], "dataset": req["dataset"], "mode": req["mode"], "request": req["request"], "attempts": []}
    repair = None
    plan: dict | None = None
    results: dict[str, dict] = {}
    total_time = 0.0
    for attempt in range(2):
        prompt = make_prompt(req["request"], schema, categories, repair)
        try:
            text, meta = call_model(args.endpoint, args.model, prompt, args.timeout_seconds, args.api_key, args.max_tokens, args.reasoning_effort, args.temperature)
        except Exception as exc:  # noqa: BLE001
            record["attempts"].append({"error": f"{type(exc).__name__}: {exc}"[:300]})
            repair = f"Your previous answer could not be used: {exc}"
            continue
        total_time += meta["duration_seconds"]
        att: dict[str, Any] = {"meta": meta, "raw": text}
        try:
            candidate = extract_json(text)
            problems = validate_plan(candidate)
        except Exception as exc:  # noqa: BLE001
            candidate, problems = None, [f"unparseable JSON: {exc}"]
        att["problems"] = problems
        if candidate is None or problems:
            record["attempts"].append(att)
            repair = "\n".join(problems)
            continue
        plan = candidate
        results = {p["id"]: execute_panel(db, p) for p in plan["panels"]}
        consistency = {p["id"]: kind_consistent(p, results[p["id"]]) for p in plan["panels"]}
        bad = [f"{pid}: {results[pid]['error'] or reason}" for pid, (ok, reason) in consistency.items() if not ok]
        att["panel_problems"] = bad
        record["attempts"].append(att)
        if bad and attempt == 0:
            repair = "These panels failed when the laptop ran them:\n" + "\n".join(bad) + "\nFix only what is needed and return the full plan again."
            # keep the best so far; a repaired plan replaces it if it improves
            record["_first"] = (plan, results, consistency)
            continue
        break
    if plan is None:
        if "_first" in record:
            plan, results, consistency = record.pop("_first")
        else:
            record.update({"plan_valid": False, "duration_seconds": total_time})
            return record
    elif "_first" in record:
        first_plan, first_results, first_cons = record.pop("_first")
        if sum(ok for ok, _ in first_cons.values()) > sum(ok for ok, _ in consistency.values()):
            plan, results, consistency = first_plan, first_results, first_cons
    record["repair_used"] = len(record["attempts"]) > 1
    narrative = plan.get("narrative") or ""
    literals = render_plan.numeric_literal_lint(narrative) if narrative else []
    html_doc = render_plan.render(plan, results, req.get("source", req["dataset"]), template="report" if req["mode"] == "report" else "dashboard", question=req["request"])
    _, unresolved = render_plan.fill_narrative(narrative, results) if narrative else ("", [])
    page = out_dir / f"{req['id']}.html"
    page.write_text(html_doc)
    (out_dir / f"{req['id']}.plan.json").write_text(json.dumps({"plan": plan, "results": {k: {"columns": v["columns"], "rows": v["rows"][:50], "rowcount": len(v["rows"]), "error": v["error"]} for k, v in results.items()}}, indent=1, default=str))
    record.update({
        "plan_valid": True,
        "panels_total": len(plan["panels"]),
        "panels_ok": sum(1 for ok, _ in consistency.values() if ok),
        "panel_problems": [f"{pid}: {results[pid]['error'] or reason}" for pid, (ok, reason) in consistency.items() if not ok],
        "kinds": [p.get("kind") for p in plan["panels"]],
        "has_narrative": bool(narrative),
        "lint_literals": literals,
        "lint_unresolved": unresolved,
        "duration_seconds": round(total_time, 2),
        "page": str(page.resolve().relative_to(ROOT)),
    })
    return record


def screenshot_pages(pages: list[Path]) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        for p in pages:
            page.goto(p.resolve().as_uri())
            page.wait_for_timeout(150)
            page.screenshot(path=str(p.with_suffix(".png")), full_page=True)
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=ROOT / "benchmarks/t0/build-suite-v1.json")
    ap.add_argument("--endpoint", default="https://openrouter.ai/api/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--api-key-file", type=Path)
    ap.add_argument("--timeout-seconds", type=int, default=180)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--reasoning-effort", choices=("none", "low", "medium", "high"))
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--screenshot", action="store_true")
    args = ap.parse_args()
    args.api_key = None
    if args.api_key_file:
        raw = json.loads(args.api_key_file.expanduser().read_text())
        args.api_key = raw.get("api_key") or raw.get("key") or raw.get("OPENROUTER_API_KEY") or next(iter(raw.values()))
    manifest = json.loads(args.manifest.read_text())
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    dbs: dict[str, tuple] = {}
    for req in manifest["requests"]:
        if args.only and req["id"] not in args.only:
            continue
        ds = manifest["datasets"][req["dataset"]]
        if req["dataset"] not in dbs:
            sub = {"tables": ds["tables"]}
            db, _ = create_database(sub)
            dbs[req["dataset"]] = (db, ddl(db, sub), known_categories(db, sub))
        db, schema, cats = dbs[req["dataset"]]
        req = {**req, "source": ", ".join(Path(t["path"]).name for t in ds["tables"])}
        started = time.monotonic()
        rec = run_request(args, db, schema, cats, req, out)
        rec["wall_seconds"] = round(time.monotonic() - started, 2)
        records.append(rec)
        status = f"{rec.get('panels_ok', 0)}/{rec.get('panels_total', 0)} panels" if rec.get("plan_valid") else "INVALID PLAN"
        print(f"{req['id']:<34} {status:<14} lint={len(rec.get('lint_literals', []))}+{len(rec.get('lint_unresolved', []))} {rec.get('duration_seconds', 0):>6}s", flush=True)
    summary = {
        "model": args.model, "endpoint": args.endpoint, "manifest": str(args.manifest.relative_to(ROOT)) if args.manifest.is_relative_to(ROOT) else str(args.manifest),
        "requests": len(records),
        "plan_valid": sum(1 for r in records if r.get("plan_valid")),
        "panels_total": sum(r.get("panels_total", 0) for r in records),
        "panels_ok": sum(r.get("panels_ok", 0) for r in records),
        "fully_clean": sum(1 for r in records if r.get("plan_valid") and r["panels_ok"] == r["panels_total"] and not r["lint_literals"] and not r["lint_unresolved"]),
        "repairs": sum(1 for r in records if r.get("repair_used")),
        "lint_literal_requests": sum(1 for r in records if r.get("lint_literals")),
        "mean_model_seconds": round(sum(r.get("duration_seconds", 0) for r in records) / max(len(records), 1), 2),
    }
    (out / "results.json").write_text(json.dumps({"summary": summary, "records": records}, indent=1, default=str))
    print(json.dumps(summary, indent=1))
    if args.screenshot:
        screenshot_pages([ROOT / r["page"] for r in records if r.get("page")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
