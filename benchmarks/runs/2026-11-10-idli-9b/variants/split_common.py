"""The split: the chat model (a 9B) runs every flow; a bigger small-active model only builds form specs.

file_ask gains `question` (the person's words). When given, the tool asks the spec model for the spec, with:
the file's form (each tab's measures, breakdowns, filters with values, presets), this file's question thread so far
(earlier questions, the spec that ran, the first lines of the answer), and the new question. The spec model replies
{"tab", "spec", "chart"} or {"cannot": why, "route": "chart_request" | "teach_file"}. The chat model never writes
a spec, never resolves "those"/"there" itself, and never decides quick chart vs Claude chart.
Everything else is the guards2 variant (card/number Stop hooks, goal-aware drive_find, card-gated delete, spec
tolerance). In the product this is a sub-call inside cowork's file_ask (the MCP server calls the model directly).
"""
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

PROMPT = """You turn a question about a spreadsheet into a form spec. The form answers with code; you only choose.
Spec keys: measures [ids], group_by [up to 2 ids], filters {column: [values]} | {column: {min, max}} |
{column: {not: [values]}}, preset [ids], date {column, period|from|to}. measures [] lists matching rows (who/which).
Use only ids and values from the form below. Follow-ups ("same but ward C", "and in summer?", "those", "there",
"that one") refine the previous spec in the thread: keep its filters unless the question changes them.
Reply with JSON only, one of:
  {"tab": "<tab>", "spec": {...}, "chart": true|false}   (chart true when they ask for a chart/graph/plot/picture
   and the spec has a breakdown)
  {"cannot": "<why, in a few words>", "route": "chart_request"}  (a chart the form can't draw: a share of a total,
   two filters compared side by side, a map, a computed trend)
  {"cannot": "<why>", "route": "teach_file"}  (the form has no measure or filter for it)"""


PROMPT2 = PROMPT.replace(
    'Follow-ups ("same but ward C", "and in summer?", "those", "there",\n"that one") refine the previous spec in the thread: keep its filters unless the question changes them.',
    'Follow-ups that refer back ("same but ward C", "and in summer?", "those", "there", "that one",\n'
    '"put that in a chart") refine the previous spec in the thread: keep its filters unless the question changes '
    'them.\nA question that doesn\'t refer back starts from an empty spec. Never filter on the column you break down '
    'by.\nAdd no filter or preset the question (or the spec it refines) doesn\'t ask for.').replace(
    '{"cannot": "<why, in a few words>", "route": "chart_request"}  (a chart the form can\'t draw',
    '{"cannot": "<why, in a few words>", "route": "chart_request"}  (only when the form can\'t draw it; one breakdown\n'
    '   or two of one measure is a form chart: use chart true. Can\'t draw')
assert PROMPT2 != PROMPT


def _guards2():
    p = os.path.join(HERE, "guards2", "hook.py")
    s = importlib.util.spec_from_file_location("guards2_hook", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def apply(mcp, ask_model_id, prompt=None):
    _guards2().apply(mcp, None)
    import convo
    from sites.files import tools as ft
    spec_m = convo.load_models()[ask_model_id]
    ask0 = mcp.TOOLS["file_ask"]
    threads = {}

    def build(file, question):
        forms = ft.files().open(file)["forms"]
        brief = [ft._brief(f) for f in forms.values()]
        thread = threads.get(file, [])[-6:]
        msg = ((prompt or PROMPT) + "\n\nThe form:\n" + json.dumps(brief, ensure_ascii=False)
               + ("\n\nThe thread so far:\n" + "\n".join(json.dumps(t, ensure_ascii=False) for t in thread) if thread else "")
               + "\n\nQuestion: " + question)
        body = {"model": spec_m["model"], "temperature": 0, "max_tokens": spec_m.get("max_tokens", 4096),
                "messages": [{"role": "user", "content": msg}]}
        body.update(spec_m.get("extra") or {})
        req = urllib.request.Request(spec_m["base"].rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json",
                                      "Authorization": "Bearer " + convo.api_key(spec_m)})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=240) as r:
            text = json.load(r)["choices"][0]["message"]["content"] or ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        m = re.search(r"\{.*\}", text, re.S)
        return (json.loads(m.group(0)) if m else {"cannot": "no spec"}), round(time.time() - t0, 1)

    def file_ask(file, spec=None, tab=None, chart=False, question=None):
        if not question:
            return ask0[0](file, spec or {}, tab=tab, chart=chart)
        try:
            got, secs = build(file, question)
        except Exception as e:
            return {"error": f"The spec builder failed: {type(e).__name__}", "then": "Try file_ask again."}
        if got.get("cannot"):
            route = got.get("route") or "teach_file"
            return {"answer": None, "spec_model_secs": secs, "cannot": got["cannot"],
                    "then": ("Call chart_request with their words (Claude designs this chart on fake data)."
                             if route == "chart_request" else
                             "Call teach_file with their question and missing = '" + str(got["cannot"]) + "'.")}
        out = ask0[0](file, got.get("spec") or {}, tab=got.get("tab") or tab, chart=bool(got.get("chart")) or chart)
        if isinstance(out, dict):
            out["spec_model_secs"] = secs
            if out.get("answer"):
                threads.setdefault(file, []).append({"q": question, "tab": got.get("tab"), "spec": got.get("spec"),
                                                     "answer": out["answer"].splitlines()[0][:160]})
        return out

    d = ("Answer a question about an opened file. Pass `question`: the person's question in their words (add what "
         "'that', 'those' or 'there' refers to if it isn't in the question). The spec is built for you and the numbers "
         "come from the data; the form tab shows the same answer. For a graph, also chart=true.")
    p = {"file": ask0[2]["file"], "question": {"type": "string", "description": "The person's question"},
         "chart": {"type": "boolean", "description": "They asked for a chart"}}
    mcp.TOOLS["file_ask"] = (file_ask, d, p, ["file", "question"])
