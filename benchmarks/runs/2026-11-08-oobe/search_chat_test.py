#!/usr/bin/env python3
"""Ask Idli to find files from a fresh chat in the Idli workspace, as a person would, and time the answer.

  python3 search_chat_test.py --provider t4gc-cowork --thinking low
"""
import argparse
import json
import os
import re
import time

import oobe_test as o

IDLI_WS = "wks_0ea5f706237b5042"
ASKS = [("find the volunteer register", "volunteer_register"),
        ("where's the 80g receipts file?", "80g_receipts"),
        ("the sheet with tree species and trunk measurements", "field_vars_indicators"),
        ("money we gave out to people last quarter", "disbursements")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="t4gc-cowork")
    ap.add_argument("--thinking", default="low")
    a = ap.parse_args()
    out = []
    for q, want in ASKS:
        t0 = time.time()
        r = o.paseo("run", "--provider", a.provider, "--workspace", IDLI_WS, "--mode", "bypassPermissions",
                    "--thinking", a.thinking, "--title", f"search test: {q[:20]}", "--no-wait", "--json", q)
        try:
            agent = json.loads(r)["agentId"]
        except (ValueError, KeyError):
            print("could not start", r[:200]); continue
        o.wait(lambda: o.status(agent) == "idle" and time.time() - t0 > 5 or None, 240, 2)
        took = round(time.time() - t0, 1)
        log = o.log(agent)
        tools = re.findall(r"^\[mcp__cowork__(\w+)\]", log, re.M)
        tail = [l for l in log.splitlines() if l.strip()][-3:]
        found = want.lower() in " ".join(tail).lower()
        res = {"provider": a.provider, "thinking": a.thinking, "q": q, "seconds": took, "tools": tools,
               "names_file": found, "tail": tail}
        print(json.dumps(res, ensure_ascii=False)[:400], flush=True)
        out.append(res)
        o.paseo("archive", agent)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_chat.jsonl"), "a") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
