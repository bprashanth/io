"""Idli's real tools, in-process, with the browser-bound parts replaced by a fake Drive on disk.

Kept real: start, drive_find (the real index and ranking), file_open (the real cards and `then`),
file_ask (the real form engine), teach_file (the real fake copy and card), skills_list, skill_delete,
working_copy (the real marked workbook, built locally), chart_request (real card).
Stubbed: downloads (file_get copies from fixtures/drive), Drive uploads (working_copy keeps the copy
locally and registers it in the fake Drive), Paseo tabs, the Teach chat start (teach_send), live Drive
search (returns nothing), Gmail.

Each conversation runs in its own process with its own IDLI_HOME / data dir (see convo.py), so the
tools' module-level caches never mix conversations.
"""
import json
import os
import re
import shutil
import sys
import time

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(BENCH)))
COWORK = os.path.join(REPO, "benchmarks", "runs", "2026-11-06-oss-desktop-independent", "cowork")
FIXTURES = os.path.join(BENCH, "fixtures")
DISALLOWED = {"gmail_draft_reply", "sheet_query", "sheet_profile"}  # as in desktop/setup-laptop.py


def setup(home):
    """Point every Idli path at `home` (a fresh folder per conversation) and load the tools."""
    data = os.path.join(home, "cowork-real")
    for d in (data, os.path.join(home, "config"), os.path.join(home, "teach")):
        os.makedirs(d, exist_ok=True)
    skills = os.path.join(home, "file-skills")
    if not os.path.isdir(skills):
        shutil.copytree(os.path.join(FIXTURES, "skills"), skills)
    with open(os.path.join(data, "cowork.sites"), "w") as f:
        f.write("google\nfiles\n")
    os.environ.update(IDLI_HOME=home, COWORK_DATA_DIR=data, IDLI_FILE_SKILLS=skills,
                      IDLI_TEACH_DIR=os.path.join(home, "teach"), IDLI_NO_WALL="1",
                      IDLI_DRIVE_INDEX=os.path.join(home, "config", "drive-index.duckdb"))
    os.environ.pop("PASEO_AGENT_ID", None)
    shutil.copy(os.path.join(FIXTURES, "drive-index.duckdb"), os.environ["IDLI_DRIVE_INDEX"])
    with open(os.path.join(home, "config", "drive-index-state.json"), "w") as f:
        json.dump({"phase": "done", "files": 1}, f)
    os.chdir(data)
    sys.path.insert(0, COWORK)
    import cowork_mcp  # noqa: E402  (loads sites google + files from cowork.sites)
    _patch(cowork_mcp, home, data)
    return cowork_mcp


def _drive():
    with open(os.path.join(FIXTURES, "drive.json")) as f:
        return json.load(f)


def _patch(mcp, home, data):
    from lib import browser, uiswitch
    from sites.files import tools as ft
    from sites.google import tools as g
    from lib import driveindex as di

    def no_browser(*a, **k):
        raise RuntimeError("no browser in the benchmark")
    browser.paseo = no_browser
    browser.tabs = lambda: []
    uiswitch.show_tab = lambda *a, **k: {"ok": True, "why": None}
    uiswitch.show_agent = lambda *a, **k: {"ok": True, "why": None}
    ft._show = lambda url, file: True
    ft._server = lambda: (8797, "bench")
    ft.claim_chat = lambda name: None
    ft.ensure_spare = lambda: None
    ft._show_mock = lambda rid, title: False
    g._preview = lambda f: None
    di.status = lambda: {"phase": "done"}
    extra = {}  # files added during the conversation (working copies): id -> path

    def drive_file(fid):
        d = _drive()
        f = next((x for x in d["files"] if x["id"] == fid), None)
        if f and f.get("path"):
            return os.path.join(FIXTURES, "drive", f["path"]), f["name"]
        if fid in extra:
            return extra[fid]
        return None, None

    def t_file_get(link, wait_seconds=45, open_after=True, goal=None):
        m = re.search(r"/d/([\w-]{20,})|[?&]id=([\w-]{20,})", link or "")
        fid = (m.group(1) or m.group(2)) if m else (link or "").strip()
        path, name = drive_file(fid)
        if not path:
            if not re.fullmatch(r"[\w-]{20,}", fid or ""):
                return {"error": "That doesn't look like a Google Sheets or Drive link. Use drive_search to find the file."}
            return {"error": "That file isn't a spreadsheet Idli can download (or it no longer exists)."}
        out_dir = os.path.join(data, "drive")
        os.makedirs(out_dir, exist_ok=True)
        title = re.sub(r"(?i)\.(xlsx|xls|csv)$", "", name)
        dest = os.path.join(out_dir, re.sub(r"[^\w .()-]+", "_", title).strip()[:80] + os.path.splitext(path)[1])
        shutil.copy2(path, dest)
        src = {}
        try:
            with open(dest + ".source.json") as f:
                src = json.load(f)
        except (OSError, ValueError):
            pass
        if src.get("id") != fid:
            src = {}
        src.update(id=fid, url=f"https://docs.google.com/spreadsheets/d/{fid}/edit")
        with open(dest + ".source.json", "w") as f:
            json.dump(src, f)
        rel = os.path.relpath(dest, data)
        if not open_after:
            return {"downloaded": True, "file": rel, "title": title}
        out = ft.t_file_open(rel, goal=goal)
        out["downloaded"] = True
        return out

    def t_working_copy(file, fresh=False):
        from lib import workcopy
        meta, e = ft.files().meta(file), ft.files().open(file)
        if not meta["known"]:
            return {"error": "Idli hasn't been taught this file yet.", "then": "Call teach_file with the user's request."}
        src = ft.files().source(file) or {}
        if not src.get("id"):
            return {"error": "I don't know where this file is in Drive.", "then": "Ask for the file's Google link and "
                    "call file_get with it, then working_copy."}
        if src.get("working_copy") and not fresh:
            wc = src["working_copy"]
            return {"exists": True, "working_copy": wc,
                    "say_to_user": f"You already have a working copy: {wc['name']} (opened in a tab). Fix the red cells "
                                   "there and tell me when you're ready.",
                    "then": "When they say they're ready, call working_copy_ready."}
        stem = os.path.splitext(os.path.basename(file))[0]
        name = f"{stem} - Idli working copy {time.strftime('%d %b %H%M')}.xlsx"
        out = os.path.join(home, "uploads", name)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        path = ft.files().resolve(file)
        if path.lower().endswith(".csv"):
            import pandas as pd
            x = path[:-4] + ".xlsx"
            pd.read_csv(path).to_excel(x, index=False, sheet_name="csv")
            path = x
        made = workcopy.build(path, e["skill"], e["problems"], out)
        fid = "wc" + str(abs(hash(name)))[:22].ljust(22, "0")
        extra[fid] = (out, name)
        src["working_copy"] = {"id": fid, "url": f"https://docs.google.com/spreadsheets/d/{fid}/edit", "name": name,
                               "folder": "My Drive", "made": time.strftime("%Y-%m-%d %H:%M"), "problems": made["cells"]}
        with open(ft.files().resolve(file) + ".source.json", "w") as f:
            json.dump(src, f)
        return {"uploaded": True, "working_copy": src["working_copy"],
                "say_to_user": f"I put \"{name}\" next to the original in My Drive and opened it in a tab. Red cells are "
                               "problems and turn white once fixed; each kind of problem has one comment on its first "
                               "cell (the number on each tab's name), and the last tab, Idli checks, lists them all. The "
                               "original is unchanged. Fix what you can, then tell me you're ready and I'll analyse the copy.",
                "then": "Write say_to_user, nothing else. Don't answer questions about the file until they say they're "
                        "ready (then call working_copy_ready) or ask you to go ahead with the original."}

    def _teach_send(request_id):
        rdir = os.path.join(os.environ["IDLI_TEACH_DIR"], request_id)
        with open(os.path.join(rdir, "request.json")) as f:
            req = json.load(f)
        title = ("Chart: " if req.get("chart") is not None else "Teach: ") + req["title"]
        with open(os.path.join(rdir, "teach_agent.json"), "w") as f:
            json.dump({"agent": "bench-teach"}, f)
        return {"started": True, "teach_chat": title}

    def t_drive_search(query, max_wait=8, **k):
        return {"files": [], "note": "live Drive search found nothing"}

    def t_file_peek(id, name=""):
        f = next((x for x in _drive()["files"] if x["id"] == id), None)
        if not f:
            return {"error": "No file with that id in Drive."}
        return {"opened": True, "say_to_user": f"Opened {f['name']} in a tab here (read only)."}

    ft.t_file_get = t_file_get
    g.t_file_peek = t_file_peek
    ft.t_working_copy = t_working_copy
    ft._teach_send = _teach_send
    g.t_drive_search = t_drive_search
    for name, fn in (("file_get", t_file_get), ("working_copy", t_working_copy), ("drive_search", t_drive_search),
                     ("file_peek", t_file_peek)):
        if name in mcp.TOOLS:
            mcp.TOOLS[name] = (fn,) + tuple(mcp.TOOLS[name][1:])
    for name in list(mcp.TOOLS):
        if name in DISALLOWED:
            del mcp.TOOLS[name]


def schemas(mcp, only=None):
    """OpenAI-style tool list: the MCP tools plus AskUserQuestion (Claude Code's card)."""
    out = []
    for n, (_, d, p, r) in mcp.TOOLS.items():
        if only and n not in only:
            continue
        out.append({"type": "function", "function": {"name": n, "description": d,
                                                     "parameters": {"type": "object", "properties": p, "required": r}}})
    out.append({"type": "function", "function": {
        "name": "AskUserQuestion",
        "description": "Ask the user one to four questions as a card with options to click (they can also type "
                       "'Other'). Use for choices; the answer comes back as the result.",
        "parameters": {"type": "object", "required": ["questions"], "properties": {"questions": {
            "type": "array", "items": {"type": "object", "required": ["question", "header", "options", "multiSelect"],
                                       "properties": {"question": {"type": "string"}, "header": {"type": "string"},
                                                      "multiSelect": {"type": "boolean"},
                                                      "options": {"type": "array", "items": {
                                                          "type": "object", "required": ["label", "description"],
                                                          "properties": {"label": {"type": "string"},
                                                                         "description": {"type": "string"}}}}}}}}}}})
    return out


def call(mcp, name, args):
    if name not in mcp.TOOLS:
        return {"error": f"unknown tool {name}"}, True
    if not isinstance(args, dict):
        return {"error": "arguments must be a JSON object"}, True
    return mcp.call(name, args)
