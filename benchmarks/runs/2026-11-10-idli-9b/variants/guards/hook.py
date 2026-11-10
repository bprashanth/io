"""Tool-side scaffolding (each is a small patch to sites/*/tools.py; see patches/):

1. drive_find takes the user's goal (find | clean | analyse). For clean/analyse, when the match is clear or
   exactly one candidate is a spreadsheet, it opens the file itself (file_get) and returns that result, the
   way file_get already chains file_open. The model classifies intent into one enum instead of following
   a paragraph of `then` prose, and saves a step.
2. skill_delete only deletes after its own card was shown in this chat: `confirmed=true` on the first call
   gets the card back instead (a confirmation the model can't skip).
"""
SHEET_KINDS = ("Microsoft Excel", "Google Sheets", "CSV")


def apply(mcp, tools):
    from sites.files import tools as ft
    from sites.google import tools as g

    find0 = mcp.TOOLS["drive_find"]

    def drive_find(query, goal="find"):
        r = find0[0](query)
        goal = str(goal or "find").lower()
        if goal not in ("clean", "analyse", "analyze") or r.get("status") not in ("found", "choose"):
            return r
        res = r.get("results") or []
        sheets = [x for x in res if x.get("kind") in SHEET_KINDS and "Idli working copy" not in x.get("name", "")]
        pick = None
        if r["status"] == "found" and res and res[0].get("kind") in SHEET_KINDS:
            pick = res[0]
        elif r["status"] == "choose" and len(sheets) == 1:
            pick = sheets[0]
        if not pick:
            if sheets and len(sheets) < len(res):  # only offer the spreadsheets for a clean/analyse request
                r["results"] = sheets
            return r
        out = ft.t_file_get(pick["id"], goal="clean" if goal == "clean" else "analyse")
        out["found"] = {"id": pick["id"], "name": pick["name"], "folder": pick.get("folder"),
                        "opened_with_goal": "clean" if goal == "clean" else "analyse"}
        return out

    mcp.TOOLS["drive_find"] = (drive_find, find0[1] + " Pass goal: 'find' (they want to find, open or see a file), "
                               "'clean' (check it for mistakes) or 'analyse' (numbers, questions, charts). For clean and "
                               "analyse it opens the spreadsheet too when it's clear which one.",
                               {**find0[2], "goal": {"type": "string", "enum": ["find", "clean", "analyse"],
                                                     "description": "What the user wants to do with the file"}},
                               find0[3])

    del0 = mcp.TOOLS["skill_delete"]
    shown = set()

    def skill_delete(file_title, confirmed=False):
        key = str(file_title).lower()
        if confirmed and not any(key in s or s in key for s in shown):
            confirmed = False  # the card hasn't been shown: show it first
        out = del0[0](file_title, confirmed=confirmed)
        if out.get("card"):
            shown.add(key)
            then = out.get("then", "")
            import re
            m = re.search(r"file_title '([^']+)'", then)
            if m:
                shown.add(m.group(1).lower())
        return out

    mcp.TOOLS["skill_delete"] = (skill_delete,) + tuple(del0[1:])
