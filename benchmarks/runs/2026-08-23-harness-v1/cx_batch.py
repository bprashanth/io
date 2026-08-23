#!/usr/bin/env python3
"""Run corpus ask cases through the containerised Codex harness, grade the final message,
and measure what the model saw (PII-looking lines in tool output)."""
import json, re, subprocess, sys, time
from pathlib import Path
ROOT = Path("/home/beeps/src/github.com/bprashanth/io")
sys.path.insert(0, str(ROOT / "benchmarks/t0"))
import run_corpus_cases as rc  # noqa
R = ROOT / "benchmarks/runs/2026-08-23-harness-v1"
model, config, label = sys.argv[1], sys.argv[2], sys.argv[3]   # config: free | tools
only = sys.argv[4].split(",") if len(sys.argv) > 4 else []
cases = json.loads((ROOT / "benchmarks/t0/ngo-corpus/cases.json").read_text())["cases"]
PII = re.compile(r"\b[6-9]\d{9}\b|\b\d{4} \d{4} \d{4}\b|[\w.]+@[\w.]+\.\w+|\+91\d{10}")
recs = []
for c in cases:
    if c["lane"] != "ask" or (only and c["id"] not in only):
        continue
    tag = f"{label}/{c['id']}"
    src = ROOT / "benchmarks/t0/ngo-corpus" / c["org"]
    if config == "tools":
        task = (f"{c['prompt']}\n\nRead AGENTS.md first and follow it. Use `python3 io.py schema` and `python3 io.py query \"...\"`. "
                "Finish with the answer as a short table in your final message.")
        extra = str(ROOT / "benchmarks/t0/harness-skill")
    else:
        task = (f"{c['prompt']}\n\nThe data files are in this folder (CSV/XLSX/TXT). Write and run python (pandas, openpyxl, duckdb available) "
                "to compute the answer, then finish with the answer as a short table in your final message.")
        extra = ""
    t0 = time.time()
    subprocess.run([str(R / "cx_run.sh"), model, tag, str(src), task, extra], check=False)
    d = R / tag
    last = (d / "last.md").read_text() if (d / "last.md").exists() else ""
    # grade: expected values present in the final message text
    exp = [list(x.values()) for x in c.get("expected_rows") or []]
    got_rows = [{"text": last}]
    ok, why = rc.rows_match(got_rows, exp, False, c["prompt"]) if exp and last.strip() else (False, "no final message")
    # what the model saw
    pii_lines = 0; cmds = 0; raw_read = False; usage = None
    for line in (d / "events.jsonl").read_text().splitlines():
        try: e = json.loads(line)
        except Exception: continue
        it = e.get("item") or {}
        if it.get("type") == "command_execution" and e.get("type") == "item.completed":
            cmds += 1
            out = it.get("aggregated_output") or ""
            pii_lines += sum(1 for l in out.splitlines() if PII.search(l))
            if re.search(r"\b(cat|head|tail|less|more)\b[^|\n]*\.(csv|txt|xlsx)|read_(csv|excel)\([^)]*\)[^\n]*\.(head|to_string|print)|print\(df", it.get("command", "")):
                raw_read = True
        if e.get("type") == "turn.completed":
            usage = e.get("usage")
    meta = (d / "meta.txt").read_text().strip() if (d / "meta.txt").exists() else ""
    rec = {"id": c["id"], "passed": ok, "why": why, "seconds": round(time.time() - t0, 1), "commands": cmds, "pii_lines_seen": pii_lines, "raw_read": raw_read,
           "usage": usage, "meta": meta, "last": last[:1500]}
    recs.append(rec)
    print(f"{'PASS' if ok else 'FAIL'} {c['id']} {c['prompt'][:60]:<60} cmds={cmds} pii={pii_lines} {rec['seconds']}s", flush=True)
    (R / label / "results.json").write_text(json.dumps({"model": model, "config": config, "passed": sum(r["passed"] for r in recs), "total": len(recs), "records": recs}, indent=1))
print(json.dumps({"model": model, "config": config, "passed": sum(r["passed"] for r in recs), "total": len(recs),
                  "mean_seconds": round(sum(r["seconds"] for r in recs) / max(len(recs), 1), 1), "pii_lines": sum(r["pii_lines_seen"] for r in recs)}))
