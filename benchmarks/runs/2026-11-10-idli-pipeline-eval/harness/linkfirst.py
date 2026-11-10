"""E7: rewrite the 9B benchmark's chats for the product without file search. The person pastes the file's link;
chats that were only about finding a file (or listing learned files, or Start here) are dropped.
Also applies the E6 benchmark fix to held3 r03 (no paid hardware claims exist: ask about approved ones).

  python harness/linkfirst.py   -> scenarios/{dev,held,held2,held3}.json in this eval's folder
"""
import copy
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
B9 = os.path.join(os.path.dirname(EVAL), "2026-11-10-idli-9b")
FIND_ONLY = {"find", "peek", "skills", "starthere"}


def link(fid):
    return f"https://docs.google.com/spreadsheets/d/{fid}/edit"


def file_id(drive, ref):
    ref = (ref or "").lower()
    for f in drive["files"]:
        if f.get("path") and f["name"].lower().startswith(ref):
            return f["id"]
    return None


def convert(conv, drive):
    if set(conv.get("segments") or []) <= FIND_ONLY:
        return None, "find-only"
    fid = file_id(drive, conv.get("ref_file"))
    if not fid:
        return None, "no file"
    c = copy.deepcopy(conv)
    c["segments"] = [s for s in c["segments"] if s not in ("find", "peek")]
    out, i, linked = [], 0, False
    steps = c["steps"]
    while i < len(steps):
        s = steps[i]
        ch = s.get("check") or {}
        finds = set(ch.get("tools_any") or []) & {"drive_find"} or ch.get("lists_choices")
        first_ask = s.get("user") and not linked and ch.get("first_tool") != "start" and \
            not re.fullmatch(r"(?i)\s*(hi|hello|hey|start)\W*", s["user"])
        if first_ask:
            s = {**s, "user": s["user"].rstrip(" .") + " " + link(fid)}
            ch = {k: v for k, v in ch.items() if k not in ("lists_choices", "tools_none", "asks_more")}
            if finds or not ch.get("tools_any"):
                ch["tools_any"] = ["file_get"]
            if "file_get" in ch["tools_any"]:
                ch["args"] = {"file_get": {"link": fid}}
            s["check"] = ch
            linked = True
            out.append(s)
            # the old "which one?" answer or the peek card that followed the search is now redundant
            while i + 1 < len(steps):
                nx = steps[i + 1]
                nch = nx.get("check") or {}
                if (nx.get("user") and "file_get" in (nch.get("tools_any") or []) and nch.get("args")) or \
                        "file_peek" in (nch.get("tools_any") or []):
                    if nch.get("card"):
                        s["check"]["card"] = True
                    i += 1
                    continue
                break
            if not (i + 1 < len(steps) and steps[i + 1].get("pick")):
                out.append({"pick": "question", "optional": True, "check": {}})
        else:
            out.append(s)
        i += 1
    c["steps"] = out
    return c, None


def fix_r03(c):
    for s in c["steps"]:
        u = s.get("user") or ""
        if "paid hardware claims" in u:
            s["user"] = u.replace("paid hardware claims", "approved hardware claims")
        ref = (s.get("check") or {}).get("ref")
        if ref and ref["spec"].get("filters", {}).get("category") == ["Hardware"]:
            ref["spec"]["filters"]["status"] = ["Approved"]


def main():
    drive = json.load(open(os.path.join(B9, "fixtures", "drive.json")))
    os.makedirs(os.path.join(EVAL, "scenarios"), exist_ok=True)
    report = {}
    for name in ("dev", "held", "held2", "held3"):
        d = json.load(open(os.path.join(B9, "scenarios", name + ".json")))
        kept, dropped = [], []
        for conv in d["conversations"]:
            c, why = convert(conv, drive)
            if c is None:
                dropped.append(f"{conv['id']} ({why})")
                continue
            if c["id"] == "r03-claim-size":
                fix_r03(c)
            kept.append(c)
        d = {**d, "conversations": kept}
        json.dump(d, open(os.path.join(EVAL, "scenarios", name + ".json"), "w"), indent=1)
        report[name] = {"kept": len(kept), "dropped": dropped}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
