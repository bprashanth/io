"""Quick feel: does the 9B split ask for details when it should, over-ask when it shouldn't, and route to Claude?

Each conversation runs through the product's own pieces: the form brief (ft._brief), the split prompt, this file's
question thread (spec + first answer line of each answered step, as tools.py keeps it), and the form engine for
answers. Only the prompt varies:
  P0  the frozen split prompt (today, the E7 / Codex-F winner)
  P1  P0 + two new outcomes: clarify (a vague term or a name that could be several values) and absent (names a
      person, place, funder or column the form doesn't have)
  P2  P1 + code hints: the form's values that match words in the question, and the question's names that match
      no value (the brief only lists 15 values per filter)
  python run.py P0 P1 P2
"""
import json, os, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import forms  # noqa: E402

NINE = os.environ.get("SPLIT_URL", "http://127.0.0.1:8291/v1/chat/completions")
MODEL = os.environ.get("SPLIT_MODEL", "qwen3.5-9b")
EXTRA = """
Two more replies, only when they apply:
  {"clarify": "<one short question back>", "options": ["<choice>", ...]}  (the question hangs on a vague word the
   form has no measure or filter for, like "poor", "senior", "big", "good", "recent", or a name that could be
   several values below. Give 2-4 options taken from the form. Don't ask when one reading clearly fits the form.)
  {"absent": "<what isn't there, in a few words>"}  (the question names a person, place, organisation, item or kind
   of information that the form doesn't have at all: no column, and no value like it)
Prefer a spec whenever the form can answer it; a follow-up that refers back is never vague."""


def prompt(variant, ft):
    p = ft.SPLIT_PROMPT
    if variant in ("P1", "P2"):
        p = p.replace("Reply with JSON only, one of:", "Reply with JSON only, one of:") + EXTRA
    return p


def hints(forms_, q):
    words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", q)}
    caps = [w for w in re.findall(r"\b[A-Z][A-Za-z0-9]+\b", q) if w.lower() not in ("i", "what", "how", "which", "who", "and", "show", "only", "just", "the")]
    found, seen = {}, set()
    for f in forms_.values():
        for x in f["filters"]:
            for v in x.get("values") or []:
                vw = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", str(v))}
                hit = (vw & words) or any(len(w) >= 4 and w in str(v).lower() for w in words)
                if hit:
                    found.setdefault(f"{f['tab']}.{x['column']}", []).append(v)
                    seen |= {w for w in words if w in str(v).lower()}
    missing = [c for c in caps if c.lower() not in seen and not any(c.lower() in str(lab).lower()
               for f in forms_.values() for lab in list(f.get("_measures", {})) + [x["label"] for x in f["filters"]])]
    out = "\n\nValues in the form that match words in the question: " + (json.dumps({k: v[:8] for k, v in found.items()}, ensure_ascii=False) if found else "none")
    if missing:
        out += "\nNames in the question that match no value or column in the form: " + ", ".join(missing)
    return out


def call(msg):
    body = {"model": MODEL, "temperature": 0, "max_tokens": 4096, "messages": [{"role": "user", "content": msg}]}
    req = urllib.request.Request(NINE, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.load(r)["choices"][0]["message"]["content"] or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return (json.loads(m.group(0)) if m else {"cannot": "no json"}), round(time.time() - t0, 1), text
    except ValueError:
        return {"cannot": "bad json"}, round(time.time() - t0, 1), text


def outcome(got):
    if got.get("clarify"):
        return "clarify"
    if got.get("absent"):
        return "absent"
    if got.get("cannot"):
        return got.get("route") if got.get("route") in ("chart_request", "teach_file") else "teach_file"
    return "answer"


def run(variant):
    mcp, ft, opened = forms.setup()
    convs = json.load(open(os.path.join(HERE, "convs.json")))["conversations"]
    rows = []
    for c in convs:
        rel = opened[c["file"]]
        fs = ft.files().open(rel)["forms"]
        thread = []
        for i, s in enumerate(c["steps"]):
            brief = [ft._brief(f) for f in fs.values()]
            msg = (prompt(variant, ft) + "\n\nThe form:\n" + json.dumps(brief, ensure_ascii=False)
                   + ("\n\nThe thread so far:\n" + "\n".join(json.dumps(t, ensure_ascii=False) for t in thread[-6:]) if thread else "")
                   + (hints(fs, s["q"]) if variant == "P2" else "")
                   + "\n\nQuestion: " + s["q"])
            got, secs, raw = call(msg)
            oc = outcome(got)
            ans, note = None, ""
            if oc == "answer":
                spec = got.get("spec") if isinstance(got.get("spec"), dict) else {}
                spec, err = ft._tolerant(rel, spec, got.get("tab"))
                out = ft._file_ask_spec(rel, spec, tab=got.get("tab"), chart=bool(got.get("chart")))
                if out.get("error"):
                    note = "form error: " + out["error"][:120]
                    oc = "answer-error"
                else:
                    ans = out["answer"]
                    if re.search(r"No rows match", ans):
                        note = "no rows match"
                    thread.append({"q": s["q"], "tab": got.get("tab"), "spec": got.get("spec"), "answer": ans.splitlines()[0][:160]})
            spec_txt = json.dumps(got, ensure_ascii=False)
            must_ok = all(m.lower() in spec_txt.lower() for m in s.get("must", [])) if oc == "answer" else None
            good = oc in s["ok"] and must_ok is not False
            # a filter on a value that isn't there comes back "No rows match": code can say "X isn't in the data"
            if not good and "absent" in s["ok"] and oc == "answer" and note == "no rows match":
                good, note = True, note + " (code can say: not in the data)"
            rows.append({"variant": variant, "file": c["file"], "step": i, "q": s["q"], "kind": s["kind"], "ok": s["ok"],
                         "outcome": oc, "good": good, "must_ok": must_ok, "got": got, "answer": (ans or "")[:200],
                         "note": note, "secs": secs})
            print(f"{variant} {'OK ' if good else 'BAD'} {oc:13} {s['kind']:28} {s['q'][:60]}  {note}", flush=True)
    return rows


if __name__ == "__main__":
    allrows = []
    for v in sys.argv[1:] or ["P0", "P1", "P2"]:
        allrows += [dict(r, model=MODEL) for r in run(v)]
    with open(os.path.join(HERE, os.environ.get("OUT", "results.json")), "w") as f:
        json.dump(allrows, f, indent=1, ensure_ascii=False, default=str)
