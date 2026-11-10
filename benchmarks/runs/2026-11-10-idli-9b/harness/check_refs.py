"""Run every ref/alt_ref spec in a scenario file through the engine; print the answers (or the errors).
  python harness/check_refs.py scenarios/<file>.json"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
path = os.path.abspath(sys.argv[1])
import score  # noqa: E402

with open(path) as f:
    sc = json.load(f)
bad = 0
for c in sc["conversations"]:
    print("##", c["id"], "|", " / ".join(s.get("user") or "[" + s.get("pick", "") + "]" for s in c["steps"])[:300])
    for s in c["steps"]:
        ch = s.get("check") or {}
        for r in ([ch["ref"]] if "ref" in ch else []) + list(ch.get("alt_refs") or []):
            try:
                a = score.ref_answer(c.get("ref_file", ""), r["spec"], r.get("tab"))
                print("   ok ", json.dumps(r["spec"])[:120], "->", a.replace("\n", " / ")[:160])
            except Exception as e:
                bad += 1
                print("   BAD", json.dumps(r["spec"])[:120], "->", str(e)[:200])
print("bad refs:", bad)
