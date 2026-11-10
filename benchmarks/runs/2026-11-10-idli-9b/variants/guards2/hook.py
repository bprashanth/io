"""guards + spec tolerance in file_ask (a patch to sites/files/tools.py; helps any model):

- key aliases (presets -> preset, measure -> measures, groupby/group -> group_by, filter -> filters); any other
  unknown key is an error listing the allowed keys, so the model retries instead of the rule silently dropping
  (today "presets": [...] is ignored without a word);
- a measure, breakdown, filter column or preset given by its label ("Number of visits") becomes its id when
  exactly one matches;
- a count with no breakdown that matches 15 rows or fewer comes back with those rows listed ("which households
  ..." answered with a count still shows who).
"""
import importlib.util
import json
import os
import re

KEYS = ("measures", "group_by", "filters", "preset", "date", "sort", "limit")
ALIAS = {"presets": "preset", "measure": "measures", "groupby": "group_by", "group": "group_by", "groups": "group_by",
         "filter": "filters", "where": "filters"}


def _base():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guards", "hook.py")
    s = importlib.util.spec_from_file_location("guards_hook", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def apply(mcp, tools):
    _base().apply(mcp, tools)
    from sites.files import tools as ft
    ask0 = mcp.TOOLS["file_ask"]

    def to_id(v, ids):  # ids: {id: label}
        if v in ids:
            return v
        hits = [i for i, lab in ids.items() if str(lab).strip().lower() == str(v).strip().lower()]
        return hits[0] if len(hits) == 1 else v

    def file_ask(file, spec, tab=None, chart=False):
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except ValueError:
                return {"error": "spec must be a JSON object."}
        if not isinstance(spec, dict):
            return {"error": "spec must be a JSON object."}
        spec = {ALIAS.get(k, k): v for k, v in spec.items()}
        if "chart" in spec:
            chart = bool(spec.pop("chart")) or chart
        bad = [k for k in spec if k not in KEYS]
        if bad:
            return {"error": f"Unknown spec key(s) {bad}. Allowed: {list(KEYS)}.", "hint": "Call file_ask again."}
        try:
            forms = ft.files().open(file)["forms"]
            form = forms.get(tab) if tab in forms else next(iter(forms.values()))
            b = ft._brief(form)
        except Exception:
            return ask0[0](file, spec, tab=tab, chart=chart)
        for k, ids in (("measures", b["measures"]), ("group_by", b["group_by"]), ("preset", b["presets"])):
            v = spec.get(k)
            if isinstance(v, str):
                v = [v]
            if isinstance(v, list):
                spec[k] = [to_id(x, ids) for x in v]
        if isinstance(spec.get("filters"), dict):
            cols = {c: f.get("label", c) for c, f in b["filters"].items()}
            spec["filters"] = {to_id(c, cols): v for c, v in spec["filters"].items()}
        out = ask0[0](file, spec, tab=tab, chart=chart)
        if spec.get("measures") == ["rows"] and not spec.get("group_by") and isinstance(out, dict) and out.get("answer"):
            m = re.search(r"(\d[\d,]*)\.?\s*$", out["answer"])
            n = int(m.group(1).replace(",", "")) if m else None
            if n is not None and 0 < n <= 15:
                lst = ask0[0](file, dict(spec, measures=[]), tab=tab, chart=False)
                if isinstance(lst, dict) and lst.get("answer"):
                    rows = [l for l in lst["answer"].splitlines() if l.startswith("- ")]
                    out["answer"] += "\nThey are:\n" + "\n".join(rows)
        return out

    mcp.TOOLS["file_ask"] = (file_ask,) + tuple(ask0[1:])
