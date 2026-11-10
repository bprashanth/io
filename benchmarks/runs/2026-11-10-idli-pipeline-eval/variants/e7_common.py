"""E7: fewer tools, by phase. Built on the 9B benchmark's split (file_ask takes the person's question; a separate
call sets the form's dials, model from PIPE_SPEC_MODEL) plus its guards2 tolerance.

mode "today": every tool Idli has (29 with the card), as the product is now.
mode "soft":  9 tools all the time: start, file_get, file_open, file_ask, chart_request, chart_show, teach_file,
              working_copy_ready, card. working_copy and teach_send run from the card click, not the model.
mode "hard":  the same 9, but only the current phase's are listed (get the file / learn / clean / analyse).
              file_get and file_open stay in every phase as the way out (re-open with another goal).
"""
import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
B9 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "2026-11-10-idli-9b")
NINE = ["start", "file_get", "file_open", "file_ask", "chart_request", "chart_show", "teach_file", "working_copy_ready"]
PHASES = {
    "get": ["start", "file_get", "file_open"],
    "learn": ["teach_file", "file_get", "file_open"],
    "clean": ["working_copy_ready", "file_get", "file_open"],
    "analyse": ["file_ask", "chart_request", "chart_show", "teach_file", "file_get", "file_open"],
}


def _split():
    p = os.path.join(B9, "variants", "split_common.py")
    s = importlib.util.spec_from_file_location("split_common", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def apply(mcp, mode):
    _split().apply(mcp, os.environ.get("PIPE_SPEC_MODEL") or "or-qwen35-9b")
    if mode == "today":
        return
    T = mcp.TOOLS
    state = {"phase": "get", "file": None, "teach_rid": None, "goal": None}
    raw = {n: T[n][0] for n in T}

    def wrap(name, after):
        fn, d, p, r = T[name]

        def w(*a, **k):
            out = fn(*a, **k)
            try:
                after(out, *a, **k)
            except Exception:  # noqa: BLE001  bookkeeping never breaks the tool
                pass
            return out
        T[name] = (w, d, p, r)

    def opened(out, *a, **k):
        if not isinstance(out, dict) or out.get("error"):
            return
        state["file"] = out.get("file") or (out.get("opened") or {}).get("file") or state["file"] or \
            (a[0] if a and name_is_path(a[0]) else None)
        goal = k.get("goal") or state["goal"]
        state["goal"] = goal
        then = str(out.get("then", ""))
        if "teach_file" in then and "file_ask" not in then:
            state["phase"] = "learn"
        elif goal == "clean":
            state["phase"] = "clean"
        else:
            state["phase"] = "analyse"

    def name_is_path(x):
        return isinstance(x, str) and not x.startswith("http")

    def taught(out, *a, **k):
        if isinstance(out, dict):
            state["teach_rid"] = out.get("request_id") or (out.get("request") or {}).get("id") or state["teach_rid"]
            state["phase"] = "learn"

    def ready(out, *a, **k):
        state["phase"] = "analyse"

    for n in ("file_get", "file_open"):
        wrap(n, opened)
    wrap("teach_file", taught)
    wrap("chart_request", taught)
    wrap("working_copy_ready", ready)
    ask0 = T["file_ask"]

    def file_ask(*a, **k):
        if state["file"] is None and not (a or k.get("file")):
            return {"error": "Not now: no file is open.", "then": "Ask for the file's Google link in one line."}
        return ask0[0](*a, **k)
    T["file_ask"] = (file_ask,) + tuple(ask0[1:])
    for n in list(T):
        if n not in NINE:
            del T[n]  # gone from the model's list; the card still reaches them below

    def find_file(card_text):
        return state["file"]

    def on_card(card, answer):
        a = answer.lower()
        if "yes, mark them in drive" in a or "make a fresh copy" in a:
            f = state["file"]
            if not f:
                return None
            args = {"file": f, **({"fresh": True} if "fresh copy" in a else {})}
            out = raw["working_copy"](**args)
            state["phase"] = "clean"
            if isinstance(out, dict):
                out.setdefault("then", "")
                out["then"] = ("Say in one line where the copy is. When they say they're ready or done fixing, call "
                               "working_copy_ready.")
            return {"name": "working_copy", "args": args, "result": out}
        if re.search(r"yes, send", a):
            rid = state["teach_rid"]
            if not rid:
                return None
            args = {"request_id": rid}
            out = raw["teach_send"](**args)
            return {"name": "teach_send", "args": args, "result": out}
        if "not now" in a and state["phase"] == "clean":
            state["phase"] = "analyse"
        if "analyse it now" in a or "use the checked copy" in a or "use the original" in a:
            state["phase"] = "analyse"
        return None

    mcp.on_card = on_card
    if mode == "hard":
        mcp.phase_tools = lambda: set(PHASES[state["phase"]])
    mcp.e7_state = state
