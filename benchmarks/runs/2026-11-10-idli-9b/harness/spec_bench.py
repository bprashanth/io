"""Segment: building the form spec from a question (what file_ask needs), isolated from the chat.

Every question with a reference in the scenario files becomes one item: the file's form (file_open's tabs, as
the chat model sees them), the user's earlier messages in that conversation, and the question. The model
returns a spec as JSON; the engine runs it; it counts as right when its answer carries the reference's
numbers (the same test score.py uses). Modes:
  free     plain JSON in the reply (what the chat model does inside a tool call)
  schema   JSON constrained by a schema whose enums are the form's own ids (response_format json_schema;
           llama.cpp turns it into a grammar), so an id can't be invented

  python harness/spec_bench.py --models muse30b,or-qwen35-9b --modes free,schema --out results/spec.json
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import convo  # noqa: E402
import idli  # noqa: E402
import score  # noqa: E402

SPEC_DOC = idli.__dict__.get("SPEC_DOC")


def items():
    out = []
    for name in ("dev", "held", "held2"):
        with open(os.path.join(BENCH, "scenarios", name + ".json")) as f:
            sc = json.load(f)
        for c in sc["conversations"]:
            said = []
            for s in c["steps"]:
                if s.get("user"):
                    said.append(s["user"])
                ch = s.get("check") or {}
                if "ref" in ch and said:
                    out.append({"id": f"{name}:{c['id']}:{len(said)}", "file": c["ref_file"], "history": said[:-1],
                                "question": said[-1], "refs": [ch["ref"]] + list(ch.get("alt_refs") or []),
                                "top_only": bool(ch.get("top_only"))})
    return out


def schema_for(tab):
    filt = {}
    for col, f in tab["filters"].items():
        if "values" in f:
            vals = [v for v in f["values"] if not str(v).startswith("... ")]
            item = {"type": "string", "enum": vals} if len(vals) == len(f["values"]) else {"type": "string"}
            filt[col] = {"anyOf": [{"type": "array", "items": item},
                                   {"type": "object", "properties": {"not": {"type": "array", "items": item}},
                                    "required": ["not"], "additionalProperties": False}]}
        else:
            filt[col] = {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}},
                         "additionalProperties": False}
    props = {"measures": {"type": "array", "items": {"type": "string", "enum": list(tab["measures"])}},
             "group_by": {"type": "array", "items": {"type": "string", "enum": list(tab["group_by"])}, "maxItems": 2},
             "filters": {"type": "object", "properties": filt, "additionalProperties": False}}
    if tab["presets"]:
        props["preset"] = {"type": "array", "items": {"type": "string", "enum": list(tab["presets"])}}
    return {"type": "object", "properties": props, "required": ["measures"], "additionalProperties": False}


def ask_model(spec, form, it, mode):
    tab = form["tabs"][0]
    prompt = ("You fill a form that answers questions about a spreadsheet. Reply with the form spec as JSON only.\n"
              "Spec keys: measures [ids], group_by [up to 2 ids], filters {column: [values]} or {column: {min, max}} "
              "or {column: {not: [values]}}, preset [ids]. measures [] lists matching rows (for who/which-rows "
              "questions). Use only ids and values from the form.\n\nThe form:\n"
              + json.dumps({k: tab[k] for k in ("tab", "row_noun", "measures", "group_by", "filters", "presets")},
                           ensure_ascii=False)
              + ("\n\nEarlier in this chat the user said:\n" + "\n".join("- " + h for h in it["history"])
                 if it["history"] else "") + "\n\nQuestion: " + it["question"])
    body = {"model": spec["model"], "temperature": 0, "max_tokens": spec.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}]}
    body.update(spec.get("extra") or {})
    if mode == "schema":
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "spec", "strict": True,
                                                                          "schema": schema_for(tab)}}
    req = urllib.request.Request(spec["base"].rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + convo.api_key(spec)})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.load(r)["choices"][0]["message"]["content"] or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--modes", default="free")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out_path = os.path.abspath(a.out)
    models = convo.load_models()
    mcp = idli.setup(tempfile.mkdtemp(prefix="idli9b-spec-"))
    score._mcp = mcp  # one fake Drive for the model's specs and the references
    forms = {}
    its = items()
    for it in its:
        if it["file"] not in forms:
            f = next(x for x in idli._drive()["files"] if x["path"] and it["file"].lower() in x["name"].lower())
            forms[it["file"]], _ = idli.call(mcp, "file_get", {"link": f["id"], "goal": "analyse"})
    res = json.load(open(out_path)) if os.path.exists(out_path) else {}
    for mid in a.models.split(","):
        for mode in a.modes.split(","):
            key = f"{mid}:{mode}"
            rows, t0 = [], time.time()
            for it in its:
                form = forms[it["file"]]
                try:
                    sp = ask_model(models[mid], form, it, mode)
                    err = None
                except Exception as e:
                    sp, err = None, str(e)[:200]
                ok = False
                ans = None
                if sp is not None:
                    r, e = idli.call(mcp, "file_ask", {"file": form["file"], "spec": sp})
                    ans = r.get("answer") if isinstance(r, dict) else None
                    err = r.get("error") if isinstance(r, dict) else None
                    if ans:
                        for ref in it["refs"]:
                            rt = score.ref_answer(it["file"], ref["spec"], ref.get("tab"))
                            if score.ref_ok(rt, ans, it["top_only"]):
                                ok = True
                rows.append({"id": it["id"], "q": it["question"], "spec": sp, "ok": ok, "error": err})
            n = sum(r["ok"] for r in rows)
            res[key] = {"right": f"{n}/{len(rows)}", "pct": round(100 * n / len(rows)),
                        "secs": round((time.time() - t0) / len(rows), 1), "rows": rows}
            print(f"{key:34} {n}/{len(rows)} ({res[key]['pct']}%)  {res[key]['secs']}s/item", flush=True)
            with open(out_path, "w") as f:
                json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
