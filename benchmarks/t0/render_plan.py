#!/usr/bin/env python3
"""Deterministic renderer for the T0 plan contract.

The model never draws and never states a number. It returns a PLAN:

{
  "title": "...", "subtitle": "...",
  "panels": [
    {"id": "p1", "kind": "kpi",   "title": "...", "sql": "SELECT ... one row one numeric", "unit": "%"},
    {"id": "p2", "kind": "bar",   "title": "...", "sql": "SELECT label, value ...", "x": "label", "y": ["value"]},
    {"id": "p3", "kind": "line",  "title": "...", "sql": "SELECT period, value ...", "x": "period", "y": ["value"], "series": "group?"},
    {"id": "p4", "kind": "table", "title": "...", "sql": "SELECT ..."},
    {"id": "p5", "kind": "stacked_bar", ...}, {"kind": "scatter", ...}, {"kind": "pie", ...}
  ],
  "narrative": "optional markdown with {{p1}} placeholders (report mode)"
}

Every figure on the page comes from executing the panel SQL locally; the
renderer formats, lays out and protects against clipping (label wrapping,
top-N with an 'others' note, ellipsis, width-aware ticks). Two templates:
"dashboard" (KPI row + chart grid + tables) and "report" (narrative first,
figures as exhibits). All self-contained HTML, no external requests.
"""

from __future__ import annotations

import html
import json
import math
import re
from typing import Any

PALETTE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569"]
MAX_BARS = 20
MAX_TABLE_ROWS = 60


def esc(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def fmt_num(v: Any, unit: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        if isinstance(v, float) and not math.isfinite(v):
            return "—"
        av = abs(v)
        if av >= 1e7:
            s = f"{v / 1e7:.2f} Cr"
        elif av >= 1e5:
            s = f"{v / 1e5:.2f} L"
        elif float(v).is_integer():
            s = f"{int(v):,}"
        elif av >= 100:
            s = f"{v:,.0f}"
        elif av >= 1 or av == 0:
            s = f"{v:,.2f}".rstrip("0").rstrip(".")
        else:
            s = f"{v:.3g}"
        return f"{s}{unit}" if unit in ("%",) else (f"{s} {unit}".strip())
    return str(v)


def short(label: Any, n: int = 18) -> str:
    s = "" if label is None else str(label)
    return s if len(s) <= n else s[: n - 1] + "…"


def ticks(max_value: float, count: int = 4) -> list[float]:
    if max_value <= 0:
        return [0.0]
    raw = max_value / count
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if max_value / step <= count:
            break
    return [i * step for i in range(int(math.ceil(max_value / step)) + 1)]


def svg_bar(rows: list[dict], x: str, ys: list[str], unit: str = "", stacked: bool = False, width: int = 640, height: int = 320) -> str:
    rows = [r for r in rows if r.get(x) is not None]
    note = ""
    if len(rows) > MAX_BARS:
        note = f"Showing the first {MAX_BARS} of {len(rows)} {x} values."
        rows = rows[:MAX_BARS]
    if not rows or not ys:
        return "<p class=empty>No rows to chart.</p>"
    left, right, top, bottom = 56, 16, 16, 64
    cw, ch = width - left - right, height - top - bottom
    vals = []
    for r in rows:
        nums = [float(r.get(y) or 0) for y in ys]
        vals.append(sum(nums) if stacked else max(nums))
    vmax = max(vals + [0.0])
    vmin = min(min(float(r.get(y) or 0) for y in ys) for r in rows)
    tk = ticks(max(vmax, abs(vmin)))
    top_v = tk[-1] if tk else 1
    if vmin < 0:
        top_v = max(top_v, abs(vmin))
    scale = ch / (top_v * (2 if vmin < 0 else 1)) if top_v else 1
    zero_y = top + ch / 2 if vmin < 0 else top + ch
    n = len(rows)
    group_w = cw / n
    bar_w = group_w * 0.7 / (1 if stacked else len(ys))
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" role="img">']
    for t in tk:
        yy = zero_y - t * scale
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        out.append(f'<text x="{left - 6}" y="{yy + 4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{esc(fmt_num(t, unit))}</text>')
    for i, r in enumerate(rows):
        gx = left + i * group_w + group_w * 0.15
        acc = 0.0
        for j, y in enumerate(ys):
            v = float(r.get(y) or 0)
            h = abs(v) * scale
            if stacked:
                bx, by = gx, zero_y - (acc + v) * scale if v >= 0 else zero_y - acc * scale
                acc += v
            else:
                bx, by = gx + j * bar_w, zero_y - h if v >= 0 else zero_y
            out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="2" fill="{PALETTE[j % len(PALETTE)]}"><title>{esc(r.get(x))}: {esc(fmt_num(v, unit))}</title></rect>')
            if not stacked and n <= 12:
                out.append(f'<text x="{bx + bar_w / 2:.1f}" y="{(by - 4) if v >= 0 else (by + h + 12):.1f}" text-anchor="middle" font-size="10" fill="#374151">{esc(fmt_num(v, unit))}</text>')
        lab = short(r.get(x), 14 if n > 8 else 22)
        lx, ly = gx + group_w * 0.35, top + ch + 14
        if n > 8:
            out.append(f'<text transform="translate({lx:.1f},{ly}) rotate(35)" font-size="10" fill="#374151">{esc(lab)}</text>')
        else:
            out.append(f'<text x="{lx:.1f}" y="{ly}" text-anchor="middle" font-size="11" fill="#374151">{esc(lab)}</text>')
    out.append(f'<line x1="{left}" x2="{width - right}" y1="{zero_y:.1f}" y2="{zero_y:.1f}" stroke="#9ca3af"/>')
    out.append("</svg>")
    legend = ""
    if len(ys) > 1:
        legend = "<div class=legend>" + "".join(f'<span><i style="background:{PALETTE[j % len(PALETTE)]}"></i>{esc(y)}</span>' for j, y in enumerate(ys)) + "</div>"
    return legend + "".join(out) + (f"<p class=note>{esc(note)}</p>" if note else "")


def svg_hbar(rows: list[dict], x: str, ys: list[str], unit: str = "", width: int = 640) -> str:
    """Horizontal bars: used automatically when category labels are long."""
    rows = [r for r in rows if r.get(x) is not None][:MAX_BARS]
    if not rows or not ys:
        return "<p class=empty>No rows to chart.</p>"
    y = ys[0]
    labw = min(max(len(str(r.get(x))) for r in rows), 34) * 6.4 + 16
    left, right, top, row_h = labw, 64, 10, 26
    height = top + row_h * len(rows) + 30
    cw = width - left - right
    vals = [float(r.get(y) or 0) for r in rows]
    vmax = max(vals + [0.0])
    tk = ticks(vmax)
    top_v = tk[-1] if tk else 1
    scale = cw / top_v if top_v else 1
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" role="img">']
    for t in tk:
        xx = left + t * scale
        out.append(f'<line y1="{top}" y2="{top + row_h * len(rows)}" x1="{xx:.1f}" x2="{xx:.1f}" stroke="#e5e7eb"/>')
        out.append(f'<text x="{xx:.1f}" y="{top + row_h * len(rows) + 16}" text-anchor="middle" font-size="11" fill="#6b7280">{esc(fmt_num(t, unit))}</text>')
    for i, (r, v) in enumerate(zip(rows, vals)):
        yy = top + i * row_h
        out.append(f'<text x="{left - 8}" y="{yy + row_h * 0.68:.1f}" text-anchor="end" font-size="12" fill="#374151">{esc(short(r.get(x), 34))}</text>')
        w = max(v, 0) * scale
        out.append(f'<rect x="{left}" y="{yy + 4}" width="{w:.1f}" height="{row_h - 8}" rx="3" fill="{PALETTE[0]}"><title>{esc(r.get(x))}: {esc(fmt_num(v, unit))}</title></rect>')
        out.append(f'<text x="{left + w + 6:.1f}" y="{yy + row_h * 0.68:.1f}" font-size="11" fill="#374151">{esc(fmt_num(v, unit))}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_line(rows: list[dict], x: str, ys: list[str], series: str | None, unit: str = "", width: int = 640, height: int = 320) -> str:
    rows = [r for r in rows if r.get(x) is not None]
    if not rows or not ys:
        return "<p class=empty>No rows to chart.</p>"
    y = ys[0]
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r.get(series)) if series else y, []).append(r)
    xs = list(dict.fromkeys(str(r.get(x)) for r in rows))  # keep the query's ORDER BY
    xi = {v: i for i, v in enumerate(xs)}
    left, right, top, bottom = 56, 16, 16, 48
    cw, ch = width - left - right, height - top - bottom
    allv = [float(r.get(y) or 0) for r in rows]
    vmax, vmin = max(allv + [0]), min(allv + [0])
    tk = ticks(max(vmax, abs(vmin)))
    top_v = tk[-1] if tk else 1
    scale = ch / (top_v - min(vmin, 0)) if top_v - min(vmin, 0) else 1
    y0 = top + ch + min(vmin, 0) * scale
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" role="img">']
    for t in tk:
        yy = y0 - t * scale
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        out.append(f'<text x="{left - 6}" y="{yy + 4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{esc(fmt_num(t, unit))}</text>')
    step = cw / max(len(xs) - 1, 1)
    for gi, (g, grs) in enumerate(groups.items()):
        pts = sorted(((xi[str(r.get(x))], float(r.get(y) or 0)) for r in grs), key=lambda p: p[0])
        path = " ".join(f"{'M' if i == 0 else 'L'}{left + p[0] * step:.1f},{y0 - p[1] * scale:.1f}" for i, p in enumerate(pts))
        col = PALETTE[gi % len(PALETTE)]
        out.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="2.5"/>')
        for p in pts:
            out.append(f'<circle cx="{left + p[0] * step:.1f}" cy="{y0 - p[1] * scale:.1f}" r="3.5" fill="{col}"><title>{esc(g)} · {esc(xs[p[0]])}: {esc(fmt_num(p[1], unit))}</title></circle>')
        if len(pts) <= 8 and len(groups) <= 3:
            for p in pts:
                out.append(f'<text x="{left + p[0] * step:.1f}" y="{y0 - p[1] * scale - 8:.1f}" text-anchor="middle" font-size="10" fill="{col}">{esc(fmt_num(p[1], unit))}</text>')
    max_labels = 7 if max(len(v) for v in xs) > 6 else 12
    every = max(1, -(-len(xs) // max_labels))
    shown = xs[::every]
    if xs[-1] not in shown and len(xs) > 1:
        if (len(xs) - 1) - xi[shown[-1]] >= max(2, every // 2):
            shown.append(xs[-1])
        else:
            shown[-1] = xs[-1]
    for v in shown:
        out.append(f'<text x="{left + xi[v] * step:.1f}" y="{top + ch + 18}" text-anchor="middle" font-size="11" fill="#374151">{esc(short(v, 10))}</text>')
    out.append("</svg>")
    legend = "<div class=legend>" + "".join(f'<span><i style="background:{PALETTE[i % len(PALETTE)]}"></i>{esc(g)}</span>' for i, g in enumerate(groups)) + "</div>" if series else ""
    return legend + "".join(out)


def svg_scatter(rows: list[dict], x: str, y: str, unit: str = "", width: int = 640, height: int = 320) -> str:
    pts = [(float(r[x]), float(r[y])) for r in rows if isinstance(r.get(x), (int, float)) and isinstance(r.get(y), (int, float))]
    if not pts:
        return "<p class=empty>No numeric pairs to plot.</p>"
    left, right, top, bottom = 56, 16, 16, 48
    cw, ch = width - left - right, height - top - bottom
    xmax, ymax = max(p[0] for p in pts) or 1, max(p[1] for p in pts) or 1
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" role="img">']
    for t in ticks(ymax):
        yy = top + ch - t / ymax * ch
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e5e7eb"/><text x="{left - 6}" y="{yy + 4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{esc(fmt_num(t, unit))}</text>')
    for t in ticks(xmax):
        xx = left + t / xmax * cw
        out.append(f'<text x="{xx:.1f}" y="{top + ch + 18}" text-anchor="middle" font-size="11" fill="#374151">{esc(fmt_num(t))}</text>')
    for px, py in pts:
        out.append(f'<circle cx="{left + px / xmax * cw:.1f}" cy="{top + ch - py / ymax * ch:.1f}" r="4" fill="{PALETTE[0]}" fill-opacity="0.7"><title>{esc(x)} {esc(fmt_num(px))}, {esc(y)} {esc(fmt_num(py, unit))}</title></circle>')
    out.append(f'<text x="{left + cw / 2}" y="{height - 4}" text-anchor="middle" font-size="11" fill="#6b7280">{esc(x)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_pie(rows: list[dict], x: str, y: str, width: int = 360, height: int = 260) -> str:
    data = [(str(r.get(x)), float(r.get(y) or 0)) for r in rows if r.get(x) is not None and float(r.get(y) or 0) > 0]
    if not data:
        return "<p class=empty>No rows to chart.</p>"
    data.sort(key=lambda d: -d[1])
    if len(data) > 8:
        data = data[:7] + [("Others", sum(d[1] for d in data[7:]))]
    total = sum(d[1] for d in data)
    cx, cy, r = 120, height / 2, 90
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:420px" preserveAspectRatio="xMidYMid meet" role="img">']
    ang = -math.pi / 2
    for i, (lab, v) in enumerate(data):
        a2 = ang + 2 * math.pi * v / total
        x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        large = 1 if a2 - ang > math.pi else 0
        out.append(f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f} Z" fill="{PALETTE[i % len(PALETTE)]}" stroke="#fff"><title>{esc(lab)}: {esc(fmt_num(v))} ({v / total * 100:.1f}%)</title></path>')
        ang = a2
    for i, (lab, v) in enumerate(data):
        out.append(f'<rect x="240" y="{24 + i * 24}" width="12" height="12" rx="2" fill="{PALETTE[i % len(PALETTE)]}"/><text x="258" y="{35 + i * 24}" font-size="12" fill="#374151">{esc(short(lab, 16))} · {v / total * 100:.0f}%</text>')
    out.append("</svg>")
    return "".join(out)


def table_html(columns: list[str], rows: list[dict], pid: str, unit: str = "") -> str:
    shown = rows[:MAX_TABLE_ROWS]
    head = "".join(f"<th>{esc(c)}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f'<td class="{"num" if isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool) else ""}">{esc(fmt_num(r.get(c)) if isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool) else r.get(c))}</td>' for c in columns) + "</tr>" for r in shown)
    note = f"<p class=note>Showing {len(shown)} of {len(rows)} rows; the download has all rows.</p>" if len(rows) > len(shown) else f"<p class=note>{len(rows)} rows.</p>"
    return f'<div class=tablewrap><table id="t-{pid}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>{note}'


def kpi_html(panel: dict, result: dict) -> str:
    rows = result["rows"]
    cols = result["columns"]
    value = None
    label = ""
    if rows:
        numeric = [c for c in cols if isinstance(rows[0].get(c), (int, float)) and not isinstance(rows[0].get(c), bool)]
        if numeric:
            value = rows[0][numeric[-1]]
            others = [c for c in cols if c not in numeric]
            if others:
                label = str(rows[0][others[0]])
        elif cols:
            value = rows[0][cols[0]]
    return (f'<div class="kpi" data-receipt="{esc(panel["id"])}"><div class=kpi-title>{esc(panel.get("title", ""))}</div>'
            f'<div class=kpi-value>{esc(fmt_num(value, panel.get("unit", "")))}</div>'
            f'<div class=kpi-label>{esc(label or panel.get("note", ""))}</div></div>')


PCT_NAME = re.compile(r"rate|percent|pct|share|%|proportion|ratio", re.I)


def plausibility(result: dict) -> list[str]:
    """Deterministic sanity flags the model cannot argue with."""
    flags = []
    cols, rows = result.get("columns", []), result.get("rows", [])
    for c in cols:
        vals = [r.get(c) for r in rows if isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool)]
        if not vals:
            continue
        if PCT_NAME.search(c) and (max(vals) > 100.5 or min(vals) < -100.5) and not re.search(r"ratio", c, re.I):
            flags.append(f'"{c}" has values outside 0–100, which is unusual for a percentage — the query may have the numerator and denominator swapped.')
        if all(v == vals[0] for v in vals) and len(vals) > 3:
            flags.append(f'"{c}" is the same value in every row.')
    return flags


def panel_html(panel: dict, result: dict) -> str:
    kind = panel.get("kind", "table")
    rows, cols = result["rows"], result["columns"]
    unit = panel.get("unit", "") or ""
    x = panel.get("x") or (cols[0] if cols else None)
    ys = panel.get("y") or [c for c in cols if c != x and rows and isinstance(rows[0].get(c), (int, float)) and not isinstance(rows[0].get(c), bool)]
    if isinstance(ys, str):
        ys = [ys]
    ys = [c for c in ys if c in cols]
    if result.get("error"):
        body = '<p class=empty>This panel could not be computed from the file; the query it tried is in the receipt below.</p>'
    elif kind in ("bar", "stacked_bar"):
        long_labels = bool(rows) and max(len(str(r.get(x))) for r in rows[:MAX_BARS]) > 14
        if x and ys and kind == "bar" and len(ys) == 1 and long_labels:
            body = svg_hbar(rows, x, ys, unit)
        else:
            body = svg_bar(rows, x, ys, unit, stacked=(kind == "stacked_bar")) if x and ys else table_html(cols, rows, panel["id"])
    elif kind == "line":
        numeric_x = bool(rows) and isinstance(rows[0].get(x), (int, float)) and not isinstance(rows[0].get(x), bool)
        if x and ys and numeric_x and len(rows) > 40:
            body = svg_scatter(rows, x, ys[0], unit)  # a 'line' over raw numeric pairs is a scatter
        elif x and ys and len(rows) > 120 and not panel.get("series"):
            body = svg_line(rows[:120], x, ys, None, unit) + "<p class=note>Showing the first 120 points.</p>"
        else:
            body = svg_line(rows, x, ys, panel.get("series"), unit) if x and ys else table_html(cols, rows, panel["id"])
    elif kind == "scatter":
        body = svg_scatter(rows, x, ys[0], unit) if x and ys else table_html(cols, rows, panel["id"])
    elif kind == "pie":
        body = svg_pie(rows, x, ys[0]) if x and ys else table_html(cols, rows, panel["id"])
    else:
        body = table_html(cols, rows, panel["id"])
    warn = "".join(f'<p class=warn>⚠ Check this: {esc(f)}</p>' for f in plausibility(result))
    return (f'<section class="panel" data-receipt="{esc(panel["id"])}"><header><h3>{esc(panel.get("title", panel["id"]))}</h3>'
            f'<button class=dl data-panel="{esc(panel["id"])}">Download CSV</button></header>{body}{warn}'
            f'<details class=receipt><summary>How this was computed · {len(rows)} rows</summary><pre>{esc(panel.get("sql", ""))}</pre>{("<pre>" + esc(result["error"]) + "</pre>") if result.get("error") else ""}</details></section>')


PLACEHOLDER = re.compile(r"{{\s*([A-Za-z_]\w*)\s*(?:\[(\d+)\])?\s*(?:\.\s*([^}]+?))?\s*}}")


def fill_narrative(text: str, results: dict[str, dict]) -> tuple[str, list[str]]:
    """Replace {{pN}}, {{pN.col}}, {{pN[k]}}, {{pN[k].col}} with computed values.

    {{pN}} on a one-row panel -> its number. On a multi-row panel -> "label (value)"
    of row k (default the first row), so prose about rankings names the thing, not
    just a number. Returns html and the unresolved references."""
    missing: list[str] = []
    zero_based = "[0]" in text  # small models count from 0 as often as from 1

    def repl(m: re.Match) -> str:
        pid, idx, col = m.group(1), m.group(2), (m.group(3) or "").strip()
        ref = m.group(0)
        res = results.get(pid)
        if not res or not res["rows"]:
            missing.append(ref)
            return '<mark title="the model referred to a panel or row that does not exist">[not computed]</mark>'
        k = (int(idx) if zero_based else max(int(idx) - 1, 0)) if idx else 0
        if k >= len(res["rows"]):
            missing.append(ref)
            return '<mark title="the model referred to a row that does not exist">[not computed]</mark>'
        row = res["rows"][k]
        cols = res["columns"]
        nums = [c for c in cols if isinstance(row.get(c), (int, float)) and not isinstance(row.get(c), bool)]
        texts = [c for c in cols if c not in nums]
        if col:
            match = next((c for c in cols if c.casefold() == col.casefold()), None)
            if match is None:
                missing.append(ref)
                return '<mark title="the model referred to a column that panel does not have">[not computed]</mark>'
            v = row[match]
            return f'<b data-receipt="{esc(pid)}">{esc(fmt_num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)}</b>'
        if len(res["rows"]) == 1 or not texts:
            v = row[nums[-1]] if nums else row[cols[0]]
            return f'<b data-receipt="{esc(pid)}">{esc(fmt_num(v))}</b>'
        label = row[texts[0]]
        value = fmt_num(row[nums[-1]]) if nums else ""
        return f'<b data-receipt="{esc(pid)}">{esc(label)}{(" (" + esc(value) + ")") if value else ""}</b>'

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    for p in paragraphs:
        if p.startswith("#"):
            level = min(len(p) - len(p.lstrip("#")), 3)
            out.append(f"<h{level + 1}>{esc(p.lstrip('# '))}</h{level + 1}>")
        elif p.startswith(("- ", "* ")):
            items = "".join(f"<li>{PLACEHOLDER.sub(repl, esc(i[2:]))}</li>" for i in p.splitlines())
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{PLACEHOLDER.sub(repl, esc(p))}</p>")
    return "".join(out), missing


def numeric_literal_lint(text: str) -> list[str]:
    """Numbers typed by the model (outside {{receipts}}) are suspects."""
    stripped = re.sub(r"{{[^}]+}}", " ", text)
    stripped = re.sub(r"\b(?:top|bottom|first|last|lowest|highest)\s+\d+\b", " ", stripped, flags=re.I)
    return [m for m in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?(?![\w.])", stripped) if m not in ("1", "2", "3", "2023", "2024", "2025", "2026", "2022", "2021")]


CSS = """
:root{--bg:#f6f7fb;--card:#fff;--ink:#111827;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1360px;margin:0 auto;padding:28px 32px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:24px 0 8px}h3{font-size:15px;margin:0}
.sub{color:var(--muted);margin:0 0 18px}.source{color:var(--muted);font-size:13px;margin-top:24px;border-top:1px solid var(--line);padding-top:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-width:0}
.kpi-title{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kpi-value{font-size:30px;font-weight:700;margin:4px 0}.kpi-label{font-size:13px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:16px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;min-width:0;overflow:hidden}
.panel header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px}
.panel header h3{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.panel.wide{grid-column:1/-1}
button.dl{font:inherit;font-size:12px;padding:5px 10px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--accent);cursor:pointer;white-space:nowrap}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}th{color:var(--muted);font-weight:600;background:#fafafa;position:sticky;top:0}td.num{text-align:right;font-variant-numeric:tabular-nums}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);margin-bottom:4px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.note{font-size:12px;color:var(--muted);margin:6px 0 0}.warn{font-size:12px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:6px 10px;margin:8px 0 0}.empty{color:var(--muted);font-style:italic}
details.receipt{margin-top:8px;font-size:12px;color:var(--muted)}details.receipt pre{white-space:pre-wrap;background:#f3f4f6;padding:8px;border-radius:8px;font-size:11px;color:#374151}
.report p{max-width:820px}.report b{color:var(--accent)}mark{background:#fee2e2}
svg text{font-family:inherit}
@media print{button.dl{display:none}}
"""

JS = """
(function(){
  const DATA = __DATA__;
  document.querySelectorAll('button.dl').forEach(b => b.addEventListener('click', () => {
    const p = DATA[b.dataset.panel]; if(!p) return;
    const esc = v => { const s = v == null ? '' : String(v); return /[",\\n]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s; };
    const csv = [p.columns.join(',')].concat(p.rows.map(r => p.columns.map(c => esc(r[c])).join(','))).join('\\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'})); a.download = b.dataset.panel + '.csv'; a.click();
  }));
})();
"""


def render(plan: dict, results: dict[str, dict], source: str, template: str = "dashboard", question: str = "") -> str:
    title = plan.get("title") or "Dashboard"
    subtitle = plan.get("subtitle") or question
    panels = plan.get("panels", [])
    kpis = [p for p in panels if p.get("kind") == "kpi"]
    others = [p for p in panels if p.get("kind") != "kpi"]
    parts = [f"<title>{esc(title)}</title><style>{CSS}</style><div class=wrap>",
             f"<h1>{esc(title)}</h1><p class=sub>{esc(subtitle)}</p>"]
    narrative_html, missing = ("", [])
    if plan.get("narrative"):
        narrative_html, missing = fill_narrative(plan["narrative"], results)
    if template == "report":
        parts.append(f'<div class=report>{narrative_html}</div>')
        if kpis:
            parts.append("<div class=kpis>" + "".join(kpi_html(p, results.get(p["id"], {"rows": [], "columns": []})) for p in kpis) + "</div>")
        if others:
            parts.append("<h2>Exhibits</h2><div class=grid>")
            for p in others:
                cls = " wide" if p.get("kind") == "table" and len(results.get(p["id"], {}).get("columns", [])) > 3 else ""
                parts.append(panel_html(p, results.get(p["id"], {"rows": [], "columns": []})).replace('class="panel"', f'class="panel{cls}"'))
            parts.append("</div>")
    else:
        if kpis:
            parts.append("<div class=kpis>" + "".join(kpi_html(p, results.get(p["id"], {"rows": [], "columns": []})) for p in kpis) + "</div>")
        if narrative_html:
            parts.append(f'<div class=report>{narrative_html}</div>')
        parts.append("<div class=grid>")
        for p in others:
            cls = " wide" if p.get("kind") == "table" and len(results.get(p["id"], {}).get("columns", [])) > 3 else ""
            parts.append(panel_html(p, results.get(p["id"], {"rows": [], "columns": []})).replace('class="panel"', f'class="panel{cls}"'))
        parts.append("</div>")
    missing = [m for m in (plan.get("missing") or []) if isinstance(m, str) and m.strip()]
    if missing:
        parts.append('<p class=note style="margin-top:16px">Not in the data, so not shown: ' + esc("; ".join(missing)) + '.</p>')
    parts.append(f"<p class=source>Source: {esc(source)} · every figure computed locally by DuckDB from the file(s) above; open a panel's receipt for the query.</p></div>")
    data = {pid: {"columns": r["columns"], "rows": r["rows"]} for pid, r in results.items()}
    parts.append("<script>" + JS.replace("__DATA__", json.dumps(data, default=str)) + "</script>")
    return "".join(parts)
