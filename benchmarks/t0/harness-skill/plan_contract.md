# Plan contract (for `python3 io.py page plan.json`)
{"title": "...", "subtitle": "...", "_mode": "dashboard" | "report",
 "panels": [
   {"id": "p1", "kind": "kpi", "title": "...", "sql": "SELECT COUNT(*) AS n FROM ...", "unit": ""},
   {"id": "p2", "kind": "bar", "title": "...", "sql": "SELECT label, value FROM ... GROUP BY 1 ORDER BY 2 DESC LIMIT 12", "x": "label", "y": ["value"]},
   {"id": "p3", "kind": "line", "title": "...", "sql": "SELECT period, value ...", "x": "period", "y": ["value"]},
   {"id": "p4", "kind": "table", "title": "...", "sql": "SELECT ... LIMIT 20"}],
 "narrative": "optional paragraphs; every number MUST be a placeholder like {{p1}} or {{p2[1].label}}"}
kinds: kpi (one row, one number), bar, stacked_bar, line, scatter, pie, table. 3-7 panels. SQL aliases must match x/y.
