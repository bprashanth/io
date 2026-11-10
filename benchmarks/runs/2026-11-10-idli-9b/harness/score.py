"""Score transcripts against their scenario checks.

A *span* is what the model did from one user step until the next step the user starts (an optional card
click and its checks belong to the span before it). A span passes when every check in it passes and nothing
went wrong (loop, step cap, timeout, API error, invented number). Each span gets one segment (what it
mostly tests) so results roll up per segment.

  python harness/score.py results/<run>/            -> results/<run>/scores.json + a table
"""
import glob
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)

NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
FATAL = {"loop_same_call", "step_cap", "turn_timeout"}
_ref_cache = {}
_mcp = None


def norm(n):
    s = n.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return s
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0").rstrip(".")


def numbers(text):
    return [norm(m) for m in NUM.findall(text or "")]


def ref_answer(ref_file, spec, tab=None):
    global _mcp
    key = json.dumps([ref_file, spec, tab], sort_keys=True)
    if key in _ref_cache:
        return _ref_cache[key]
    import idli
    if _mcp is None:
        _mcp = idli.setup(tempfile.mkdtemp(prefix="idli9b-score-"))
    f = next(x for x in idli._drive()["files"] if x["path"] and ref_file.lower() in x["name"].lower())
    got, _ = idli.call(_mcp, "file_get", {"link": f["id"], "open_after": False})
    out, err = idli.call(_mcp, "file_ask", {"file": got["file"], "spec": spec, **({"tab": tab} if tab else {})})
    if err or out.get("error"):
        raise RuntimeError(f"bad ref {spec}: {out}")
    _ref_cache[key] = out["answer"]
    return out["answer"]


def segment_of(checks):
    keys = json.dumps(checks)
    for seg, pat in (("start", '"first_tool": "start"'), ("clean", "working_copy"), ("teach", "teach_"),
                     ("chart", "chart_relayed|chart_request"), ("ask", '"ref"'), ("skills", "skill"),
                     ("find", "drive_find|file_peek|asks_which_file|lists_choices|asks_more"),
                     ("open", '"file_get"|"file_ask"|"card"')):
        if re.search(pat, keys):
            return seg
    return "other"


def ref_ok(ref_text, text, top_only):
    rn = [n for n in numbers(ref_text) if n not in ("1", "2")] or numbers(ref_text)
    # the label lines ("Ward D: Rs 4,92,652") give the values; the first value is the top row
    vals = [norm(m) for m in re.findall(r":\s*(?:Rs\s*)?(-?[\d,]+(?:\.\d+)?)", ref_text)] or rn
    tn = set(numbers(text))
    if not vals:
        return False
    if top_only:
        return vals[0] in tn
    hit = sum(1 for v in vals if v in tn)
    return hit / len(vals) >= 0.8 if len(vals) > 1 else hit == 1


def score_conv(sc_conv, log, seen_before):
    steps = sc_conv["steps"]
    spans, cur = [], None
    for idx, st in enumerate(steps):
        if st.get("optional") and cur is not None:
            cur["steps"].append(idx)
            cur["checks"].append(st.get("check") or {})
        else:
            cur = {"steps": [idx], "checks": [st.get("check") or {}]}
            spans.append(cur)
    turns = log["turns"]
    allowed = set()  # numbers the user or a tool has said so far
    for t in turns:
        inp = t.get("input") or {}
        allowed.update(numbers(inp.get("user", "")))
    out = []
    for sp in spans:
        evs, devs = [], []
        for t in turns:
            if t["step"] in sp["steps"]:
                evs += t["events"]
                devs += t.get("deviations") or []
        tools = [e for e in evs if e["type"] in ("tool", "card")]
        names = [("AskUserQuestion" if e["type"] == "card" else e["name"]) for e in tools]
        text = "\n".join(e["text"] for e in evs if e["type"] == "model" and e.get("text"))
        for e in evs:
            if e["type"] == "tool":
                allowed.update(numbers(json.dumps(e.get("result"), ensure_ascii=False)))
                allowed.update(numbers(json.dumps(e.get("args"), ensure_ascii=False)))
            if e["type"] == "card":
                allowed.update(numbers(json.dumps(e.get("card"), ensure_ascii=False)))
        res = {"steps": sp["steps"], "checks": {}, "deviations": devs,
               "secs": round(sum(e.get("secs", 0) for e in evs if e["type"] == "model"), 1),
               "model_calls": sum(1 for e in evs if e["type"] == "model"),
               "api_error": any(e["type"] == "api_error" for e in evs),
               "bad_json": sum(1 for e in evs if e.get("error") == "bad_json"),
               "tool_errors": sum(1 for e in evs if e["type"] == "tool" and e.get("error")),
               "text": text[:1500], "tools": names}
        merged = {}
        for ch in sp["checks"]:
            for k, v in ch.items():
                if k in merged and k == "tools_any":
                    merged.setdefault("tools_any_more", []).append(v)
                else:
                    merged[k] = v
        res["segment"] = segment_of(merged)
        c = res["checks"]
        if "first_tool" in merged:
            c["first_tool"] = bool(names) and names[0] == merged["first_tool"]
        for key in ("tools_any",):
            if key in merged:
                c[key] = any(n in names for n in merged[key])
        for i, more in enumerate(merged.get("tools_any_more", [])):
            c[f"tools_any_{i + 2}"] = any(n in names for n in more)
        if "tools_none" in merged:
            c["tools_none"] = not any(n in names for n in merged["tools_none"])
        if merged.get("card"):
            c["card"] = "AskUserQuestion" in names
        for tool, params in (merged.get("args") or {}).items():
            calls = [e for e in tools if e["type"] == "tool" and e["name"] == tool]

            def val(a, p):
                v = (a or {}).get(p) if isinstance(a, dict) else None
                return json.dumps(v) if not isinstance(v, str) else v
            c[f"args:{tool}"] = any(all(re.search(rx, val(e["args"], p) or "", re.I) for p, rx in params.items())
                                    for e in calls)
        for tool, n in (merged.get("max_calls") or {}).items():
            c[f"max_calls:{tool}"] = names.count(tool) <= n
        if "ref" in merged:
            refs = [merged["ref"]] + list(merged.get("alt_refs") or [])
            asks = [e for e in tools if e["type"] == "tool" and e["name"] == "file_ask" and not e.get("error")
                    and isinstance(e.get("result"), dict) and e["result"].get("answer")]
            spec_ok = relay_ok = False
            for r in refs:
                try:
                    rt = ref_answer(sc_conv.get("ref_file", ""), r["spec"], r.get("tab"))
                except Exception as ex:
                    res["ref_error"] = str(ex)[:200]
                    continue
                if any(ref_ok(rt, a["result"]["answer"], merged.get("top_only")) for a in asks):
                    spec_ok = True
                    if ref_ok(rt, text, merged.get("top_only")):
                        relay_ok = True
            c["spec"] = spec_ok
            c["relay"] = relay_ok
        if merged.get("chart_relayed"):
            c["chart_relayed"] = bool(re.search(r"!\[[^\]]*\]\([^)]+\.svg\)", text))
        if merged.get("lists_choices"):
            c["lists_choices"] = len(re.findall(r"(?i)household survey (2025|2024|questionnaire)", text)) >= 2
        if merged.get("asks_which_file") or merged.get("asks_more"):
            c["asks"] = "?" in text
        invented = [n for n in numbers(text) if n not in allowed and not re.fullmatch(r"[0-9]", n)]
        res["invented"] = invented[:10]
        if merged.get("no_invented") or merged.get("no_numbers"):
            c["no_invented"] = not invented
        fatal = bool(set(devs) & FATAL) or res["api_error"]
        res["pass"] = all(c.values()) and not fatal and not invented
        res["fatal"] = fatal
        out.append(res)
    return out


def main(run_dir):
    run_dir = os.path.abspath(run_dir)  # idli.setup changes the working folder
    scen = {}
    for p in glob.glob(os.path.join(BENCH, "scenarios", "*.json")):
        with open(p) as f:
            for c in json.load(f)["conversations"]:
                scen[(os.path.basename(p), c["id"])] = c
    rows = []
    for p in sorted(glob.glob(os.path.join(run_dir, "**", "*.json"), recursive=True)):
        if os.path.basename(p) in ("scores.json", "judge.json"):
            continue
        with open(p) as f:
            log = json.load(f)
        if "turns" not in log:
            continue
        sc = scen[(log["scenario"], log["conv"])]
        for i, sp in enumerate(score_conv(sc, log, None)):
            rows.append({"model": log["model"], "variant": log.get("variant", "base"), "scenario": log["scenario"],
                         "conv": log["conv"], "rep": log.get("rep", 0), "span": i, **sp})
    with open(os.path.join(run_dir, "scores.json"), "w") as f:
        json.dump(rows, f, indent=1)
    table(rows)


def table(rows):
    from collections import defaultdict
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        k = (r["model"], r["variant"])
        agg[k]["all"].append(r["pass"])
        agg[k][r["segment"]].append(r["pass"])
        if "spec" in r["checks"]:
            agg[k]["spec"].append(r["checks"]["spec"])
            agg[k]["relay"].append(r["checks"]["relay"])
        agg[k]["invented"].append(bool(r["invented"]))
        agg[k]["fatal"].append(r["fatal"])
        agg[k]["secs"].append(r["secs"])
    segs = ["start", "find", "open", "ask", "chart", "teach", "clean", "skills"]
    print(f"{'model':28} {'variant':10} {'ALL':>6} " + " ".join(f"{s:>7}" for s in segs)
          + f" {'spec':>6} {'relay':>6} {'invent':>6} {'fatal':>6} {'s/span':>6}")
    for (m, v), d in sorted(agg.items()):
        def pct(x):
            return f"{100 * sum(x) / len(x):5.0f}%" if x else "     -"
        print(f"{m:28} {v:10} {pct(d['all']):>6} " + " ".join(f"{pct(d[s]):>7}" for s in segs)
              + f" {pct(d['spec']):>6} {pct(d['relay']):>6} {pct(d['invented']):>6} {pct(d['fatal']):>6}"
              + f" {sum(d['secs']) / max(1, len(d['secs'])):6.1f}")


if __name__ == "__main__":
    main(sys.argv[1])
