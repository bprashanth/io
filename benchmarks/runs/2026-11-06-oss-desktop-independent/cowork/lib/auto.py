"""Auto: the 9B fills the form plus three flags (what kind of question, whether the figure is ambiguous, which
figures might be meant); code gates the form before running it: a "why / high" about one group gets a baseline
injected, an ambiguous figure gets a profile of every candidate as % difference from the whole file, and figures in
different units never share an axis. Every answer carries a render receipt, read from the drawn chart, which is the
9B's only source for talking about the chart.

Proposal "Grounded Small-Model Analytics Pipeline" (benchmarks/runs/2026-11-13-grounded-9b). Used when the chat's
model is idli-9b-auto: lib/modes.py adds pipeline="auto" to file_ask, masks a reply the person challenges, re-injects
the receipt, and keeps other models out of the chat.

  ask(files, file, question, chart=False) -> tool result {answer, table, chart_markdown?, render_receipt, say_to_user}
"""
import hashlib
import json
import os

from lib import receipt as R
from lib.careful import Ctx, _fmt, _llm, _match_value, _q, _where, _brief  # shared plumbing only

ARCHETYPES = ["single_lookup", "comparison", "why_diagnostic", "distribution", "trend", "ambiguous_metric", "listing"]
PROMPT = """You turn a question about a spreadsheet into a form spec, plus three flags. The form answers with code.

- spec: measures [ids], group_by [up to 2 ids], filters {column: [values]}. Use only ids and values from the form.
  When the person names several groups ("across A, B and C"), put them in filters and group_by that column.
- intent_archetype: single_lookup, comparison, why_diagnostic ("why is X high / low"), distribution, trend,
  ambiguous_metric, listing.
- ambiguity_detected: true when the person uses high / low / worst / struggling / doing well / so bad without naming
  a figure.
- candidate_measures: when ambiguity_detected, the figures they might mean (up to 6 ids); else [].
- target_entity: the one group the question is about ({"column", "value"}), or null.
- chart: true when they ask for a chart/graph/plot/picture/visualise.
Follow-ups ("same but", "now debt", "that ward") refine the previous question in the thread."""


def _schema(form):
    mids = [m["id"] for m in form["measures"]]
    gids = [g["id"] for g in form["group_by"]] or ["_none"]
    cols = [x["column"] for x in form["filters"]] or ["_none"]
    return {"type": "object", "additionalProperties": False,
            "required": ["spec", "intent_archetype", "ambiguity_detected", "candidate_measures", "target_entity",
                         "chart"],
            "properties": {
                "spec": {"type": "object", "additionalProperties": False, "required": ["measures", "group_by", "filters"],
                         "properties": {"measures": {"type": "array", "maxItems": 6, "items": {"enum": mids}},
                                        "group_by": {"type": "array", "maxItems": 2, "items": {"enum": gids}},
                                        "filters": {"type": "object", "additionalProperties": {
                                            "type": "array", "items": {"type": "string"}, "maxItems": 5}}}},
                "intent_archetype": {"enum": ARCHETYPES},
                "ambiguity_detected": {"type": "boolean"},
                "candidate_measures": {"type": "array", "maxItems": 6, "items": {"enum": mids}},
                "target_entity": {"anyOf": [{"type": "null"}, {"type": "object", "additionalProperties": False,
                                                               "required": ["column", "value"],
                                                               "properties": {"column": {"enum": cols},
                                                                              "value": {"type": "string"}}}]},
                "chart": {"type": "boolean"}}}


_threads = {}  # file -> [{q, spec, archetype}]
SAY = ("Write chart_markdown exactly, on its own line (if there is one). Then tell the person what it shows in two or "
       "three short sentences, using only render_receipt for anything about the chart (axes, number of bars, groups, "
       "baseline) and only `answer` / `table` for numbers. If render_receipt.omitted_from_chart is not empty, say "
       "which figures were left off the chart and that they are in the table. Never mention or offer other AI models.")


def ask(files, file, question, chart=False, tab=None):
    c = Ctx(files, file, tab)
    thread = _threads.setdefault(file, [])
    prompt = (PROMPT + "\n\nThe form:\n" + json.dumps(_brief(c.f), ensure_ascii=False)
              + ("\n\nThe thread so far:\n" + "\n".join(json.dumps(t, ensure_ascii=False) for t in thread[-4:])
                 if thread else "") + "\n\nQuestion: " + question)
    got, secs = _llm(prompt, _schema(c.f))
    out = gate_and_run(c, got, question, chart or bool(got.get("chart")))
    out["spec_model_secs"] = secs
    out["form_fill"] = got
    thread.append({"q": question, "spec": out.get("ran"), "archetype": got.get("intent_archetype")})
    return out


def _single_target(c, got):
    """(column, value) when the question is about one group: from target_entity or a one-value filter."""
    by = {x["column"]: x for x in c.f["filters"] if x["kind"] == "choice"}
    t = got.get("target_entity") or {}
    if t.get("column") in by:
        v = _match_value(by[t["column"]], t.get("value"))
        if v is not None:
            return t["column"], v
    for col, vals in ((got.get("spec") or {}).get("filters") or {}).items():
        if col in by and isinstance(vals, list) and len(vals) == 1:
            v = _match_value(by[col], vals[0])
            if v is not None:
                return col, v
    if t.get("value"):  # the 9B named a group but in the wrong column
        for col, x in by.items():
            v = _match_value(x, t["value"])
            if v is not None:
                return col, v
    return None


def gate_and_run(c, got, question, chart):
    spec = got.get("spec") or {}
    mids = [m for m in spec.get("measures") or [] if m in c.f["_measures"]]
    cands = [m for m in got.get("candidate_measures") or [] if m in c.f["_measures"] and m != "rows"]
    arche = got.get("intent_archetype") or "single_lookup"
    amb = bool(got.get("ambiguity_detected"))
    tgt = _single_target(c, got)
    actions = []
    if arche in ("comparison", "why_diagnostic") or amb:
        if tgt:
            pool = _fair([m for m in (cands if amb and cands else mids) if m != "rows"], c)
            pool = pool or [m for m in mids if m != "rows"] or _defaults(c)
            if len(pool) > 1 and (amb or len({c.units.get(m) for m in pool}) > 1 or arche == "why_diagnostic"):
                actions.append(f"ambiguity short-circuit: profile of {len(pool)} figures as % difference from the "
                               "whole file")
                return _profile(c, tgt, pool[:6], question, actions, got)
            actions.append("baseline rule: one group can't show 'high'; all groups drawn, whole-file average as the "
                           "reference")
            return _with_baseline(c, tgt, pool[0], question, actions, got)
    if arche == "trend" and not c.f.get("date_columns"):
        return {"answer": "This file has no date column, so there is no change over time to show. Nothing was "
                          "estimated.", "render_receipt": R.receipt(None, None, why_no_chart="no dates in the file"),
                "say_to_user": SAY, "gate": ["no dates: nothing estimated"]}
    # the form as filled; mixed units go to panels (one axis each), recorded
    run = {"measures": mids if arche != "listing" else [], "group_by": [g for g in spec.get("group_by") or []
                                                                         if g in c.f["_groups"]]}
    filt = {}
    by = {x["column"]: x for x in c.f["filters"]}
    for col, vals in (spec.get("filters") or {}).items():
        if col in by and isinstance(vals, list):
            vv = [_match_value(by[col], v) if by[col]["kind"] == "choice" else v for v in vals]
            vv = [v for v in vv if v is not None]
            if vv:
                filt[col] = vv
    if filt:
        run["filters"] = filt
    res = c.files.run(c.file, c.tab, run)
    path, vl = None, None
    labels = [c.label(m) for m in mids]
    why = None
    if not res["rows"]:
        why = "no rows match"
    elif chart and run["group_by"] and mids and len(res["rows"]) >= 2:
        from lib import vlchart
        vl = vlchart.spec_for(res, res["described"], run, c.f)
        if vl:
            path = _render(c, vl, ["auto", run])
            if len(mids) > 1 and len({c.units.get(m) for m in mids}) > 1:
                actions.append("units differ: one panel per figure, each with its own axis")
    elif chart:
        why = "one row: the numbers say it better than one bar"
    rc = R.receipt(path, vl, requested=labels, units_of={c.label(k): u for k, u in c.units.items()},
                   why_no_chart=why if not path else None)
    out = {"answer": res["text"] if res["rows"] else "No rows match that. (That's no data, not a zero.)",
           "render_receipt": rc, "say_to_user": SAY, "gate": actions or ["form run as filled"], "ran": run}
    if path:
        out["chart_markdown"] = f"![{res['described']}]({path})"
    return out


def _fair(ids, c):
    """Totals grow with the group, so a ward's total against the file's says nothing: use the average instead."""
    out = []
    for m in ids:
        if m.startswith("sum:"):
            m = "avg:" + m[4:]
        if m in c.f["_measures"] and m not in out:
            out.append(m)
    return out


def _defaults(c):
    taught = [m["id"] for m in c.f["measures"] if not m.get("auto") and m["id"] != "rows" and m.get("format") != "count"]
    return taught[:5] or [m["id"] for m in c.f["measures"] if m["id"].startswith("avg:")][:5]


def _rate(c, mid, where):
    """A figure comparable across groups of any size: averages as they are; counts as a share of the rows (%)."""
    v, n, blank = c.value(mid, where)
    if c.units.get(mid) == "count":
        return (100.0 * v / n if n and v is not None else None), n, "percent", f"{c.label(mid)} (% of {c.f['row_noun']})"
    return v, n, c.units.get(mid), c.label(mid)


def _profile(c, tgt, pool, question, actions, got):
    col, val = tgt
    rows, table = [], []
    for mid in pool:
        tv, tn, unit, lab = _rate(c, mid, _where(col, [val]))
        av, an, _, _ = _rate(c, mid, f"{_q(col)} IS NOT NULL")
        d = (100.0 * (tv - av) / abs(av)) if (tv is not None and av not in (None, 0)) else None
        rows.append({"Figure": lab, "Difference from the whole file (%)": None if d is None else round(d, 1),
                     "label": "n/a" if d is None else f"{'+' if d >= 0 else ''}{round(d)}%"})
        table.append([lab, _fmt(tv, unit), _fmt(av, unit), "n/a" if d is None else f"{'+' if d >= 0 else ''}{round(d)}%"])
    ok = [r for r in rows if r["Difference from the whole file (%)"] is not None]
    from lib import vlchart
    vl = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "config": vlchart.CONFIG, "background": "white",
          "title": f"{val} compared with all {c.f['row_noun']} in the file (% difference)",
          "width": 460, "height": max(60, 26 * len(ok)), "data": {"values": ok},
          "encoding": {"y": {"field": "Figure", "type": "nominal", "sort": None, "title": None},
                       "x": {"field": "Difference from the whole file (%)", "type": "quantitative",
                             "title": "Difference from the whole file (%)"}},
          "layer": [{"mark": {"type": "bar"},
                     "encoding": {"color": {"condition": {"test": "datum['Difference from the whole file (%)'] >= 0",
                                                          "value": "#C2552D"}, "value": vlchart.BLUE}}},
                    {"mark": {"type": "text", "align": "left", "dx": 4, "fontSize": 11},
                     "encoding": {"text": {"field": "label"}}},
                    {"data": {"values": [{"z": 0}]}, "mark": {"type": "rule", "color": "#555"},
                     "encoding": {"x": {"field": "z", "type": "quantitative"}, "y": None}}]}
    path = _render(c, vl, ["auto-profile", col, val, pool])
    rc = R.receipt(path, vl, requested=["Difference from the whole file (%)"], kind="diverging_bar_pct_diff_from_mean",
                   baseline=f"all {c.f['row_noun']} in the file (each counts once)")
    missing = [r["Figure"] for r in rows if r["Difference from the whole file (%)"] is None]
    if missing:
        rc["omitted_from_chart"] = [{"fields": missing, "reason": "no value to compare (blank or zero average)"}]
    tn = c.value("rows", _where(col, [val]))[0] if "rows" in c.f["_measures"] else None
    lines = [f"{val} ({_fmt(tn, 'count')} {c.f['row_noun']}) against all {c.f['row_noun']} in the file:"] + \
            [f"- {a}: {b} vs {cc} ({d})" for a, b, cc, d in table]
    out = {"answer": "\n".join(lines), "table": {"columns": ["Figure", val, f"All {c.f['row_noun']}", "Difference"],
                                                  "rows": table},
           "render_receipt": rc, "say_to_user": SAY + " Say that these differences go together with the group; they "
                                                      "don't show causes.",
           "gate": actions, "ran": {"profile": pool, "target": {col: val}}}
    if path:
        out["chart_markdown"] = f"![{vl['title']}]({path})"
    return out


def _with_baseline(c, tgt, mid, question, actions, got):
    col, val = tgt
    unit = c.units.get(mid)
    rows = c.sql(f"SELECT {_q(col)}, {c.f['_measures'][mid]['sql']}, count(*) FROM {_q(c.table)} WHERE {_q(col)} IS "
                 f"NOT NULL GROUP BY 1 ORDER BY 2 DESC NULLS LAST")
    av, an, _ = c.value(mid, f"{_q(col)} IS NOT NULL")
    lab = c.label(mid)
    from lib import vlchart
    vals = [{col: str(r[0]), lab: float(r[1]) if isinstance(r[1], (int, float)) else None, "t": _fmt(r[1], unit),
             "is": "target" if r[0] == val else "other"} for r in rows]
    vl = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "config": vlchart.CONFIG, "background": "white",
          "title": f"{lab} by {col}, {val} in orange; line = all {c.f['row_noun']}",
          "width": 480, "height": max(60, 24 * len(vals)), "data": {"values": vals},
          "encoding": {"y": {"field": col, "type": "nominal", "sort": [v[col] for v in vals], "title": None},
                       "x": {"field": lab, "type": "quantitative", "title": lab}},
          "layer": [{"mark": {"type": "bar"}, "encoding": {"color": {
                        "condition": {"test": "datum['is'] === 'target'", "value": "#C2552D"}, "value": vlchart.BLUE}}},
                    {"mark": {"type": "text", "align": "left", "dx": 4, "fontSize": 11}, "encoding": {"text": {"field": "t"}}},
                    {"data": {"values": [{"ref": av}]}, "mark": {"type": "rule", "strokeDash": [4, 3], "color": "#555"},
                     "encoding": {"x": {"field": "ref", "type": "quantitative"}, "y": None}}]}
    path = _render(c, vl, ["auto-base", col, val, mid])
    rc = R.receipt(path, vl, requested=[lab], units_of={lab: unit},
                   baseline=f"dashed line = all {c.f['row_noun']} in the file: {_fmt(av, unit)}")
    tv = next((r[1] for r in rows if r[0] == val), None)
    rank = next((i + 1 for i, r in enumerate(rows) if r[0] == val), None)
    ans = (f"{lab}: {val} {_fmt(tv, unit)}; all {c.f['row_noun']} in the file {_fmt(av, unit)} ({an}). "
           f"{val} is number {rank} of {len(rows)} {col}s.")
    out = {"answer": ans, "render_receipt": rc, "say_to_user": SAY, "gate": actions,
           "ran": {"measures": [mid], "group_by": [col], "baseline": "all rows"}}
    if path:
        out["chart_markdown"] = f"![{vl['title']}]({path})"
    return out


def _render(c, vl, key):
    from lib import vlchart
    from sites.files import tools as T
    k = hashlib.sha1(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:10]
    out = os.path.join(T._charts_dir(c.file), f"auto-{k}.svg")
    got = vlchart.svg(vl, out)
    if got and os.environ.get("IDLI_FAULT") == "drop_series":
        from lib.careful import _drop_after_first_panel
        _drop_after_first_panel(got)
    return got
