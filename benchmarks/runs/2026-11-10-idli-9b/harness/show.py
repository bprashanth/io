"""Print a transcript compactly.  python harness/show.py <transcript.json> [width]"""
import json
import sys

l = json.load(open(sys.argv[1]))
w = int(sys.argv[2]) if len(sys.argv) > 2 else 220
print(l["model"], l.get("variant"), l["conv"], l.get("secs"), "s")
for t in l["turns"]:
    print("STEP", t["step"], repr(t["input"].get("user") or ("[pick] " + t["input"].get("pick", ""))),
          "skipped" if t.get("skipped") else "", t.get("deviations") or "", t.get("secs") or "")
    for e in t["events"]:
        if e["type"] == "model":
            print("   M", e["secs"], "s", repr(e["text"][:w]), [c["name"] for c in e["tool_calls"]], e.get("finish"),
                  "r" + str(e.get("reasoning_chars")) if e.get("reasoning_chars") else "")
        elif e["type"] == "tool":
            print("   T", e["name"], json.dumps(e["args"])[:w // 1], "->", json.dumps(e.get("result"))[:w // 2])
        elif e["type"] == "card":
            q = (e["card"] or {}).get("questions") or [{}]
            print("   C", repr(q[0].get("question", ""))[:w // 2], [o.get("label") for o in q[0].get("options") or []],
                  "->", str(e["answer"])[-90:])
        else:
            print("  ", e)
