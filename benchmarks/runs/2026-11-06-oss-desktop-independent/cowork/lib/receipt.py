"""What a chart actually shows, and checks of what a model says about it. Shared by the two grounded 9B modes
(lib/careful.py, lib/auto.py; benchmarks/runs/2026-11-13-grounded-9b).

  read_svg(path)            -> the marks drawn in a chart SVG (vl-convert labels each one), grouped by panel
  receipt(svg, vl, ...)     -> the render receipt: chart type, bars on screen, panels with axes, categories and
                               values shown, measures asked for but not drawn, and why
  units(form)               -> measure id -> unit (inr, count, percent, score, number) from the taught format
  PUSHBACK                  -> the person says the chart isn't what they see
  check_reply(text, rcpt)   -> claims in a reply that the receipt doesn't support
  scrub_escalation(text)    -> the text without offers of Claude or another model

The receipt is read from the drawn file, not from the plan: a renderer that drops a series shows up here.
"""
import html
import json
import re

UNIT_OF_FORMAT = {"inr": "inr", "count": "count", "percent": "percent", "number": "number"}
UNIT_WORDS = {"inr": "rupees", "count": "count of rows", "percent": "percent", "score": "score",
              "number": "number", "months": "months"}


def units(form):
    """measure id -> unit. A taught format wins; a 'number' whose label says score / months gets that unit, so
    a 1-10 score and a count of months never share an axis."""
    out = {}
    for mid, m in (form or {}).get("_measures", {}).items():
        u = UNIT_OF_FORMAT.get(m.get("format") or "", "number")
        lab = (m.get("label") or "").lower()
        if u == "number" and "score" in lab:
            u = "score"
        elif u == "number" and "month" in lab:
            u = "months"
        elif u == "number" and ("(rs" in lab or "rs)" in lab or "rupee" in lab):
            u = "inr"
        out[mid] = u
    return out


def _fields(label):
    out = {}
    for part in html.unescape(label).split("; "):
        k, sep, v = part.partition(": ")
        if sep:
            out[k.strip()] = v.strip()
    return out


def read_svg(path):
    """[{panel, kind, fields}] for every rect / symbol / line mark in the SVG, in drawing order."""
    try:
        s = open(path).read()
    except OSError:
        return []
    marks = []
    for g in re.finditer(r'<g class="mark-(\w+) role-mark (\w+)"', s):
        kind, panel = g.group(1), g.group(2)
        if kind not in ("rect", "symbol", "line"):
            continue
        nxt = s.find('<g class="mark-', g.end())
        chunk = s[g.end(): nxt if nxt > 0 else len(s)]
        for p in re.finditer(r'<path[^>]*?aria-label="([^"]*)"', chunk):
            marks.append({"panel": panel, "kind": kind, "fields": _fields(p.group(1))})
    return marks


def _panels(vl):
    """[(group field, measure field, measure title, orientation)] in drawing order, from the Vega-Lite spec that drew
    it. orientation: 'horizontal' = bars run left to right (categories down the left, values along the bottom)."""
    if not isinstance(vl, dict):
        return []
    if vl.get("vconcat") or vl.get("hconcat"):
        out = []
        for sub in vl.get("vconcat") or vl.get("hconcat"):
            out += _panels(sub)
        return out
    enc = vl.get("encoding") or {}
    x, y = enc.get("x") or {}, enc.get("y") or {}
    if x.get("type") == "quantitative" and y.get("type") != "quantitative":
        return [(y.get("field"), x.get("field"), x.get("title") or x.get("field"), "horizontal")]
    if y.get("type") == "quantitative" and x.get("type") != "quantitative":
        return [(x.get("field"), y.get("field"), y.get("title") or y.get("field"), "vertical")]
    if x.get("type") == "quantitative" and y.get("type") == "quantitative":
        return [("(points)", None, None, "points")]
    return [(y.get("field"), (enc.get("color") or {}).get("field"), None, "grid")] if enc else []


def receipt(svg_path, vl, requested=None, labels=None, kind=None, baseline=None, why_no_chart=None, units_of=None):
    """The render receipt. requested: measure labels asked for; labels: id -> label (for units_of ids)."""
    requested = list(requested or [])
    if not svg_path:
        return {"chart_rendered": False, "chart_type": None, "total_bars_on_screen": 0, "panels": [],
                "omitted_from_chart": ([{"fields": requested, "reason": why_no_chart or "no chart was drawn"}]
                                       if requested else []),
                "why_no_chart": why_no_chart or "no chart was drawn"}
    marks = read_svg(svg_path)
    plan = _panels(vl)
    panels, by = [], {}
    for mk in marks:
        by.setdefault(mk["panel"], []).append(mk)
    for i, (pid, ms) in enumerate(by.items()):
        g, m, title, orient = plan[i] if i < len(plan) else (None, None, None, None)
        cats, vals = [], {}
        for mk in ms:
            f = mk["fields"]
            cat = f.get(g) if g in f else next((v for k, v in f.items() if k != m), None)
            val = f.get(m) if m in f else None
            cats.append(cat)
            if cat is not None:
                vals[cat] = val
        cat_axis = {"field": g, "shows": "categories", "categories_shown": cats, "category_count": len(cats)}
        val_axis = {"field": m, "shows": "values", "label": title, "unit": (units_of or {}).get(m)}
        horiz = orient == "horizontal"
        panels.append({"orientation": ("bars run left to right" if horiz else "bars run bottom to top"
                                       if orient == "vertical" else orient),
                       "x_axis": val_axis if horiz else cat_axis, "y_axis": cat_axis if horiz else val_axis,
                       "category": cat_axis, "measure": val_axis,
                       "marks": ms[0]["kind"] if ms else None, "bars": sum(1 for x in ms if x["kind"] == "rect"),
                       "values_shown": vals})
    drawn = {p["measure"]["field"] for p in panels}
    omitted = [r for r in requested if r not in drawn]
    bars = sum(p["bars"] for p in panels)
    if kind is None:
        kind = ("bar_single_series" if len(panels) == 1 and panels[0]["marks"] == "rect" else
                "bar_panels" if panels and all(p["marks"] == "rect" for p in panels) else
                "points" if panels and panels[0]["marks"] == "symbol" else "line" if panels else "empty")
    out = {"chart_rendered": bool(panels), "chart_type": kind, "total_bars_on_screen": bars,
           "series_count": len(panels), "grouped_bars": False, "panels": panels,
           "omitted_from_chart": ([{"fields": omitted, "reason": "not drawn (more figures than panels, or the "
                                                                  "renderer left them out); they are in the answer"}]
                                  if omitted else [])}
    if baseline:
        out["baseline"] = baseline
    return out


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return v
    return str(int(x)) if x.is_integer() else str(round(x, 2))


def describe(rcpt):
    """The receipt as two or three plain sentences: what is on screen. Code, not a model."""
    if not rcpt or not rcpt.get("chart_rendered"):
        why = (rcpt or {}).get("why_no_chart") or "no chart was drawn"
        return f"No chart is drawn for this answer ({why})."
    parts = []
    for i, p in enumerate(rcpt["panels"]):
        cats = [c for c in p["category"]["categories_shown"] if c is not None]
        unit = p["measure"].get("unit")
        head = (f"Panel {i + 1}: " if len(rcpt["panels"]) > 1 else "")
        shown = ", ".join(f"{c} {_num(p['values_shown'].get(c))}" for c in cats[:8]) + (" ..." if len(cats) > 8 else "")
        xa = "x-axis (along the bottom)"
        ya = "y-axis (down the left side)"
        cat_on, val_on = (ya, xa) if p["x_axis"] is p["measure"] else (xa, ya)
        parts.append(f"{head}{p['bars']} bar{'s' if p['bars'] != 1 else ''}, one per {p['category']['field']} "
                     f"({shown}); {p['category']['field']} is on the {cat_on}, and "
                     f"{p['measure']['label'] or p['measure']['field']}"
                     + (f" ({UNIT_WORDS.get(unit, unit)})" if unit else "") + f" is on the {val_on}.")
    if rcpt.get("baseline"):
        parts.append(f"Reference: {rcpt['baseline']}.")
    for o in rcpt.get("omitted_from_chart") or []:
        parts.append("Not on the chart: " + ", ".join(o["fields"]) + f" ({o['reason']}).")
    return " ".join(parts)


PUSHBACK = re.compile(r"(?i)\b(only (see|seeing|one|a single)|single (blue )?bar|just (one|a) bar|one (blue )?bar|"
                      r"where (is|are) (the )?(other|rest)|(chart|graph|it) (doesn'?t|does not|isn'?t) show|"
                      r"not what i('?m| am) seeing|i don'?t see|can'?t see|that'?s not (right|what)|wrong (axis|chart)|"
                      r"how are you combining|that'?s wrong|doesn'?t match|you said .* but)\b")
READ_CHART = re.compile(r"(?i)\b(x[ -]?axis|y[ -]?axis|axes|axis|what (is|does) (the|this|that) (graph|chart|plot)|"
                        r"graph (you showed|is telling)|chart (is telling|you showed)|what am i looking at|"
                        r"legend|what do the bars)\b")


def check_reply(text, rcpt, known_categories=()):
    """Chart claims in a reply that the receipt contradicts. Returns a list of short problems (empty: fine)."""
    if not text:
        return []
    bad = []
    t = text.lower()
    if not rcpt or not rcpt.get("chart_rendered"):
        if re.search(r"(?i)\b(the|this) (chart|graph|bar chart|plot) (shows|has|compares|displays)\b", text):
            bad.append("describes a chart, but no chart was drawn")
        return bad
    bars = rcpt.get("total_bars_on_screen", 0)
    if re.search(r"\bgrouped\b|\bside[- ]by[- ]side\b|\bmultiple (metrics|measures|series) (on|as)\b", t) and \
            rcpt.get("series_count", 1) <= 1:
        bad.append("says the bars are grouped / several series; the chart has one series")
    m = re.search(r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten) bars?\b", t)
    words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else words[m.group(1)]
        if n != bars:
            bad.append(f"says {n} bars; the chart has {bars}")
    shown = {str(c).lower() for p in rcpt["panels"] for c in p["category"]["categories_shown"] if c}
    for c in known_categories:
        c2 = str(c).lower()
        if c2 and c2 not in shown and re.search(r"\b" + re.escape(c2) + r"\b", t) and \
                re.search(r"(?i)\b(chart|graph|bar|axis)\b", text):
            bad.append(f"names {c} as on the chart; it isn't")
            break
    for which in ("x", "y"):
        axis = re.search(r"(?i)\b" + which + r"[- ]?axis\b[^a-z0-9]{0,6}(?:\([^)]*\))?[^a-z0-9]{0,6}(?:is |shows |has |lists |= )?"
                         r"(?:the )?([^.;\n]{3,60})", text)
        if not axis:
            continue
        said = axis.group(1).lower()
        real = [p[which + "_axis"] for p in rcpt["panels"]]
        words = set()
        for a in real:
            words |= {w for w in re.findall(r"[a-z]{4,}", str(a.get("label") or a.get("field") or "").lower())}
            if a.get("shows") == "categories":
                words |= {"categor", "categories", "wards", "groups", "figure", "figures", "metric", "metrics",
                          "statistic", "names"} if a.get("field") == "Figure" else {"categories", "names"}
        other = [p["y_axis" if which == "x" else "x_axis"] for p in rcpt["panels"]]
        other_words = set()
        for a in other:
            other_words |= {w for w in re.findall(r"[a-z]{4,}", str(a.get("label") or a.get("field") or "").lower())}
        hit = any(w in said for w in words)
        wrong = any(w in said for w in other_words - words)
        if wrong and not hit:
            bad.append(f"{which}-axis described as '{axis.group(1).strip()[:40]}'; on screen the {which}-axis is "
                       + ", ".join(str(a.get('label') or a.get('field')) for a in real))
    return bad


ESCALATION = re.compile(r"(?i)[^.\n]*\b(claude|gpt|openai|anthropic|a (bigger|stronger|larger) model|another model)\b"
                        r"[^.\n]*[.\n]?")


def scrub_escalation(text):
    return re.sub(r"\s{2,}", " ", ESCALATION.sub("", text or "")).strip()


def mentions_escalation(text):
    return bool(ESCALATION.search(text or ""))


def dumps(x):
    return json.dumps(x, ensure_ascii=False)
