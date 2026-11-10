"""Smoke the tool layer: open every fixture spreadsheet through file_get and print what the model would see.

  python harness/probe.py [name-substring] [--full]
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idli  # noqa: E402

home = tempfile.mkdtemp(prefix="idli9b-probe-")
mcp = idli.setup(home)
want = [a for a in sys.argv[1:] if not a.startswith("--")]
d = idli._drive()
print("tools:", len(mcp.TOOLS), sorted(mcp.TOOLS))
print(json.dumps(idli.call(mcp, "start", {})[0])[:600])
print(json.dumps(idli.call(mcp, "drive_find", {"query": "household survey"})[0])[:900])
for f in d["files"]:
    if not f["path"] or (want and not any(w.lower() in f["name"].lower() for w in want)):
        continue
    out, err = idli.call(mcp, "file_get", {"link": f["id"], "goal": "analyse"})
    if "--full" in sys.argv:
        print(json.dumps(out, indent=1)[:6000])
    else:
        print(f"\n## {f['name']}: known={out.get('known')} err={out.get('error')} problems={out.get('problems')}")
        for t in out.get("tabs", []):
            print("  tab", t["tab"], "measures", list(t["measures"])[:12], "group_by", list(t["group_by"])[:10])
        print("  say:", (out.get("say_to_user") or out.get("then") or "")[:300])
