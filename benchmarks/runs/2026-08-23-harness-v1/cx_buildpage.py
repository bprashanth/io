#!/usr/bin/env python3
"""Codex harness on corpus build/page cases: build via io tools (plan -> io.py page), page free-HTML."""
import json, subprocess, sys, time, shutil
from pathlib import Path
ROOT = Path("/home/beeps/src/github.com/bprashanth/io"); R = ROOT / "benchmarks/runs/2026-08-23-harness-v1"
model, label = sys.argv[1], sys.argv[2]; ids = sys.argv[3].split(",")
cases = {c["id"]: c for c in json.loads((ROOT / "benchmarks/t0/ngo-corpus/cases.json").read_text())["cases"]}
from playwright.sync_api import sync_playwright
recs = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for cid in ids:
        c = cases[cid]; tag = f"{label}/{cid}"; src = ROOT / "benchmarks/t0/ngo-corpus" / c["org"]
        if c["lane"] == "build":
            task = (f"{c['prompt']}\n\nRead AGENTS.md and plan_contract.md first. Explore with `python3 io.py schema` and test each panel's SQL with "
                    "`python3 io.py query`. Then write plan.json and run `python3 io.py page plan.json`. The deliverable is io_out/page.html. "
                    "Finish with one sentence saying what the page shows.")
            extra = str(ROOT / "benchmarks/t0/harness-skill")
        else:
            task = (f"{c['prompt']}\n\nWrite a single self-contained HTML file named page.html (inline CSS/JS, no CDNs, must work offline, no console errors). "
                    "Data files in this folder contain personal details: do not print them; if the page needs data, read the files with python and embed only aggregated values. "
                    "Finish with one sentence.")
            extra = ""
        t0 = time.time()
        subprocess.run([str(R / "cx_run.sh"), model, tag, str(src), task, extra], check=False)
        ws = Path.home() / ".cache/io-codex-ws" / tag / "work"
        page = ws / ("io_out/page.html" if c["lane"] == "build" else "page.html")
        rec = {"id": cid, "lane": c["lane"], "seconds": round(time.time() - t0, 1), "page_exists": page.exists()}
        d = R / tag
        if page.exists():
            shutil.copy(page, d / "page.html")
            p = b.new_page(viewport={"width": 1366, "height": 900}); errs = []
            p.on("pageerror", lambda e: errs.append(str(e)[:150]))
            p.goto(page.resolve().as_uri()); p.wait_for_timeout(800)
            p.screenshot(path=str(d / "page.png"), full_page=True)
            rec.update({"runtime_errors": errs[:3], "text_chars": len(p.inner_text("body")), "bytes": page.stat().st_size})
            p.close()
        usage = None; cmds = 0
        for line in (d / "events.jsonl").read_text().splitlines():
            try: e = json.loads(line)
            except Exception: continue
            if e.get("type") == "turn.completed": usage = e.get("usage")
            if (e.get("item") or {}).get("type") == "command_execution" and e.get("type") == "item.completed": cmds += 1
        rec.update({"usage": usage, "commands": cmds})
        recs.append(rec); print(json.dumps(rec), flush=True)
        (R / label / "results.json").write_text(json.dumps(recs, indent=1))
    b.close()
