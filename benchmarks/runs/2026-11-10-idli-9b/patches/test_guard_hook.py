"""Check idli-guard-hook.py on a real Claude Code transcript: whole (no block), cut after a card-returning tool
with a text reply (card block), and with a made-up number appended (numbers block)."""
import json
import os
import subprocess
import sys
import tempfile

T = sys.argv[1]
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktop", "idli-guard-hook.py")
lines = open(T).read().splitlines()


def run(ls, label):
    p = tempfile.mktemp(suffix=".jsonl")
    open(p, "w").write("\n".join(ls) + "\n")
    out = subprocess.run([sys.executable, HOOK], input=json.dumps({"transcript_path": p, "stop_hook_active": False}),
                         capture_output=True, text=True).stdout.strip()
    print(f"{label:28} -> {out[:160] or '(no block)'}")


def asst(text):
    return json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}})


run(lines, "whole chat")
cut = next(i for i, l in enumerate(lines) if '"tool_result"' in l and "How would you like to start" in l)
run(lines[:cut + 1] + [asst("How would you like to start? - I have a question - Suggest analyses")], "card written as text")
run(lines + [asst("Ward D has Rs 4,92,652 of debt, about 25.1% of the total.")], "invented share")
run(lines + [asst("Ward D has Rs 4,92,652 of debt.")], "number from the tool")
