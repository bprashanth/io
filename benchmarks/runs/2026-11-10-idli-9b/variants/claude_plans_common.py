"""Claude plans, the local model executes. The chat model (a local 9B) runs every flow; for a question, file_ask
asks Claude for the spec, but Claude only ever sees:
  - the question, redacted on this machine by the GLiNER scanner (io's privacy server, :8899): names, places, ids
    become placeholders (<village_1>, <person_name_2>);
  - the form's ids and labels (Claude wrote those from fake data) and its filter values, redacted the same way
    with the same placeholders (so "Thonimalai" in the question and "Thonimalai Village" in the values line up);
  - earlier redacted questions in this chat and the specs that ran. Never an answer, a number or a row.
Claude's spec comes back with placeholders; they are put back and matched to the real values here, and the
engine runs it here. Backtrack (shape only): if the engine errors or nothing matches, Claude gets the error text or
"0 rows" (no values) and one chance to repair the spec.
Cost, latency and redaction stats go to <IDLI_HOME>/claude_plans.jsonl (not to the chat model).
"""
import difflib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.environ.get("IDLI_SCANNER", "http://127.0.0.1:8899/scan")
PROMPT = open(os.path.join(HERE, "split_common.py")).read().split('PROMPT = """', 1)[1].split('"""', 1)[0]
PROMPT += ("\nNames, places and ids are replaced by placeholders like <village_1>; use the placeholders exactly as "
           "they appear (in the question or in the form's values) when you filter on them.")


def _guards2():
    p = os.path.join(HERE, "guards2", "hook.py")
    s = importlib.util.spec_from_file_location("guards2_hook", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def scan(texts):
    req = urllib.request.Request(SCAN, json.dumps({"texts": texts}).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["results"]


class Redactor:
    def __init__(self):
        self.ph, self.back, self.n = {}, {}, {}

    def key(self, text, label):
        k = text.strip().lower()
        if k not in self.ph:
            self.n[label] = self.n.get(label, 0) + 1
            p = f"<{re.sub(r'[^a-z_]', '_', label.lower())}_{self.n[label]}>"
            self.ph[k], self.back[p] = p, text.strip()
        return self.ph[k]

    def apply(self, text, spans):
        out, last = [], 0
        for a, b, label, score in sorted(spans):
            if a < last:
                continue
            out += [text[last:a], self.key(text[a:b], label)]
            last = b
        out.append(text[last:])
        s = "".join(out)
        for k, p in sorted(self.ph.items(), key=lambda x: -len(x[0])):  # known entities inside other strings
            s = re.sub(re.escape(k), p, s, flags=re.I) if len(k) >= 3 else s
        return s

    def restore(self, s):
        return re.sub(r"<[a-z_]+_\d+>", lambda m: self.back.get(m.group(0), m.group(0)), s)


def claude(model, prompt):
    t0 = time.time()
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["claude", "-p", prompt, "--model", model, "--output-format", "json", "--tools="],
                           capture_output=True, text=True, timeout=300, cwd=d, stdin=subprocess.DEVNULL)
    out = json.loads(r.stdout)
    text = out.get("result") or ""
    m = re.search(r"\{.*\}", text, re.S)
    return (json.loads(m.group(0)) if m else {"cannot": "no spec"}), out.get("total_cost_usd") or 0.0, \
        round(time.time() - t0, 1)


def apply(mcp, model, backtrack=True):
    _guards2().apply(mcp, None)
    from sites.files import tools as ft
    ask0 = mcp.TOOLS["file_ask"]
    threads, red = {}, Redactor()
    logp = os.path.join(os.environ.get("IDLI_HOME", tempfile.gettempdir()), "claude_plans.jsonl")

    def brief(file):
        forms = ft.files().open(file)["forms"]
        bs = [ft._brief(f) for f in forms.values()]
        vals = sorted({str(v) for b in bs for f in b["filters"].values() for v in (f.get("values") or [])
                       if not str(v).startswith("... ")})
        return bs, vals

    def red_brief(bs):
        out = []
        for b in bs:
            b = json.loads(json.dumps(b))
            for f in b["filters"].values():
                if f.get("values"):
                    f["values"] = [red.apply(str(v), []) if not str(v).startswith("... ") else v for v in f["values"]]
            b.pop("summary", None)
            out.append(b)
        return out

    def map_back(spec, bs):
        allv = {}
        for b in bs:
            for col, f in b["filters"].items():
                allv[col] = [str(v) for v in (f.get("values") or []) if not str(v).startswith("... ")]

        def fix(col, v):
            if not isinstance(v, str):
                return v
            r = red.restore(v)
            opts = allv.get(col) or []
            if not opts or r in opts:
                return r
            low = {o.lower(): o for o in opts}
            if r.lower() in low:
                return low[r.lower()]
            cont = [o for o in opts if r.lower() in o.lower()]
            if len(cont) == 1:
                return cont[0]
            close = difflib.get_close_matches(r, opts, n=1, cutoff=0.6)
            return close[0] if close else r
        for col, v in list((spec.get("filters") or {}).items()):
            if isinstance(v, list):
                spec["filters"][col] = [fix(col, x) for x in v]
            elif isinstance(v, dict) and isinstance(v.get("not"), list):
                v["not"] = [fix(col, x) for x in v["not"]]
        return spec

    def file_ask(file, spec=None, tab=None, chart=False, question=None):
        if not question:
            return ask0[0](file, spec or {}, tab=tab, chart=chart)
        bs, vals = brief(file)
        try:
            spans = scan([question] + vals)
        except Exception as e:
            return {"error": f"The privacy scanner isn't running ({type(e).__name__}).", "then": "Say so in one line."}
        for v, sp in zip(vals, spans[1:]):  # values first, so the question reuses their placeholders
            red.apply(v, sp)
        rq = red.apply(question, spans[0])
        thread = threads.get(file, [])[-6:]
        prompt = (PROMPT + "\n\nThe form:\n" + json.dumps(red_brief(bs), ensure_ascii=False)
                  + ("\n\nThe thread so far:\n" + "\n".join(json.dumps(t, ensure_ascii=False) for t in thread) if thread else "")
                  + "\n\nQuestion: " + rq)
        rec = {"question": question, "redacted": rq, "intact": rq == question, "placeholders": len(spans[0]),
               "model": model, "calls": 0, "cost": 0.0, "secs": 0.0}
        try:
            got, cost, secs = claude(model, prompt)
        except Exception as e:
            return {"error": f"The planner failed: {type(e).__name__}", "then": "Try file_ask again."}
        rec.update(calls=1, cost=cost, secs=secs)
        out = None
        for attempt in range(2 if backtrack else 1):
            if got.get("cannot"):
                break
            sp = map_back(json.loads(json.dumps(got.get("spec") or {})), bs)
            out = ask0[0](file, sp, tab=got.get("tab") or tab, chart=bool(got.get("chart")) or chart)
            bad = (out or {}).get("error") or ("No rows match" in str((out or {}).get("answer") or "") and "0 rows")
            if not bad or attempt == 1 or not backtrack:
                break
            shape = out.get("error") if out.get("error") else "The spec ran but no rows matched (0 rows)."
            g2, c2, s2 = claude(model, prompt + "\n\nYou answered: " + json.dumps(got) + "\nWhat happened (shape only, "
                                "no data): " + str(shape) + "\nReply with a repaired JSON answer.")
            rec.update(calls=rec["calls"] + 1, cost=rec["cost"] + c2, secs=rec["secs"] + s2, backtracked=True)
            got = g2
        with open(logp, "a") as f:
            f.write(json.dumps(rec) + "\n")
        if got.get("cannot") or out is None:
            route = got.get("route") or "teach_file"
            return {"answer": None, "cannot": got.get("cannot"),
                    "then": ("Call chart_request with their words (Claude designs this chart on fake data)."
                             if route == "chart_request" else
                             "Call teach_file with their question and missing = '" + str(got.get("cannot")) + "'.")}
        if isinstance(out, dict) and out.get("answer"):
            threads.setdefault(file, []).append({"q": rq, "tab": got.get("tab"), "spec": got.get("spec")})
        return out

    d = ("Answer a question about an opened file. Pass `question`: the person's question in their words (add what "
         "'that', 'those' or 'there' refers to if it isn't in the question). The spec is built for you and the numbers "
         "come from the data; the form tab shows the same answer. For a graph, also chart=true.")
    p = {"file": ask0[2]["file"], "question": {"type": "string", "description": "The person's question"},
         "chart": {"type": "boolean", "description": "They asked for a chart"}}
    mcp.TOOLS["file_ask"] = (file_ask, d, p, ["file", "question"])
