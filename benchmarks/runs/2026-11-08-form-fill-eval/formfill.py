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
    try:
        with open(os.path.expanduser("~/.config/idlisseus/openrouter.json")) as f:
            k = json.load(f).get("api_key", "")
        if k.startswith("sk-or-"):
            return k
    except (OSError, ValueError):
        pass
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


def chat(model, system, user, history=()):
    body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}, *history],
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
    """Same answer, whatever the shape. Equivalences (documented in the README): a row listing matches a
    breakdown with the same number of rows (e.g. "who joined" grouped by name); a single total matches a
    one-row breakdown with the same value (e.g. Pune's hours grouped by the filtered district)."""
    if "__rows__" in gold:
        if "__rows__" in got:
            return gold["__rows__"] == got["__rows__"]
        return len(got) == gold["__rows__"] and gold["__rows__"] > 0
    if "__rows__" in got:
        return False
    gm = {k: list(v.values())[0] for k, v in gold.items()}
    if len(gm) == 1 and len(got) == 1 and "__rows__" not in got and () in gm:
        gold_v = gm[()]
        return any(v is not None and gold_v is not None and abs(v - gold_v) <= 0.01 * max(1, abs(gold_v))
                   for v in next(iter(got.values())).values() if isinstance(v, (int, float)))
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


def judge(q, out, con, fs, built, tab):
    """(correct, note, error to show the model or None)."""
    if q["gold"] == "teach":
        return bool(out) and out.get("action") == "teach", (out or {}).get("action", "no json"), None
    if not out:
        return False, "no json", "Reply with one JSON object only."
    if out.get("action") != "answer":
        return False, f"action={out.get('action')}", None
    spec = out.get("spec") or {}
    t = out.get("tab") if out.get("tab") in fs else tab
    try:
        got = result_map(fm.run(con, fs[t], built[t]["table"], spec), spec)
    except fm.SpecError as e:
        return False, f"spec error: {e}"[:200], f"{e} Use only ids from the form."
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200], f"{type(e).__name__}: {e}"[:300]
    for g in (q["gold"] if isinstance(q["gold"], list) else [q["gold"]]):
        want = result_map(fm.run(con, fs[tab], built[tab]["table"], g), g)
        if same(want, got, q.get("top")):
            return True, "", None
    return False, f"got {str(got)[:160]}", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="keywords,muse,9b,gemma4b,ministral3b")
    ap.add_argument("--only", default="")
    ap.add_argument("--questions", default="questions.json")
    ap.add_argument("--prompt", default="v1", choices=["v1", "v2"], help="v1: model resolves dates; v2: user's date words")
    ap.add_argument("--tag", default="", help="suffix for results files, e.g. a prompt version")
    ap.add_argument("--rescore", action="store_true", help="re-score saved outputs, no model calls")
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
    spec_text = SPEC["description"]  # v1, as Idli's file_ask tool describes it: the model resolves dates
    if a.prompt == "v2":  # tried and dropped: the user's date words, resolved by formkit.parse_when
        spec_text = re.sub(r"date \{column, period\}.*?a month like 2026-09\. ",
                           'date {column, text}: put the user\'s own date words in text (e.g. "last month", "since july", '
                           '"08/26 to 10/26", "this FY"); code works out the dates. Add date only if the user mentions a time. ',
                           spec_text, flags=re.S)
        spec_text = spec_text.replace('"date": {"period": "this_year"}', '"date": {"text": "this year"}')
    system = SYSTEM.format(today=Q["today"], spec=spec_text)
    board = {}
    for model in a.models.split(","):
        rows, ok, ok1, secs = [], 0, 0, 0.0
        for q in Q["questions"]:
            if a.only and q["id"] not in a.only.split(","):
                continue
            con, built, fs, tab = forms[q["file"]]
            brief = {"tabs": [_brief(fs[tab])]}
            saved = None
            retry_rec = None
            if a.rescore:
                try:
                    with open(os.path.join(HERE, f"results-{os.path.splitext(a.questions)[0]}-{model}{a.tag}.json")) as f:
                        saved = {r["id"]: r for r in json.load(f)}
                except OSError:
                    saved = None
            if saved is not None and q["id"] in saved:
                out, raw, took = saved[q["id"]]["output"], saved[q["id"]].get("raw", ""), saved[q["id"]]["secs"]
            elif model == "keywords":
                t0 = time.time()
                out, raw = keywords(fs[tab], q["q"], today), ""
                took = time.time() - t0
            else:
                raw, took = chat(model, system, f"Form:\n{json.dumps(brief, ensure_ascii=False)}\n\nQuestion: {q['q']}")
                out = parse(raw)
            first_out = out
            first_ok = None
            for attempt in (0, 1):
                verdict, note, err = judge(q, out, con, fs, built, tab)
                if attempt == 0:
                    first_ok = verdict
                if verdict or not err or model == "keywords" or attempt == 1:
                    break
                old = (saved or {}).get(q["id"], {}).get("retry")
                if old:  # re-scoring: reuse the saved retry
                    raw2, took2, retry_out = old.get("raw", ""), 0.0, old["output"]
                else:
                    raw2, took2 = chat(model, system, f"Form:\n{json.dumps(brief, ensure_ascii=False)}\n\nQuestion: {q['q']}",
                                       [{"role": "assistant", "content": json.dumps(out) if out else raw[-2000:]},
                                        {"role": "user", "content": f"The tool said: {err} Fix the JSON and reply again."}])
                    retry_out = parse(raw2)
                took += took2
                retry_rec = {"output": retry_out, "raw": raw2[-1500:] if not retry_out else ""}
                out = retry_out
            secs += took
            ok += verdict
            ok1 += bool(first_ok)
            rec = {"id": q["id"], "q": q["q"], "ok": verdict, "first_try_ok": bool(first_ok), "secs": round(took, 1),
                   "output": first_out, "note": note, "raw": raw[-1500:] if not first_out else ""}
            if out is not first_out:
                rec["retry"] = retry_rec
            rows.append(rec)
            print(f"{model:12s} {q['id']:4s} {'ok  ' if verdict else 'MISS'}{' (retry)' if verdict and not first_ok else ''} "
                  f"{took:5.1f}s {note[:110]}", flush=True)
        board[model] = (ok1, ok, len(rows), secs / max(1, len(rows)))
        with open(os.path.join(HERE, f"results-{os.path.splitext(a.questions)[0]}-{model}{a.tag}.json"), "w") as f:
            json.dump(rows, f, indent=1, ensure_ascii=False, default=str)
    print(f"\n{a.questions}: model   first try   with one retry   avg s/question")
    for m, (ok1, ok, n, s) in board.items():
        print(f"{m:12s}  {ok1:2d}/{n:2d}       {ok:2d}/{n:2d}           {s:5.1f}")


if __name__ == "__main__":
    main()
