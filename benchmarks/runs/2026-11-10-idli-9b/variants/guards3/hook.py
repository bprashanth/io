"""guards2 + a stateful form: file_ask remembers the last spec per file (like dropdowns that stay where they were).

- refine=true: the spec holds only what changes ("same but ward C", "and in summer?"); it is merged into the last
  spec for that file: filters merge column by column (a value of null removes that filter), measures / group_by /
  preset replace when given.
- every answer carries `form_now`: the spec that ran, so the model sees the state it is refining.
A small model no longer has to rebuild every filter from the chat history for each follow-up.
"""
import copy
import importlib.util
import json
import os


def _base():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guards2", "hook.py")
    s = importlib.util.spec_from_file_location("guards2_hook", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def apply(mcp, tools):
    _base().apply(mcp, tools)
    ask0 = mcp.TOOLS["file_ask"]
    last = {}

    def file_ask(file, spec, tab=None, chart=False, refine=False):
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except ValueError:
                return {"error": "spec must be a JSON object."}
        if isinstance(refine, str):
            refine = refine.lower() in ("true", "yes", "1")
        key = (file, tab or "")
        if refine and key in last and isinstance(spec, dict):
            base = copy.deepcopy(last[key])
            for k, v in spec.items():
                if k == "filters" and isinstance(v, dict):
                    f = dict(base.get("filters") or {})
                    for col, val in v.items():
                        if val is None:
                            f.pop(col, None)
                        else:
                            f[col] = val
                    base["filters"] = f
                else:
                    base[k] = v
            spec = base
        out = ask0[0](file, spec, tab=tab, chart=chart)
        if isinstance(out, dict) and not out.get("error"):
            last[key] = {k: v for k, v in spec.items() if k != "chart"} if isinstance(spec, dict) else spec
            out["form_now"] = last[key]
        return out

    d = ask0[1] + (" For a follow-up that changes one thing ('same but ward C', 'and in summer?', 'only the done "
                   "ones'), set refine=true and put only what changes in spec; the rest stays as in `form_now` of the "
                   "last answer (a filter set to null is removed).")
    p = dict(ask0[2], refine={"type": "boolean", "description": "Change only what's in spec; keep the rest of the last "
                                                                 "answer's form (form_now)"})
    mcp.TOOLS["file_ask"] = (file_ask, d, p, ask0[3])
