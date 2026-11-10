"""Transcripts made before the scripted user learned to click the obvious file on a "which file?" card: any with a
card_where_user_types deviation. List them, or delete them (--delete) so run.py redoes them.
  python harness/stale.py <run dir> [--delete]"""
import glob
import json
import os
import sys
from collections import Counter

n = Counter()
FIX = os.path.getmtime(os.path.join(os.path.dirname(os.path.abspath(__file__)), "convo.py"))  # the obvious-click fix
for p in glob.glob(os.path.join(sys.argv[1], "*", "*", "*.json")):
    if os.path.getmtime(p) > FIX:
        continue
    try:
        log = json.load(open(p))
    except ValueError:
        continue
    if "turns" not in log:
        continue
    if any("card_where_user_types" in (t.get("deviations") or []) for t in log["turns"]) and \
            not any(e.get("obvious_click") for t in log["turns"] for e in t["events"]):
        n[(log["model"], log.get("variant"))] += 1
        if "--delete" in sys.argv:
            os.remove(p)
for k, v in sorted(n.items()):
    print(k, v)
print("total", sum(n.values()))
