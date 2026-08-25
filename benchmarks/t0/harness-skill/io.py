#!/usr/bin/env python3
"""io tools for an agent harness: the same loader and guard rails as the io desktop app,
as a command line. The agent sees column names and category values, never rows,
unless it runs a query — and query results are the only data it ever sees.

  python3 io.py schema            tables, columns, types, notes (blocks, ledgers, paise, WhatsApp...)
  python3 io.py query "SELECT ..."   run one read-only DuckDB query (max 60 rows shown; full CSV in io_out/last.csv)
  python3 io.py page plan.json    render a dashboard/report plan (see plan_contract.md) to io_out/page.html
"""
import json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "iotools"))
import io_service as svc  # noqa: E402
import render_plan  # noqa: E402

FOLDER = Path(os.environ.get("IO_FOLDER", ".")).resolve()


def load():
    svc.WS.load(FOLDER)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "schema"
    load()
    out = Path("io_out"); out.mkdir(exist_ok=True)
    if cmd == "schema":
        print(svc.WS.schema)
        print("\nKNOWN CATEGORICAL VALUES:\n" + json.dumps(svc.WS.categories, ensure_ascii=False)[:6000])
        return
    if cmd == "query":
        sql = sys.argv[2]
        try:
            res = svc.execute(svc.safe_sql(sql))
        except Exception as exc:
            print(f"QUERY ERROR: {type(exc).__name__}: {str(exc)[:400]}")
            sys.exit(1)
        cols, rows = res["columns"], res["rows"]
        print(" | ".join(cols))
        for r in rows[:60]:
            print(" | ".join("" if r[c] is None else str(r[c]) for c in cols))
        if len(rows) > 60:
            print(f"... {len(rows)} rows total (all rows in io_out/last.csv)")
        else:
            print(f"({len(rows)} rows)")
        (out / "last.csv").write_text(svc.csv_text(res))
        return
    if cmd == "page":
        plan = json.loads(Path(sys.argv[2]).read_text())
        results = {}
        for p in plan["panels"]:
            try:
                results[p["id"]] = svc.execute(svc.safe_sql(p["sql"]))
            except Exception as exc:
                results[p["id"]] = {"columns": [], "rows": [], "error": str(exc)[:200]}
        html = render_plan.render(plan, results, str(FOLDER.name), template=plan.get("_mode", "dashboard"), question=plan.get("subtitle", ""))
        (out / "page.html").write_text(html)
        bad = [k for k, v in results.items() if v.get("error") or not v["rows"]]
        print(f"rendered io_out/page.html with {len(plan['panels'])} panels; failed/empty: {bad}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
