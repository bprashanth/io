"""Careful: the 9B fills a typed, partial intent; code validates it, asks when a needed detail is missing, runs a
typed procedure, records what was done and drawn (a manifest), and writes the reply from the manifest.

Proposal "Reliable Conversational Spreadsheet Analysis" (benchmarks/runs/2026-11-13-grounded-9b). Used when the
chat's model is idli-9b-careful: lib/modes.py adds pipeline="careful" to file_ask, and routes follow-ups about the
chart (READ / VERIFY / RE_RENDER) to read_chart / verify_chart / as_table here, from the manifest in the chat.

  ask(files, file, question, chart=False, thread=None) -> tool result {reply, manifest, card?, chart_markdown?}

No model writes numbers or chart descriptions: the 9B only parses intent; the reply is code's.
"""
import hashlib
import json
import os
import re
import time
import urllib.request

from lib import receipt as R

INTENTS = ["DESCRIBE", "COMPARE", "RANK", "DISTRIBUTION", "TREND", "EXPLAIN_DIFFERENCE", "INVESTIGATE", "LIST",
           "DEFINE", "OTHER"]
PROMPT = """You read a question about a spreadsheet and fill a typed intent. Code does all the work; you only
classify. Never guess what the person didn't say: leave it empty and list it in `unresolved`.

- intent: DESCRIBE (a figure), COMPARE (a group against others), RANK (order groups), DISTRIBUTION (spread, typical
  household, outliers), TREND (over time), EXPLAIN_DIFFERENCE ("why is X high/low"), INVESTIGATE (a follow-up asking
  what might explain an earlier difference: "why might it be higher?", "could income explain it?"), LIST (which rows),
  DEFINE (what a figure means or how it is worked out: "what is X?", "how is X calculated?", "did you divide"),
  OTHER.
- target: the one group the question is about ({"column": filter column, "values": [value]}), or null.
- measures: figure ids the person named or clearly meant ("debt" -> a debt figure). If they say high / low / bad /
  struggling without naming a figure, and the active analysis below doesn't name one, leave measures [] and put
  "measure" in unresolved. Follow-ups ("it", "that", "now median", "instead") keep the active analysis's figure
  unless the question changes it.
- candidates: up to 4 figure ids the person most likely means when `measures` is empty (for a choice to show them).
- measure_named: true only if the person's own words name or clearly mean those figures, or the active analysis does.
- baseline: other_groups (the rest), all_rows, none, or unspecified.
- group_by: breakdown ids, only if asked ("by ward", "across wards", "per ward").
- refers_to_previous: true if the question builds on the active analysis.
- chart: true if they ask for a chart/graph/plot/picture/visualise."""


def _schema(form):
    mids = [m["id"] for m in form["measures"]]
    gids = [g["id"] for g in form["group_by"]] or ["_none"]
    cols = [x["column"] for x in form["filters"]] or ["_none"]
    return {"type": "object", "additionalProperties": False,
            "required": ["intent", "target", "measures", "candidates", "measure_named", "baseline", "group_by",
                         "refers_to_previous", "chart", "unresolved"],
            "properties": {
                "intent": {"enum": INTENTS},
                "target": {"anyOf": [{"type": "null"}, {"type": "object", "additionalProperties": False,
                                                        "required": ["column", "values"],
                                                        "properties": {"column": {"enum": cols},
                                                                       "values": {"type": "array", "maxItems": 3,
                                                                                  "items": {"type": "string"}}}}]},
                "measures": {"type": "array", "maxItems": 4, "items": {"enum": mids}},
                "candidates": {"type": "array", "maxItems": 4, "items": {"enum": mids}},
                "measure_named": {"type": "boolean"},
                "baseline": {"enum": ["other_groups", "all_rows", "none", "unspecified"]},
                "group_by": {"type": "array", "maxItems": 2, "items": {"enum": gids}},
                "refers_to_previous": {"type": "boolean"},
                "chart": {"type": "boolean"},
                "unresolved": {"type": "array", "maxItems": 4,
                               "items": {"enum": ["measure", "comparison", "period", "entity"]}}}}


def _brief(f):
    def vals(x):
        v = x.get("values") or []
        return v if len(v) <= 15 else v[:15] + [f"... {len(v) - 15} more"]
    return {"row_noun": f["row_noun"], "summary": f.get("summary", ""),
            "measures": {m["id"]: m["label"] for m in f["measures"]},
            "group_by": {g["id"]: g["label"] for g in f["group_by"]},
            "filters": {x["column"]: ({"label": x["label"], "values": vals(x)} if x["kind"] == "choice" else
                                      {"label": x["label"], "kind": x["kind"]}) for x in f["filters"]},
            "date_columns": f.get("date_columns") or []}


def _llm(prompt, schema):
    from lib import muse
    body = {"model": os.environ.get("IDLI_SPEC_MODEL", "idli-9b"), "temperature": 0, "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "intent", "schema": schema}}}
    req = urllib.request.Request(muse.base_url() + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer none", **muse.headers()})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=240) as r:
        text = json.load(r)["choices"][0]["message"]["content"] or "{}"
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    return (json.loads(m.group(0)) if m else {}), round(time.time() - t0, 1)


# ---------------------------------------------------------------- state: this chat's analyses, per file
_state = {}  # file -> {"analyses": [manifest...], "pending": {question, intent}}


def _st(file):
    return _state.setdefault(file, {"analyses": [], "pending": None})


def _fmt(v, unit):
    from lib.formkit import indian
    if v is None:
        return "none"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if unit == "inr":
        return "Rs " + indian(round(v) if isinstance(v, float) and abs(v) >= 100 else v)
    if unit == "percent":
        return f"{round(v, 1)}%"
    if isinstance(v, float):
        return str(round(v, 2))
    return indian(v) if isinstance(v, int) else str(v)


def _match_value(x, v):
    """The filter's known value for what the 9B wrote ('yerawada' -> 'Yerawada Ward'), or None."""
    known = x.get("values") or []
    low = str(v).strip().lower()
    for k in known:
        if str(k).strip().lower() == low:
            return k
    hits = [k for k in known if low and (low in str(k).lower() or str(k).lower() in low)]
    if len(hits) == 1:
        return hits[0]
    import difflib  # typos: "yearwada" -> "Yerawada Ward"
    first = {str(k).lower().split()[0]: k for k in known if str(k).strip()}
    for cand in (low, low.split()[0] if low.split() else low):
        got = difflib.get_close_matches(cand, [str(k).lower() for k in known], n=1, cutoff=0.8) or \
            difflib.get_close_matches(cand, list(first), n=1, cutoff=0.75)
        if got:
            return next((k for k in known if str(k).lower() == got[0]), None) or first.get(got[0])
    return None


def _sql_cols(f, mid):
    sql = (f["_measures"].get(mid) or {}).get("sql", "")
    return [c for c in (f.get("_kinds") or {}) if re.search(r"\b" + re.escape(c) + r"\b", sql)]


def _q(c):
    return '"' + str(c).replace('"', '""') + '"'


def _where(col, vals, negate=False):
    if not col or not vals:
        return "TRUE"
    inner = ", ".join("'" + str(v).replace("'", "''") + "'" for v in vals)
    return f"{_q(col)} {'NOT ' if negate else ''}IN ({inner})"


class Ctx:
    def __init__(self, files, file, tab=None):
        self.files, self.file = files, file
        e = files.open(file)
        self.tab = tab or next(iter(e["forms"]))
        self.f = e["forms"][self.tab]
        self.e = e
        self.units = R.units(self.f)

    def sql(self, q):
        with self.files.lock:
            return self.e["con"].execute(q).fetchall()

    @property
    def table(self):
        return self.e["built"][self.tab]["table"]

    def value(self, mid, where="TRUE"):
        """A measure over the rows in `where`, its row count, and the rows where its inputs are blank."""
        m = self.f["_measures"][mid]
        cols = _sql_cols(self.f, mid)
        miss = " + ".join(f"count(*) FILTER (WHERE {_q(c)} IS NULL)" for c in cols) or "0"
        v, n, blank = self.sql(f"SELECT {m['sql']}, count(*), {miss} FROM {_q(self.table)} WHERE {where}")[0]
        return (float(v) if isinstance(v, (int, float)) else v), int(n), int(blank or 0)

    def label(self, mid):
        return self.f["_measures"][mid]["label"]


# ---------------------------------------------------------------- the procedures
def _compare(c, mid, col, target, chart):
    """Target vs the other groups: every group's figure (bars, target marked) and the rest taken together
    (household-weighted), with the counts behind each. Returns (lines, manifest parts, chart path, vl)."""
    unit = c.units.get(mid)
    rows = c.sql(f"SELECT {_q(col)}, {c.f['_measures'][mid]['sql']}, count(*) FROM {_q(c.table)} "
                 f"WHERE {_q(col)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC NULLS LAST")
    tv, tn, tb = c.value(mid, _where(col, target))
    rv, rn, rb = c.value(mid, _where(col, target, negate=True) + f" AND {_q(col)} IS NOT NULL")
    others = [float(r[1]) for r in rows if r[0] not in target and isinstance(r[1], (int, float))]
    eq = sum(others) / len(others) if others else None
    rank = next((i + 1 for i, r in enumerate(rows) if r[0] in target), None)
    tname = ", ".join(target)
    noun = c.f["row_noun"]
    lines = [f"{tname}: {_fmt(tv, unit)} ({tn} {noun}" + (f", {tb} with a blank value" if tb else "") + ")",
             f"The other {len(rows) - len(target)} {_plural(c, col)}' "
             f"{noun} together: {_fmt(rv, unit)} ({rn} {noun}" + (f", {rb} with a blank value" if rb else "") + ")",
             f"{tname} is number {rank} of {len(rows)}."]
    if eq is not None and rv is not None and abs(eq - rv) > max(abs(rv) * 0.02, 0.01):
        lines.append(f"(Averaging the other groups' figures with each group counted once gives {_fmt(eq, unit)}; "
                     f"the line above counts every {noun.rstrip('s')} once.)")
    parts = {"values": {tname: tv, "others": rv, **{str(r[0]): r[1] for r in rows}},
             "counts": {tname: tn, "others": rn, **{str(r[0]): r[2] for r in rows}},
             "missing": {tname: tb, "others": rb}, "rank": rank, "groups": len(rows),
             "baseline": {"kind": "other_groups", "weighting": f"each {noun.rstrip('s')} counts once",
                          "value": rv, "n": rn}}
    path = vl = None
    if chart:
        path, vl = _bars_chart(c, mid, col, rows, target, rv)
    return lines, parts, path, vl


def _plural(c, col):
    lab = next((x["label"] for x in c.f["filters"] if x["column"] == col), col)
    return str(lab).lower().rstrip("s") + "s"


def _bars_chart(c, mid, col, rows, target, ref):
    from lib import vlchart
    lab = c.label(mid)
    unit = c.units.get(mid)
    vals = [{col: str(r[0]), lab: float(r[1]) if isinstance(r[1], (int, float)) else None,
             lab + " ": _fmt(r[1], unit), "is": "target" if r[0] in target else "other"} for r in rows]
    order = [v[col] for v in vals]
    vl = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "config": vlchart.CONFIG, "background": "white",
          "title": f"{lab} by {col}: {', '.join(target)} marked; line = the other groups together",
          "width": 520, "height": max(60, 24 * len(vals)), "data": {"values": vals},
          "encoding": {"y": {"field": col, "type": "nominal", "sort": order, "title": None},
                       "x": {"field": lab, "type": "quantitative", "title": lab}},
          "layer": [{"mark": {"type": "bar"}, "encoding": {"color": {
                        "condition": {"test": "datum['is'] === 'target'", "value": "#C2552D"}, "value": vlchart.BLUE}}},
                    {"mark": {"type": "text", "align": "left", "dx": 4, "fontSize": 11},
                     "encoding": {"text": {"field": lab + " "}}}]}
    if ref is not None:
        vl["layer"].append({"data": {"values": [{"ref": ref}]}, "mark": {"type": "rule", "strokeDash": [4, 3],
                                                                         "color": "#555"},
                            "encoding": {"x": {"field": "ref", "type": "quantitative"}}})
    return _render(c, vl, ["careful", mid, col, target])


def _render(c, vl, key):
    from lib import vlchart
    from sites.files import tools as T
    k = hashlib.sha1(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:10]
    out = os.path.join(T._charts_dir(c.file), f"careful-{k}.svg")
    got = vlchart.svg(vl, out)
    if got and os.environ.get("IDLI_FAULT") == "drop_series":  # fault injection: a renderer that loses panels
        _drop_after_first_panel(got)
    return got, vl


def _drop_after_first_panel(path):
    s = open(path).read()
    first = re.search(r'<g class="mark-rect role-mark (\w+)"', s)
    if first:
        s = re.sub(r'(<g class="mark-rect role-mark (?!' + first.group(1) + r')\w+"[^>]*>)(.*?)(</g>)',
                   lambda m: m.group(1) + m.group(3), s, flags=re.S)
        open(path, "w").write(s)


def _distribution(c, mid, col, target):
    """The spread behind an average: median, quartiles, the largest values, and how much the top two move it."""
    m = c.f["_measures"][mid]
    cols = _sql_cols(c.f, mid)
    if len(cols) != 1 or not m["sql"].lower().startswith("avg("):
        return None
    x = cols[0]
    w = _where(col, target)
    got = c.sql(f"SELECT median({_q(x)}), quantile_cont({_q(x)}, 0.25), quantile_cont({_q(x)}, 0.75), "
                f"avg({_q(x)}), count({_q(x)}), max({_q(x)}) FROM {_q(c.table)} WHERE {w}")[0]
    top = [r[0] for r in c.sql(f"SELECT {_q(x)} FROM {_q(c.table)} WHERE {w} AND {_q(x)} IS NOT NULL "
                               f"ORDER BY 1 DESC LIMIT 2")]
    rest = c.sql(f"SELECT avg({_q(x)}) FROM (SELECT {_q(x)} FROM {_q(c.table)} WHERE {w} AND {_q(x)} IS NOT NULL "
                 f"ORDER BY 1 DESC OFFSET 2)")[0][0]
    return {"median": got[0], "q1": got[1], "q3": got[2], "mean": got[3], "n": got[4], "max": got[5], "top2": top,
            "mean_without_top2": rest}


def ask(files, file, question, chart=False, tab=None):
    c = Ctx(files, file, tab)
    st = _st(file)
    active = st["analyses"][-1] if st["analyses"] else None
    pending = st.get("pending")
    if pending and re.match(r"(?i)^\s*figure:\s*", question or ""):
        # the answer to our "which figure?" card: carry on with the original question
        picked = re.sub(r"(?i)^\s*figure:\s*", "", question).strip()
        mid = next((m["id"] for m in c.f["measures"] if m["label"] == picked), None)
        intent = dict(pending["intent"], measures=[mid] if mid else [], measure_named=bool(mid),
                      unresolved=[u for u in pending["intent"].get("unresolved", []) if u != "measure"])
        question = pending["question"]
        secs = 0
        st["pending"] = None
    else:
        prompt = (PROMPT + "\n\nThe form:\n" + json.dumps(_brief(c.f), ensure_ascii=False)
                  + ("\n\nActive analysis: " + active["interpretation"] if active else "\n\nActive analysis: none")
                  + "\n\nQuestion: " + question)
        intent, secs = _llm(prompt, _schema(c.f))
    plan = validate(c, intent, active, question)
    plan["parse_secs"] = secs
    if plan.get("card"):
        st["pending"] = {"question": question, "intent": intent}
        return {"card": plan["card"], "intent": intent, "then": "AskUserQuestion with this card.",
                "reply": None}
    m = execute(c, plan, chart or bool(intent.get("chart")), question)
    st["analyses"].append(m)
    m["analysis_id"] = f"a{len(st['analyses'])}"
    out = {"reply": compose(m), "manifest": m}
    if m.get("chart_path"):
        out["chart_markdown"] = f"![{m['chart_title']}]({m['chart_path']})"
    return out


def _ambiguous(question):
    return bool(re.search(r"(?i)\b(so )?(high|low|bad|good|worse|better|struggling|poor|well|badly|stand out|"
                          r"different)\b", question or ""))


def validate(c, intent, active, question):
    """Code's checks on the 9B's intent: known ids, a figure when one is needed, a baseline for a comparison."""
    f = c.f
    plan = {"intent": intent.get("intent") or "OTHER", "notes": []}
    mids = [m for m in intent.get("measures") or [] if m in f["_measures"] and m != "rows"]
    named = bool(intent.get("measure_named")) and "measure" not in (intent.get("unresolved") or [])
    if intent.get("refers_to_previous") and active and not mids:
        mids = list(active.get("measures") or [])
        named = bool(mids)
    tgt = intent.get("target") or {}
    by = {x["column"]: x for x in f["filters"]}
    col = tgt.get("column") if tgt.get("column") in by else None
    target = []
    for v in tgt.get("values") or []:
        k = _match_value(by[col], v) if col else None
        if k is None:
            for x in f["filters"]:  # the 9B may have picked the wrong column
                if x["kind"] == "choice" and _match_value(x, v) is not None:
                    col, k = x["column"], _match_value(x, v)
                    break
        if k is None:
            groupish = sorted((x for x in f["filters"] if x["kind"] == "choice" and x.get("values")),
                              key=lambda x: len(x["values"]))
            plan["unknown_value"] = (groupish[0]["column"] if groupish else col, v)
        else:
            target.append(k)
    if target and not _mentioned(target, question) and not intent.get("refers_to_previous"):
        target, col = [], None  # the 9B added groups the person never named
    if not col and active and intent.get("refers_to_previous"):
        col, target = active.get("target_column"), list(active.get("target") or [])
    plan.update(measures=mids, target_column=col, target=target, group_by=intent.get("group_by") or [])
    if plan.get("unknown_value"):
        return plan
    need_figure = plan["intent"] in ("EXPLAIN_DIFFERENCE", "COMPARE", "RANK", "DISTRIBUTION", "INVESTIGATE")
    if plan["intent"] == "INVESTIGATE" and active:
        plan.update(measures=list(active.get("measures") or []), target_column=active.get("target_column"),
                    target=list(active.get("target") or []))
        return plan
    if need_figure and (not mids or (not named and _ambiguous(question) and len(mids) != 1)):
        opts = []
        for m in list(mids) + list(intent.get("candidates") or []) + _comparable(f):
            if m in f["_measures"] and m != "rows" and m not in opts:
                opts.append(m)
        opts = opts[:4]
        who = ", ".join(target) or "it"
        plan["card"] = {"questions": [{"header": "Which figure", "multiSelect": False,
                                       "question": f"Which figure do you mean is {_adj(question)} for {who}?",
                                       "options": [{"label": f["_measures"][m]["label"],
                                                    "description": "compare " + (who if target else "the groups")
                                                                   + " on this"} for m in opts]}]}
        return plan
    if len(mids) > 1 and plan["intent"] in ("EXPLAIN_DIFFERENCE", "COMPARE") and target:
        plan["notes"].append("one figure at a time for a comparison: the first is shown, the others are listed")
    base = intent.get("baseline") or "unspecified"
    if plan["intent"] in ("EXPLAIN_DIFFERENCE", "COMPARE") and target:
        plan["baseline"] = "other_groups" if base in ("unspecified", "other_groups", "none") else base
        if base == "unspecified":
            plan["notes"].append("compared with the other groups (assumed; say 'compare with all' to change)")
    return plan


def _mentioned(values, question):
    """Is each value named in the question (allowing typos: 'yearwada' for 'Yerawada Ward')?"""
    import difflib
    words = re.findall(r"[a-z0-9]+", (question or "").lower())
    for v in values:
        parts = [w for w in re.findall(r"[a-z0-9]+", str(v).lower()) if len(w) >= 4 and w not in ("ward", "block")]
        if parts and not any(difflib.get_close_matches(p, words, n=1, cutoff=0.75) for p in parts):
            return False
    return True


def _comparable(f):
    """Figures that compare fairly between groups of different sizes: taught averages and rates first, then the
    automatic averages. Totals and plain counts grow with the group, so they come last (never in a card)."""
    taught = [m["id"] for m in f["measures"] if not m.get("auto") and m["id"] != "rows" and m.get("format") != "count"]
    autos = [m["id"] for m in f["measures"] if m.get("auto") and m["id"].startswith("avg:")]
    return taught + autos


def _adj(q):
    m = re.search(r"(?i)\b(so )?(high|low|bad|good|worse|better|struggling|poor)\b", q or "")
    return m.group(2).lower() if m else "notable"


def execute(c, plan, chart, question):
    f, intent = c.f, plan["intent"]
    m = {"file": c.file, "tab": c.tab, "question": question, "intent": intent, "measures": plan["measures"],
         "target_column": plan.get("target_column"), "target": plan.get("target"), "notes": list(plan["notes"]),
         "requested_measures": [c.label(x) for x in plan["measures"]], "lines": [], "chart_path": None,
         "status": "ok", "time": time.strftime("%H:%M:%S")}
    if plan.get("unknown_value"):
        col, v = plan["unknown_value"]
        known = [x for x in f["filters"] if x["column"] == col][0].get("values") or []
        m.update(status="no_data", interpretation=f"'{v}' is not in this file",
                 lines=[f"There is no '{v}' in this file (nothing to show; this is not a zero). Its {col} values "
                        f"are: {', '.join(map(str, known[:12]))}."])
        m["receipt"] = R.receipt(None, None, why_no_chart="nothing to draw: no matching rows")
        return m
    col, target, mids = plan.get("target_column"), plan.get("target") or [], plan["measures"]
    if intent == "TREND":
        dates = f.get("date_columns") or []
        if not dates:
            m.update(status="cannot", interpretation="Trend · no date column in this file",
                     lines=["This file has no date column, so it can't show change over time, and I won't estimate "
                            "it. To see change, the sheet needs the same figures recorded on dated rounds (ideally "
                            "the same households each time)."])
            m["receipt"] = R.receipt(None, None, why_no_chart="no dates in the file")
            return m
    if intent == "DEFINE":
        from sites.files import tools as T
        mid = mids[0] if mids else None
        got = T.t_form_explain(c.file, c.label(mid) if mid else None)
        text = got.get("answer") or got.get("say_to_user") or got.get("error") or json.dumps(got)[:600]
        m.update(interpretation="Define · " + (c.label(mid) if mid else "the figures"), lines=[str(text)])
        if mid:
            m["lines"].append("Worked out as: " + c.f["_measures"][mid]["sql"].replace('"', ""))
        m["receipt"] = R.receipt(None, None, why_no_chart="a definition, not a chart")
        return m
    year = re.search(r"\b(19|20)\d{2}\b", question or "")
    if year and not f.get("date_columns"):
        m.update(status="no_data", interpretation=f"{year.group(0)} · this file has no dates",
                 lines=[f"This file has no date column, so I can't pick out {year.group(0)}: nothing to show (that's "
                        "no data, not a zero). Ask without the year to see what the file has."])
        m["receipt"] = R.receipt(None, None, why_no_chart="no dates in the file")
        return m
    if intent in ("COMPARE", "EXPLAIN_DIFFERENCE") and len(target) >= 2 and mids:
        intent = plan["intent"] = "COMPARE_GROUPS"  # the named groups side by side, not lumped against the rest
    if intent in ("EXPLAIN_DIFFERENCE", "COMPARE") and target and mids:
        mid = mids[0]
        lines, parts, path, vl = _compare(c, mid, col, target, True)
        m.update(parts)
        m["interpretation"] = (f"Compare · {c.label(mid)} · {', '.join(target)} vs the other {_plural(c, col)} "
                               f"({parts['baseline']['weighting']})")
        m["lines"] = lines
        if len(mids) > 1:
            m["lines"].append("Also asked: " + ", ".join(c.label(x) for x in mids[1:]) + " (ask about each to compare "
                              "it the same way).")
        if intent == "EXPLAIN_DIFFERENCE":
            m["lines"].append("This shows how far it is from the others; it doesn't say why. Ask \"why might it be "
                              "higher?\" to look at what goes with it.")
        _chart_into(m, c, path, vl, [c.label(mid)], f"{c.label(mid)} by {col}")
        if m["receipt"].get("chart_rendered"):
            m["receipt"]["baseline"] = (f"dashed line = the other {_plural(c, col)}' {c.f['row_noun']} together "
                                        f"({_fmt(parts['baseline']['value'], c.units.get(mid))}); "
                                        f"{', '.join(target)} in orange")
        return m
    if intent == "INVESTIGATE" and target and mids:
        mid = mids[0]
        unit = c.units.get(mid)
        rows = []
        for o in f["measures"]:
            if o["id"] in (mid, "rows") or o["id"].startswith("sum:") or o.get("hidden"):
                continue
            if any(k in o["id"] for k in ("lat", "lon")):
                continue
            tv, tn, _ = c.value(o["id"], _where(col, target))
            rv, rn, _ = c.value(o["id"], _where(col, target, negate=True) + f" AND {_q(col)} IS NOT NULL")
            u = c.units.get(o["id"])
            if u == "count" and tn and rn:  # a count compares as a share of the group's rows
                rows.append((o["label"] + " (share of " + f["row_noun"] + ")", f"{round(100 * tv / tn)}%",
                             f"{round(100 * rv / rn)}%"))
            else:
                rows.append((o["label"], _fmt(tv, u), _fmt(rv, u)))
        d = _distribution(c, mid, col, target)
        tname = ", ".join(target)
        m["interpretation"] = f"Investigate · {c.label(mid)} · {tname}: what goes with it, and its spread"
        m["table"] = {"columns": ["Figure", tname, f"Other {_plural(c, col)} together"], "rows": rows}
        m["lines"] = [f"What else differs for {tname} (other {_plural(c, col)} taken together):"] + \
                     [f"- {a}: {b} vs {cc}" for a, b, cc in rows]
        if d:
            m["distribution"] = d
            m["lines"].append(f"Spread of {c.label(mid)} in {tname}: median {_fmt(d['median'], unit)}, middle half "
                              f"{_fmt(d['q1'], unit)} to {_fmt(d['q3'], unit)}, highest {_fmt(d['max'], unit)}. "
                              f"Without its two highest, the average is {_fmt(d['mean_without_top2'], unit)} "
                              f"instead of {_fmt(d['mean'], unit)}.")
        m["lines"].append("These go together with it in this file; they don't show what causes what. The score's "
                          "formula isn't in the form, so it can't be split into parts.")
        m["receipt"] = R.receipt(None, None, why_no_chart="a table answers this")
        m["measures"] = [mid]
        return m
    # DESCRIBE / RANK / DISTRIBUTION / LIST / OTHER: the form, as asked
    spec = {"measures": mids if intent != "LIST" else [], "group_by": plan.get("group_by") or []}
    if intent in ("RANK", "COMPARE_GROUPS") and col and not spec["group_by"]:
        spec["group_by"] = [g["id"] for g in f["group_by"] if g.get("column", g["id"]) == col][:1] or [col]
    if target and col:
        spec["filters"] = {col: target}
    res = c.files.run(c.file, c.tab, spec)
    m["interpretation"] = (f"{intent.replace('_', ' ').title()} · " + (", ".join(m["requested_measures"]) or "rows") +
                           (f" · {col} = {', '.join(target)}" if target else "") +
                           (" · by " + ", ".join(spec["group_by"]) if spec["group_by"] else ""))
    m["lines"] = res["text"].splitlines()
    m["spec"] = spec
    m["values"] = {"rows": res["rows"][:30], "total": res.get("total")}
    m["counts"] = {"rows_returned": len(res["rows"])}
    if not res["rows"]:
        m["status"] = "no_data"
        m["lines"] = ["No rows match that (nothing to show; this is not a zero)."]
    path = vl = None
    labels = [c.label(x) for x in mids]
    if (chart or intent == "COMPARE_GROUPS") and spec["group_by"] and mids and len(res["rows"]) >= 2:
        from lib import vlchart
        vl = res.get("vl") or vlchart.spec_for(res, res["described"], spec, c.f)
        if vl:
            path, vl = _render(c, vl, ["careful", spec])
    elif chart and len(res["rows"]) < 2:
        m["notes"].append("no chart: one row is clearer as numbers")
    _chart_into(m, c, path, vl, labels, res["described"],
                why=None if path else ("one row: shown as numbers" if len(res["rows"]) < 2 else "not asked for a chart"))
    return m


def _chart_into(m, c, path, vl, labels, title, why=None):
    by_label = {c.label(k): u for k, u in c.units.items()}
    m["receipt"] = R.receipt(path, vl, requested=labels, units_of=by_label, why_no_chart=why)
    m["chart_path"] = path
    m["chart_title"] = title
    if path and m["receipt"].get("omitted_from_chart"):
        m["status"] = "partial_chart"


def compose(m):
    """The reply, from the manifest only."""
    out = [f"*{m['interpretation']}*"]
    if m.get("chart_path"):
        out.append(f"![{m['chart_title']}]({m['chart_path']})")
    out.append("\n".join(m["lines"]))
    r = m.get("receipt") or {}
    if m.get("chart_path"):
        out.append("On the chart: " + R.describe(r))
        if m["status"] == "partial_chart":
            out.append("Note: the chart doesn't show everything that was asked; the numbers above are complete.")
    for n in m.get("notes") or []:
        out.append(f"({n})")
    return "\n\n".join(x for x in out if x)


# ---------------------------------------------------------------- follow-ups about what's on screen (no 9B)
def read_chart(m, which="active"):
    if not m:
        return "There's no chart in this chat yet."
    r = m.get("receipt") or {}
    head = "The previous chart" if which == "previous" else "The chart"
    if not r.get("chart_rendered"):
        return f"{head}: none was drawn for \"{m.get('question', '')}\" ({r.get('why_no_chart', 'no chart')})."
    lines = []
    for i, p in enumerate(r["panels"]):
        pre = f"Panel {i + 1}: " if len(r["panels"]) > 1 else ""
        horiz = R.horizontal(p)
        xa, ya = (p["measure"], p["category"]) if horiz else (p["category"], p["measure"])
        def name(a):
            return a.get("label") or a.get("field")
        lines.append(f"{pre}**x-axis** (along the bottom): {name(xa)}"
                     + (f" ({R.UNIT_WORDS.get(xa.get('unit'), xa.get('unit'))})" if xa.get("unit") else "")
                     + f". **y-axis** (down the left): {name(ya)}"
                     + (f" ({R.UNIT_WORDS.get(ya.get('unit'), ya.get('unit'))})" if ya.get("unit") else "")
                     + f". {p['bars']} bars, one per {p['category']['field']}: "
                     + ", ".join(str(x) for x in p['category']['categories_shown'][:8]) + ".")
    if r.get("baseline"):
        lines.append(r["baseline"][0].upper() + r["baseline"][1:] + ".")
    return f"{head} (\"{m.get('question', '')}\"):\n\n" + "\n".join(lines)


def verify_chart(m, said, previous_reply=""):
    """The person says the chart isn't what they see: compare the receipt with what they said and what we said."""
    if not m:
        return "There's no chart in this chat to check yet."
    r = m.get("receipt") or {}
    bars = r.get("total_bars_on_screen", 0)
    facts = R.describe(r)
    out = ["I checked what was actually drawn. " + facts]
    claims = R.check_reply(previous_reply, r)
    if claims:
        out.append("What I said before was wrong: " + "; ".join(claims) + ".")
    said_one = re.search(r"(?i)\b(one|single|a) (blue )?bar\b|only (one|a single)", said or "")
    if said_one and bars > 1:
        out.append(f"The chart has {bars} bars. If you see only one, the chart may be cut off: scroll inside it, "
                   "or open the dashboard tab.")
    elif said_one and bars <= 1:
        out.append("You're right: there is one bar, so the chart compares nothing. "
                   + ("Ask me to compare it with the other groups and I'll redo it properly."
                      if m.get("intent") not in ("COMPARE", "EXPLAIN_DIFFERENCE") else ""))
    if r.get("omitted_from_chart"):
        out.append("Left off the chart: " + "; ".join(", ".join(o["fields"]) for o in r["omitted_from_chart"])
                   + ". Those numbers are in the answer.")
    return "\n\n".join(out)


def as_table(m):
    if not m:
        return "There's nothing to put in a table yet."
    if m.get("table"):
        t = m["table"]
        rows = t["rows"]
        head = "| " + " | ".join(t["columns"]) + " |\n|" + "---|" * len(t["columns"])
        return head + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in rows)
    vals, counts = m.get("values") or {}, m.get("counts") or {}
    if isinstance(vals, dict) and "rows" in vals:
        rows = vals["rows"]
        if not rows:
            return "No rows to show."
        cols = list(rows[0])
        return ("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n" +
                "\n".join("| " + " | ".join("" if r.get(k) is None else str(r.get(k)) for k in cols) + " |"
                          for r in rows))
    lab = (m.get("requested_measures") or ["Figure"])[0]
    lines = [f"| {m.get('target_column') or 'Group'} | {lab} | Rows |", "|---|---|---|"]
    for k, v in vals.items():
        lines.append(f"| {k} | {'' if v is None else round(v, 2) if isinstance(v, float) else v} | {counts.get(k, '')} |")
    return f"*{m['interpretation']}* (same numbers, as a table)\n\n" + "\n".join(lines)
