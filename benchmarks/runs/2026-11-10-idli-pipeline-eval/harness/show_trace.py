import json,sys
d=json.load(open(sys.argv[1]))
for t in d["turns"]:
    print("\n### USER:", t["input"].get("user"), "| expected:", json.dumps(t["input"].get("check"))[:200])
    for e in t["events"]:
        if e["type"]=="model":
            for c in e["tool_calls"]: print("  9B -> tool", c["name"], c["args"][:300])
            if e["text"]: print("  9B says:", e["text"][:500].replace("\n"," / "))
        elif e["type"]=="tool":
            r=e["result"]
            if isinstance(r,dict):
                keep={k:r[k] for k in r if k in("answer","spec","tab","spec_model_secs","cannot","then","error","chart_markdown")}
                print("  tool", e["name"], "returned:", json.dumps(keep,ensure_ascii=False)[:600])
            else: print("  tool", e["name"], "returned:", str(r)[:300])
        elif e["type"]=="guard": print("  [guard]", e["reason"][:150])
    print("  RESULT:", {k:t[k] for k in t if k not in("input","events")})
