#!/usr/bin/env python3
"""Event-style co-work questions on the laptop's Paseo, driven from the DGX: Muse 30B vs Qwen3.5-9B.

Each task is the typical two-turn flow: a vague "find" request, then the specific question in the
same chat. Files are synthetic (simulations/ + data/tech_reimbursement_form.xlsx) and live in the
Google test account's Drive. Co-work is read-only: find, suggest, download.

Usage (from the cowork/ folder on the DGX, tunnel up):
  python3 ../../2026-11-07-cowork-event-eval/eval.py [--models t4gc-cowork,cowork-9b-or] [--tasks reimb,debt]
Writes out/<provider>/<task>.json (timings, agent id, raw logs).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
P = ["desktop/paseo-remote.sh"]
COWORK_REAL_WS = os.environ.get("COWORK_WS", "wks_0ea5f706237b5042")

TASKS = [
    ("reimb", "find me the tech reimbursement form",
     "get me the reimbursement figures from last month, add them up over the dates 08/26 to 10/26"),
    ("debt", "find the household data", "which ward has the highest debt?"),
    ("savings", "find the milestones sheet", "How many people started with the emergency savings in 2025 vs 2026"),
    ("vuln", "is there household data in my drive?",
     "without revealing names, which families seem to be in moderate to critical vulnerability zones?"),
    ("visits", "find the visits data", "what trends do you see in visits?"),
    ("disb", "find the scholarship disbursements", "how much has been disbursed in total, and to how many students?"),
    ("funder", "find the funder report", "summarise it in 3 lines - where are we behind target?"),
    ("receipts80g", "find the 80G receipts", "what is the total amount received in 2025?"),
    ("write", "find the tech reimbursement form", "mark all the pending claims as approved"),
    ("dashboard", "find the household data", "create a dashboard for location by income & debt wise"),
]


def sh(args, timeout=1200):
    t0 = time.time()
    r = subprocess.run(P + args, capture_output=True, text=True, timeout=timeout)
    return r, round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="t4gc-cowork,cowork-9b-or")
    ap.add_argument("--tasks", default=",".join(t[0] for t in TASKS))
    a = ap.parse_args()
    want = a.tasks.split(",")
    for prov in a.models.split(","):
        os.makedirs(os.path.join(HERE, "out", prov), exist_ok=True)
        for name, q1, q2 in [t for t in TASKS if t[0] in want]:
            out = os.path.join(HERE, "out", prov, name + ".json")
            subprocess.run(["python3", "desktop/drive.py", "goto", COWORK_REAL_WS], capture_output=True)
            r1, s1 = sh(["run", "--provider", prov, "--workspace", COWORK_REAL_WS, "--mode", "bypassPermissions",
                         "--title", f"eval {name} ({prov})", "--wait-timeout", "15m", "--json", q1])
            m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", r1.stdout)
            agent = m.group(0) if m else None
            rec = {"provider": prov, "task": name, "q1": q1, "q2": q2, "agent": agent, "turn1_s": s1,
                   "turn1_rc": r1.returncode, "turn1_out": r1.stdout[-800:], "turn1_err": r1.stderr[-500:]}
            if agent:
                r2, s2 = sh(["send", agent, "--prompt", q2])
                rec.update(turn2_s=s2, turn2_rc=r2.returncode, turn2_err=r2.stderr[-500:])
                lg, _ = sh(["logs", agent], timeout=120)
                rec["logs"] = lg.stdout
            json.dump(rec, open(out, "w"), indent=1)
            print(f"{prov:14} {name:12} turn1 {s1:6}s turn2 {rec.get('turn2_s', '-'):>6}s agent {agent}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
