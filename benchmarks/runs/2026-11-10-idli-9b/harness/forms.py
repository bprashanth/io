"""Print each taught fixture's form (measures, group_by, filters with values) and run reference specs.

  python harness/forms.py                      every form, compact
  python harness/forms.py ask <file-substr> '<spec json>' [tab]
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idli  # noqa: E402

home = tempfile.mkdtemp(prefix="idli9b-forms-")
mcp = idli.setup(home)
d = idli._drive()


def get(sub):
    f = next(x for x in d["files"] if x["path"] and sub.lower() in x["name"].lower())
    out, _ = idli.call(mcp, "file_get", {"link": f["id"], "goal": "analyse"})
    return f, out


if len(sys.argv) > 1 and sys.argv[1] == "ask":
    f, out = get(sys.argv[2])
    r, _ = idli.call(mcp, "file_ask", {"file": out["file"], "spec": json.loads(sys.argv[3]),
                                       **({"tab": sys.argv[4]} if len(sys.argv) > 4 else {})})
    print(json.dumps(r, indent=1)[:3000])
    sys.exit()
for f in d["files"]:
    if not f["path"]:
        continue
    _, out = get(f["name"])
    if not out.get("known"):
        continue
    print(f"\n## {f['name']}  (file: {out['file']})")
    for t in out["tabs"]:
        print(" tab:", t["tab"], "| rows:", t["row_noun"])
        print("  measures:", json.dumps(t["measures"]))
        print("  group_by:", json.dumps(t["group_by"]))
        print("  filters:", json.dumps(t["filters"])[:1500])
        print("  presets:", json.dumps(t["presets"]))
