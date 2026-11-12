"""Form answers as Vega-Lite charts: one chart description for the chat (rendered to SVG here, offline, with
vl-convert) and for the dashboard tab (rendered there with vega-embed, interactive: hover for values, click a bar to
drill into it).

Code picks the chart from the answer's shape, never a model:
  one breakdown, one figure          -> bars, sorted, values on the bars (top 15 of more)
  one breakdown, several figures     -> a column of bar panels, one per figure, same order, each its own axis
  a date breakdown (month/quarter/year) -> a line with points, in time order (several figures: one line panel each)
  two breakdowns, one figure         -> a heatmap grid with the value in each cell
  rows with latitude and longitude   -> a point map (no base map: offline), coloured by the first category
  one row                             -> nothing (the answer's list says it better)
"""
import json
import re

from lib.formkit import indian

LAT = re.compile(r"(?i)^(lat|latitude|gps[ _-]?lat.*|y[ _-]?coord.*)$")
LON = re.compile(r"(?i)^(lon|lng|long|longitude|gps[ _-]?lon.*|x[ _-]?coord.*)$")
TIME = re.compile(r"(?i):\s*(month|quarter|year|week|day)$")
BLUE = "#2E6F95"
TOP = 15
CONFIG = {"view": {"stroke": None}, "font": "sans-serif",
          "axis": {"labelFontSize": 11, "titleFontSize": 11, "labelLimit": 240, "titleFontWeight": "normal"},
          "title": {"fontSize": 13, "anchor": "start", "fontWeight": "bold"},
          "legend": {"labelFontSize": 11, "titleFontSize": 11}}


FORMATS = {}  # label -> taught format (inr | count | number | percent), set per chart by chart()/spec_for()


def _label(col, v):
    """A value as the answer text writes it: Indian grouping, and Rs / % from the measure's taught format (else
    from its label)."""
    if v is None:
        return "none"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if not isinstance(v, (int, float)):
        return str(v)
    s = indian(v)
    kind = FORMATS.get(col)
    if kind == "inr":
        return "Rs " + s
    if kind == "percent" or "%" in col:
        return s + "%"
    if kind == "count":
        return s
    ratio = re.search(r"(?i)\b(months?|ratio|vs|share|score|rate|days?)\b", col)
    if re.search(r"(?i)\(\s*(rs|inr|₹)\s*\)", col) and not ratio:
        return "Rs " + s
    return s


def _short(col):
    return re.sub(r"\s*\(\s*(?:Rs|INR|₹)\s*\)", " (Rs)", str(col)).strip()


def _split(res, spec):
    rows, cols, total = res.get("rows") or [], res.get("columns") or [], res.get("total") or {}
    listing = not (spec or {}).get("measures")
    if listing:
        return rows, cols, [], True
    if total:
        nums = [c for c in cols if c in total]
    else:
        nums = [c for c in cols if any(isinstance(r.get(c), (int, float)) for r in rows)]
    return rows, [c for c in cols if c not in nums], nums, False


def _vals(rows, groups, nums):
    out = []
    for r in rows:
        d = {g: ("(blank)" if r.get(g) in (None, "") else str(r.get(g))) for g in groups}
        for m in nums:
            v = r.get(m)
            d[m] = float(v) if isinstance(v, (int, float)) else None
            d[m + " "] = _label(m, v)  # the label shown on the chart and in the tooltip
        out.append(d)
    return out


def _bars(values, g, m, order, title=None, width=520):
    n = len(values)
    enc_y = {"field": g, "type": "nominal", "sort": order, "title": None}
    base = {"data": {"values": values}, "width": width, "height": max(40, 22 * n),
            "encoding": {"y": enc_y, "x": {"field": m, "type": "quantitative", "title": _short(m)},
                         "tooltip": [{"field": g, "type": "nominal"}, {"field": m + " ", "title": _short(m)}]}}
    if title:
        base["title"] = {"text": _short(title), "fontSize": 12}
    base["layer"] = [{"mark": {"type": "bar", "color": BLUE, "cornerRadiusEnd": 2},
                      "params": [{"name": "pick", "select": {"type": "point", "fields": [g]}}]},
                     {"mark": {"type": "text", "align": "left", "dx": 4, "fontSize": 11},
                      "encoding": {"text": {"field": m + " "}}}]
    return base


def _line(values, g, m, order, title=None, width=560):
    lay = [{"mark": {"type": "line", "color": BLUE, "point": {"filled": True, "size": 50, "color": BLUE}}}]
    if len(values) <= 14:
        lay.append({"mark": {"type": "text", "dy": -10, "fontSize": 10}, "encoding": {"text": {"field": m + " "}}})
    out = {"data": {"values": values}, "width": width, "height": 220, "layer": lay,
           "encoding": {"x": {"field": g, "type": "ordinal", "sort": order, "title": g,
                              "axis": {"labelAngle": -40 if len(values) > 8 else 0}},
                        "y": {"field": m, "type": "quantitative", "title": _short(m)},
                        "tooltip": [{"field": g}, {"field": m + " ", "title": _short(m)}]}}
    if title:
        out["title"] = {"text": _short(title), "fontSize": 12}
    return out


def spec_for(res, title, spec=None, form=None):
    """The Vega-Lite spec for a form answer, or None when a chart wouldn't help. form (formkit's form for the tab)
    gives the measures' formats and the column labels for ids (e.g. the map's size column, from spec.sort)."""
    FORMATS.clear()
    labels = {}
    if form:
        FORMATS.update({m["label"]: m.get("format") for m in form.get("_measures", {}).values()})
        labels.update({x["column"]: x["label"] for x in form.get("filters", [])})
    rows, groups, nums, listing = _split(res, spec)
    if listing:
        cols = res.get("columns") or []
        lat = next((c for c in cols if LAT.match(str(c))), None)
        lon = next((c for c in cols if LON.match(str(c))), None)
        if not (lat and lon) or len(rows) < 2:
            return None
        cats = [c for c in cols if c not in (lat, lon) and not any(isinstance(r.get(c), (int, float)) for r in rows)
                and 1 < len({r.get(c) for r in rows}) <= 12]
        sort_by = ((spec or {}).get("sort") or {}).get("by")
        size = labels.get(sort_by) if labels.get(sort_by) in cols else None
        values = [dict(r, **{c + " ": _label(c, r.get(c)) for c in cols}) for r in rows
                  if isinstance(r.get(lat), (int, float)) and isinstance(r.get(lon), (int, float))]
        if len(values) < 2:
            return None
        enc = {"x": {"field": lon, "type": "quantitative", "title": "Longitude", "scale": {"zero": False, "nice": False,
                                                                                         "padding": 12}},
               "y": {"field": lat, "type": "quantitative", "title": "Latitude", "scale": {"zero": False, "nice": False,
                                                                                        "padding": 12}},
               "tooltip": [{"field": c + " ", "title": c} for c in cols if c not in (lat, lon)][:8]}
        if cats:
            enc["color"] = {"field": cats[0], "type": "nominal"}
        if size:
            enc["size"] = {"field": size, "type": "quantitative", "title": _short(size), "scale": {"range": [30, 600]}}
        return {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "config": CONFIG, "background": "white",
                "title": title + (f", sized by {_short(size)}" if size else "") + " (one point per row; no base map)",
                "width": 480, "height": 420, "data": {"values": values},
                "mark": {"type": "circle", "opacity": 0.75, "stroke": "white", "strokeWidth": 0.5,
                         **({} if size else {"size": 90})},
                "encoding": enc}
    if not groups or not nums or len(rows) < 2:
        return None
    values = _vals(rows, groups, nums)
    out = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "config": CONFIG, "background": "white"}
    if len(groups) == 1:
        g = groups[0]
        if TIME.search(g):
            order = sorted({v[g] for v in values})
            if len(nums) == 1:
                return {**out, **_line(values, g, nums[0], order), "title": title}
            return {**out, "title": title, "vconcat": [_line(values, g, m, order, title=m) for m in nums[:6]],
                    "resolve": {"scale": {"y": "independent"}}}
        first = nums[0]
        values.sort(key=lambda v: (v[first] is None, -(v[first] or 0)))
        note = f" (top {TOP} of {len(values)})" if len(values) > TOP else ""
        values = values[:TOP]
        order = [v[g] for v in values]
        if len(nums) == 1:
            return {**out, **_bars(values, g, first, order), "title": title + note}
        return {**out, "title": title + note, "vconcat": [_bars(values, g, m, order, title=m, width=460)
                                                          for m in nums[:6]],
                "resolve": {"scale": {"x": "independent"}}}
    if len(groups) == 2 and len(nums) == 1:
        g1, g2, m = groups[0], groups[1], nums[0]

        def order(g):
            vs = sorted({v[g] for v in values})
            try:
                return sorted(vs, key=lambda x: float(x))
            except ValueError:
                return vs
        return {**out, "title": title, "data": {"values": values},
                "width": max(260, 46 * len(order(g2))), "height": max(120, 26 * len(order(g1))),
                "encoding": {"y": {"field": g1, "type": "nominal", "sort": order(g1), "title": g1},
                             "x": {"field": g2, "type": "ordinal", "sort": order(g2), "title": g2,
                                   "axis": {"labelAngle": 0}},
                             "tooltip": [{"field": g1}, {"field": g2}, {"field": m + " ", "title": _short(m)}]},
                "layer": [{"mark": {"type": "rect"},
                           "encoding": {"color": {"field": m, "type": "quantitative", "title": _short(m),
                                                  "scale": {"scheme": "blues"}}}},
                          {"mark": {"type": "text", "fontSize": 10},
                           "encoding": {"text": {"field": m + " "},
                                        "color": {"condition": {"test": f"datum['{m}'] > 0.6 * "
                                                                        f"{max([v[m] or 0 for v in values])}",
                                                                "value": "white"}, "value": "black"}}}]}
    return None


def svg(vl, out_svg):
    """Render a spec to an SVG file (offline). Returns out_svg, or None if vl-convert isn't installed or fails."""
    try:
        import vl_convert as vlc
        text = vlc.vegalite_to_svg(json.dumps(vl))
    except Exception:  # noqa: BLE001  (no vl-convert: the caller falls back to matplotlib)
        return None
    with open(out_svg, "w") as f:
        f.write(text)
    with open(out_svg[:-4] + ".vl.json", "w") as f:
        json.dump(vl, f)
    return out_svg


def chart(res, title, out_svg, spec=None, form=None):
    """The chat's picture for a form answer: Vega-Lite when it can, else the matplotlib bars (chartkit)."""
    vl = spec_for(res, title, spec, form)
    if vl is not None:
        got = svg(vl, out_svg)
        if got:
            return got
        if (spec or {}).get("measures") == [] or not (spec or {}).get("measures"):
            return None
    from lib import chartkit
    return chartkit.bar_svg(res, title, out_svg)
