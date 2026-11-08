#!/usr/bin/env python3
"""Who should fill the file form? Scores models (and a no-model baseline) on turning a vague question into a
form spec. The spec is run with the same code Idli uses (lib/formkit.py) and the *numbers* are compared with
the reference spec's numbers, so any spec that gives the right answer counts.

  cd benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
  .venv/bin/python ../../2026-11-08-form-fill-eval/formfill.py --models keywords,muse,9b,gemma4b,ministral3b

Models: muse = Muse 30B (llama.cpp, MUSE_URL, default http://127.0.0.1:8181), others via OpenRouter. The
OpenRouter key is read from OPENROUTER_API_KEY or the co-work 9B Claude settings file; it is never printed.
Writes results-<model>.json next to this file and prints a scorecard.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
COWORK = os.path.join(REPO, "benchmarks", "runs", "2026-11-06-oss-desktop-independent", "cowork")
sys.path.insert(0, COWORK)
os.environ.setdefault("IDLI_FILE_SKILLS", os.path.join(COWORK, "file-skills"))
import duckdb  # noqa: E402
from lib import filekit as fk  # noqa: E402
from lib import formkit as fm  # noqa: E402
from sites.files.tools import SPEC, _brief  # noqa: E402

OR_MODELS = {"9b": "qwen/qwen3.5-9b", "gemma4b": "google/gemma-3-4b-it", "ministral3b": "mistralai/ministral-3b-2512",
             "qwen30b-or": "qwen/qwen3-30b-a3b-instruct-2507"}


def openrouter_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for p in ("~/idli-insights/config/claude-or-9b/settings.json",):
        try:
            with open(os.path.expanduser(p)) as f:
                env = (json.load(f).get("env") or {})
        except (OSError, ValueError):
            continue
        for v in env.values():
            if isinstance(v, str) and v.startswith("sk-or-"):
                return v
    raise SystemExit("No OpenRouter key (set OPENROUTER_API_KEY).")


def chat(model, system, user):
    body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0, "max_tokens": 3000}
    if model == "muse":
        url = (os.environ.get("MUSE_URL") or "http://127.0.0.1:8181") + "/v1/chat/completions"
        body["model"] = "muse-glimmer-30b"
        body["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json"}
    else:
        url = "https://openrouter.ai/api/v1/chat/completions"
        body["model"] = OR_MODELS[model]
        body["response_format"] = {"type": "json_object"}
        body["reasoning"] = {"enabled": False}
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + openrouter_key()}
    t = time.time()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, json.dumps(body).encode(), headers)
            with urllib.request.urlopen(req, timeout=300) as r:
                out = json.load(r)
            msg = out["choices"][0]["message"]
            return (msg.get("content") or ""), time.time() - t
        except Exception as e:  # retry transient provider errors
            err = e
            time.sleep(3)
    return f"ERROR {type(err).__name__}: {err}", time.time() - t


SYSTEM = """You fill in a form for a spreadsheet, so that code can answer the user's question. You never compute numbers.
Today is {today}.
Reply with one JSON object and nothing else:
- {{"action": "answer", "tab": "<tab>", "spec": {{...}}}} to answer with the form;
- {{"action": "teach"}} if the form can't express the question (e.g. a ratio of two totals, comparing two columns
  row by row, growth rates); Idli will then ask to be taught;
- {{"action": "ask", "question_to_user": "..."}} only if a value is genuinely unclear.
Spec: {spec}
Use only the ids listed in the form."""


def parse(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


# ---------------------------------------------------------------- the no-model baseline
MONTHS = {m.lower(): i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                               "september", "october", "november", "december"], 1)}


def keywords(f, q, today):
    """Keyword matching + a small date parser: what a form-filler without a model could do."""
    ql = q.lower()
    words = set(re.findall(r"[a-z0-9]+", ql))
    spec = {}
    if re.search(r"\b(growth|per hour|ratio|more \w+ than|compared?)\b", ql):
        return {"action": "teach"}
    if re.search(r"\b(who|which|list|show me)\b", ql) and not re.search(r"\b(most|highest|top|least)\b", ql):
        spec["measures"] = []
    else:
        best, score = "rows", 0
        for m in f["measures"]:
            toks = set(re.findall(r"[a-z]+", (m["label"] + " " + m["id"]).lower())) - {"of", "number", "total", "rs"}
            s = len(toks & words) + (0.5 if m["id"] != "rows" and re.search(r"how much|total|spend|paid|money|give out", ql) else 0)
            if "average" in ql and "average" not in m["label"].lower():
                s -= 1
            if s > score:
                best, score = m["id"], s
        if re.search(r"\bhow many\b", ql) and score < 1.5:
            best = "rows"
        spec["measures"] = [best]
    for g in f["group_by"]:
        lab = g["label"].lower().split(":")[0]
        if re.search(r"\b(by|each|per|which|wise)\b", ql) and any(w in ql for w in re.findall(r"[a-z]+", lab) if len(w) > 3):
            if ":" in g["id"]:
                if ("month" in ql and g["id"].endswith(":month")):
                    spec.setdefault("group_by", []).append(g["id"])
            elif not spec.get("group_by"):
                spec.setdefault("group_by", []).append(g["id"])
    if re.search(r"monthly|month by month", ql):
        mg = [g["id"] for g in f["group_by"] if g["id"].endswith(":month")]
        if mg:
            spec["group_by"] = mg[:1]
    for x in f["filters"]:
        for v in x.get("values") or []:
            if len(v) > 2 and re.search(r"\b" + re.escape(v.lower()) + r"\b", ql):
                spec.setdefault("filters", {}).setdefault(x["column"], []).append(v)
            elif " " in v and re.search(r"\b" + re.escape(v.split()[0].lower()) + r"('s)?\b", ql):
                spec.setdefault("filters", {}).setdefault(x["column"], []).append(v)
    for p in f["presets"]:
        toks = set(re.findall(r"[a-z]+", p["label"].lower())) - {"and", "or", "the", "out", "only", "leave", "usual", "rule"}
        if toks & words:
            spec.setdefault("preset", []).append(p["id"])
    d = {}
    if "last month" in ql:
        d["period"] = "last_month"
    elif "last quarter" in ql:
        d["period"] = "last_quarter"
    elif "this financial year" in ql:
        d["period"] = "this_financial_year"
    elif "this year" in ql:
        d["period"] = "this_year"
    m = re.search(r"(\d{1,2})/(\d{1,2})\s*(?:to|-)\s*(\d{1,2})/(\d{1,2})", ql)
    if m:
        a, b, c, e = map(int, m.groups())
        mm1, dd1, mm2, dd2 = (a, b, c, e) if a <= 12 and c <= 12 else (b, a, e, c)
        d = {"from": f"{today.year}-{mm1:02d}-{dd1:02d}", "to": f"{today.year}-{mm2:02d}-{dd2:02d}"}
    m = re.search(r"since (" + "|".join(MONTHS) + ")", ql)
    if m:
        d = {"from": f"{today.year}-{MONTHS[m.group(1)]:02d}-01"}
    else:
        for name, i in MONTHS.items():
            if re.search(r"\b(in|for|from) " + name, ql) and "since" not in ql:
                d = {"from": f"{today.year}-{i:02d}", "to": f"{today.year}-{i:02d}"}
    if d and f["date_columns"]:
        spec["date"] = {"column": f["date_columns"][0], **d}
    m = re.search(r"(more than|over|above) (a lakh|\d[\d,]*)", ql)
    if m:
        num = 100000 if "lakh" in m.group(2) else float(m.group(2).replace(",", ""))
        nums = [x for x in f["filters"] if x["kind"] == "number"]
        if nums:
            spec.setdefault("filters", {})[nums[0]["column"]] = {"min": num}
    return {"action": "answer", "tab": f["tab"], "spec": spec}


# ---------------------------------------------------------------- scoring
def result_map(res, spec):
    """{group key: primary measure value}, or {"__rows__": n} for a row listing."""
    if not spec.get("measures"):
        return {"__rows__": list(res["total"].values())[0] if res["total"] else len(res["rows"])}
    mcols = [c for c in res["columns"] if res["total"] and c in res["total"]] or res["columns"][-len(spec["measures"]):]
    gcols = [c for c in res["columns"] if c not in mcols]
    out = {}
    for r in res["rows"]:
        out[tuple(str(r[c]) for c in gcols)] = {c: r[c] for c in mcols}
    return out


def same(gold, got, top):
    if "__rows__" in gold:
        return "__rows__" in got and gold["__rows__"] == got["__rows__"]
    gm = {k: list(v.values())[0] for k, v in gold.items()}
    if top:
        gk = max(gm, key=lambda k: (gm[k] or 0))
        for col in (next(iter(got.values())) or {}) if got else []:
            vals = {k: v.get(col) for k, v in got.items()}
            if vals and max(vals, key=lambda k: (vals[k] or 0)) == gk:
                return True
        return False
    def close(a, b):
        return (a or 0) == (b or 0) or (a is not None and b is not None and abs(a - b) <= 0.01 * max(1, abs(b)))
    for col in (next(iter(got.values())) or {}) if got else []:
        vals = {k: v.get(col) for k, v in got.items()}
        keys = {k for k in set(gm) | set(vals) if (gm.get(k) or 0) != 0 or (vals.get(k) or 0) != 0}
        if keys and all(close(vals.get(k), gm.get(k)) for k in keys):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="keywords,muse,9b,gemma4b,ministral3b")
    ap.add_argument("--only", default="")
    ap.add_argument("--questions", default="questions.json")
    a = ap.parse_args()
    with open(os.path.join(HERE, a.questions)) as f:
        Q = json.load(f)
    today = dt.date.fromisoformat(Q["today"])
    forms = {}
    for key, rel in Q["files"].items():
        p = os.path.join(REPO, rel)
        sheets, _ = fk.raw_sheets(p)
        skill, _, _ = fm.match_file(sheets)
        con = duckdb.connect()
        built = fm.build(con, p, skill, "t")
        tab = next(iter(built))
        forms[key] = (con, built, {t: fm.form(con, skill, t, built) for t in built}, tab)
    system = SYSTEM.format(today=Q["today"], spec=SPEC["description"])
    board = {}
    for model in a.models.split(","):
        rows, ok, secs = [], 0, 0.0
        for q in Q["questions"]:
            if a.only and q["id"] not in a.only.split(","):
                continue
            con, built, fs, tab = forms[q["file"]]
            brief = {"tabs": [_brief(fs[tab])]}
            if model == "keywords":
                t0 = time.time()
                out, raw = keywords(fs[tab], q["q"], today), ""
                took = time.time() - t0
            else:
                raw, took = chat(model, system, f"Form:\n{json.dumps(brief, ensure_ascii=False)}\n\nQuestion: {q['q']}")
                out = parse(raw)
            secs += took
            verdict, note = False, ""
            if q["gold"] == "teach":
                verdict = bool(out) and out.get("action") == "teach"
                note = (out or {}).get("action", "no json")
            elif not out or out.get("action") != "answer":
                note = f"action={(out or {}).get('action', 'no json')}"
            else:
                spec = out.get("spec") or {}
                try:
                    got = result_map(fm.run(con, fs[out.get("tab") or tab] if out.get("tab") in fs else fs[tab],
                                            built[out.get("tab") if out.get("tab") in built else tab]["table"], spec), spec)
                    golds = q["gold"] if isinstance(q["gold"], list) else [q["gold"]]
                    for g in golds:
                        want = result_map(fm.run(con, fs[tab], built[tab]["table"], g), g)
                        if same(want, got, q.get("top")):
                            verdict = True
                            break
                    note = "" if verdict else f"got {str(got)[:160]}"
                except fm.SpecError as e:
                    note = f"spec error: {e}"[:200]
                except Exception as e:
                    note = f"{type(e).__name__}: {e}"[:200]
            ok += verdict
            rows.append({"id": q["id"], "q": q["q"], "ok": verdict, "secs": round(took, 1), "output": out,
                         "note": note, "raw": raw[-1500:] if not out else ""})
            print(f"{model:12s} {q['id']:3s} {'ok  ' if verdict else 'MISS'} {took:5.1f}s {note[:120]}", flush=True)
        board[model] = (ok, len(rows), secs / max(1, len(rows)))
        with open(os.path.join(HERE, f"results-{os.path.splitext(a.questions)[0]}-{model}.json"), "w") as f:
            json.dump(rows, f, indent=1, ensure_ascii=False, default=str)
    print("\nmodel         correct   avg s/question")
    for m, (ok, n, s) in board.items():
        print(f"{m:12s}  {ok:2d}/{n:2d}     {s:5.1f}")


if __name__ == "__main__":
    main()
