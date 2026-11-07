"""Files site: spreadsheets Idli has been *taught* (file skills), and asking to be taught new ones.

Idli never computes numbers itself. For a spreadsheet it calls file_open; a known file has a file
skill (built by Claude in the Teach workspace from a junk-data mock) with validations and taught
questions, run here with DuckDB. An unknown file, or a new kind of question, goes to teach_file /
teach_send. Originals are never changed: validations go into a separate "<name> - checked.xlsx".
"""
import json
import os
import shutil
import subprocess
import sys

from lib import filekit as fk
from sites.sheets import tools as sh

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_open = {}  # file -> {"skill", "table", "problems"}


def _skill_summary(skill):
    return {"name": skill.get("title") or skill["id"], "version": skill.get("version", 1),
            "what_it_knows": skill.get("summary", ""),
            "questions": [{"id": q["id"], "answers": q.get("ask", ""),
                           "params": {k: v.get("description", v.get("type", "")) + (" (optional)" if v.get("optional") else "")
                                      for k, v in (q.get("params") or {}).items()}}
                          for q in skill.get("questions", [])],
            "checks": len(skill.get("validations") or [])}


def _load(file):
    path = sh.resolve(file)
    sheets, _ = fk.raw_sheets(path)
    if not sheets:
        raise ValueError(f"'{file}' has no data.")
    main = fk.main_sheet(sheets)
    skill, score = fk.match(sheets[main])
    return path, sheets, main, skill, score


def t_file_open(file):
    path, sheets, main, skill, score = _load(file)
    df = sheets[main]
    if not skill:
        _open[file] = {"skill": None}
        return {"file": file, "known": False, "rows": len(df), "columns": list(df.columns)[:30],
                "tell_the_user": "Say: I haven't seen this file before. Rather than guess, I'd like you to teach me "
                                 "how to read it. I'll make a copy with fake data (same columns, no real values) "
                                 "and send it with your question to Claude in the Teach workspace. Ask if that's OK; "
                                 "if yes, call teach_file. Don't work out numbers from this file yourself."}
    table = fk.slug(skill["id"])
    fk.build_tables(sh._con, path, skill, table)
    sh._tables[table] = {"file": file, "sheet": main, "columns": {fk.slug(c): c for c in df.columns}}
    _open[file] = {"skill": skill, "table": table}
    return {"file": file, "known": True, "rows": len(df), **_skill_summary(skill),
            "next": "Call file_check(file) once in this chat. Then pick the question that fits what the user "
                    "asked and call file_answer with its parameters (ask the user if a value is unclear). If no "
                    "question fits, tell the user you haven't been taught this kind of question and offer "
                    "teach_file."}


def t_file_check(file):
    if file not in _open:
        t_file_open(file)
    skill = _open[file].get("skill")
    if not skill:
        return {"error": "Idli hasn't been taught this file yet. Offer teach_file."}
    out_dir = os.path.join(sh.data_dir(), "checked")
    problems, out, sheet = fk.check(sh.resolve(file), skill, out_dir)
    _open[file]["problems"] = len(problems)
    groups = {}
    for p in problems:
        g = groups.setdefault((p["column"], p["problem"]), {"column": p["column"], "problem": p["problem"],
                                                           "count": 0, "examples": []})
        g["count"] += 1
        if len(g["examples"]) < 4:
            g["examples"].append({"row": p["row"], "value": p["value"]})
    rel = os.path.relpath(out, sh.data_dir())
    return {"file": file, "problems": len(problems), "by_kind": list(groups.values())[:10], "checked_copy": rel,
            "tell_the_user": ("No problems found." if not problems else
                              f"List the problem kinds briefly (counts and a couple of row numbers). Say the "
                              f"checked copy at {rel} has the check formulas and the problem cells in red, and the "
                              "original is unchanged. Ask whether to carry on now or wait while they fix the "
                              "original.")}


def t_file_answer(file, question, params=None):
    if file not in _open or not _open[file].get("table"):
        r = t_file_open(file)
        if not r.get("known"):
            return {"error": "Idli hasn't been taught this file yet. Offer teach_file."}
    skill, table = _open[file]["skill"], _open[file]["table"]
    qs = {q["id"]: q for q in skill.get("questions", [])}
    q = qs.get(question)
    if not q:
        return {"error": f"No taught question '{question}'. Taught: {list(qs)}. If none fits, offer teach_file."}
    try:
        sql = fk.fill(q["sql"].replace("{{table}}", f'"{table}"'), params or {}, q.get("params"))
    except ValueError as e:
        return {"error": str(e), "hint": "Ask the user for the missing value, then call again."}
    df = sh._con.execute(sql).fetchdf()
    caveat = ""
    try:
        with open(sh.resolve(file) + ".hidden.json") as f:
            hidden = json.load(f)
        used = [c for c in hidden if fk.slug(c) in sql]
        if used:
            caveat = (f" Also say plainly: {', '.join(f'{c} ({hidden[c]} cells)' for c in used)} may be missing values, "
                      "because Google's sheet export hides text in number columns (like 'Rs. 300'); totals from those "
                      "columns may be too low until the cells hold plain numbers.")
    except (OSError, ValueError):
        pass
    return {"question": q.get("ask", question), "params": params or {}, "rows": sh.rows(df, 50),
            "row_count": int(len(df)), "unresolved_problems": _open[file].get("problems"),
            "tell_the_user": "Give these numbers exactly as returned (format them, never change or re-add them). "
                             "Mention the parameters used, e.g. the date range."
                             + (" Say the answer includes rows that failed checks." if _open[file].get("problems")
                                else "") + caveat}


def t_teach_file(file, question, share_labels=None):
    path = sh.resolve(file)
    req, mock, preview = fk.make_mock(path, question, caller_agent=os.environ.get("PASEO_AGENT_ID"),
                                      share_labels=share_labels or ())
    cols = {c: v["kind"] for c, v in req["columns"][req["main_sheet"]].items()}
    labels = {c: v for c, v in fk.label_columns(path).items() if c not in (req.get("real_labels") or [])}
    out = {"request_id": req["id"], "will_send": {"question": req["question"], "columns": cols,
                                                   "example_fake_rows": preview[req["main_sheet"]][:2],
                                                   "real_labels_sent_for": req.get("real_labels") or "none"},
           "updating": req["existing_skill"]}
    if labels and share_labels is None:
        out["could_share_labels"] = labels
        out["tell_the_user"] = ("Show what will be sent: the question and the column list, all values fake. Then show "
                                "could_share_labels and ask which columns' labels may be sent as they are (e.g. a "
                                "status like Approved/Pending helps Claude; names of people or places should stay "
                                "fake). Call teach_file again with share_labels=[...] (or [] for none), then "
                                "teach_send after they confirm.")
    else:
        out["tell_the_user"] = "Show what will be sent and ask them to confirm. If they agree, call teach_send(request_id)."
    return out


def _paseo():
    for p in (shutil.which("paseo"), os.path.expanduser("~/.local/bin/paseo"), "/usr/local/bin/paseo", "/usr/bin/paseo"):
        if p and os.path.exists(p):
            return p
    raise RuntimeError("The paseo command was not found on this computer.")


def t_teach_send(request_id):
    rdir = os.path.join(fk.TEACH_DIR, request_id)
    with open(os.path.join(rdir, "request.json")) as f:
        req = json.load(f)
    prompt = (f"Idli asked to be taught a file. The request is in teach/inbox/{request_id}/ (mock.xlsx with fake data "
              f"and a hidden _idli_teach sheet, plus request.json). Question: \"{req['question']}\". "
              "Use the teach-file skill.")
    paseo = _paseo()
    # Run the CLI as the user, not as this Idli agent: an agent-scoped CLI defaults to the caller's (private)
    # workspace and ignores --cwd. The Teach chat must run in the Teach folder, never in the private one.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PASEO_")}
    ws = subprocess.run([paseo, "workspace", "ls", "--json"], capture_output=True, text=True, timeout=60, env=env)
    try:
        wid = next(w["workspaceId"] for w in json.loads(ws.stdout) if os.path.realpath(w["cwd"]) == os.path.realpath(HERE))
    except (ValueError, StopIteration):
        return {"error": "No Teach workspace found (a Paseo workspace on the co-work plugin folder). Open one, then retry."}
    r = subprocess.run([paseo, "run", "--provider", "diy-claude", "--workspace", wid, "--mode", "auto",
                        "--title", f"Teach: {req['title']}", "--no-wait", "--json", prompt],
                       capture_output=True, text=True, timeout=90, env=env)
    if r.returncode:
        return {"error": f"Could not start the Teach chat: {(r.stderr or r.stdout)[-300:]}"}
    try:
        info = json.loads(r.stdout)
        agent, cwd = info.get("agentId"), info.get("cwd", "")
    except ValueError:
        agent, cwd = None, ""
    if not agent or os.path.realpath(cwd) != os.path.realpath(HERE):
        if agent:
            subprocess.run([paseo, "stop", agent], capture_output=True, timeout=60, env=env)
            subprocess.run([paseo, "archive", agent], capture_output=True, timeout=60, env=env)
        return {"error": f"The Teach chat did not start in the Teach folder (got '{cwd}'); stopped it. Nothing was sent."}
    if req.get("caller_agent"):
        subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "lib", "teachwatch.py"), rdir,
                          req["caller_agent"], paseo], start_new_session=True, env=env,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"started": True, "teach_chat": f"Teach: {req['title']}",
            "tell_the_user": "Say teaching has started in the 'Teach - Claude' workspace, in the chat called "
                             f"'Teach: {req['title']}'. Claude will ask a few questions about the columns there. "
                             "When it finishes, this chat gets a message and you will continue."}


FILE = {"file": {"type": "string", "description": "Path in the workspace folder, e.g. from gsheet_read's saved_csv "
                                                  "or sheet_list"}}
TOOLS = {
    "file_open": (t_file_open, "Open a spreadsheet (Excel or CSV in the workspace folder, e.g. a Google Sheet saved by "
                  "gsheet_read). Says whether Idli has been taught this file and which questions it can answer. "
                  "Always call this before answering anything about a spreadsheet.", FILE, ["file"]),
    "file_check": (t_file_check, "Run the taught checks on a known file (phones, emails, dates, amounts...). Writes a "
                   "separate '<name> - checked.xlsx' with formulas; never changes the original.", FILE, ["file"]),
    "file_answer": (t_file_answer, "Answer a taught question on a known file. The numbers come from the data, never "
                    "from you.", {**FILE, "question": {"type": "string", "description": "Question id from file_open"},
                                  "params": {"type": "object", "description": "Values for the question's params, "
                                             "e.g. {\"start\": \"2026-08-26\", \"end\": \"2026-10-26\"}"}},
                    ["file", "question"]),
    "teach_file": (t_teach_file, "Prepare a teaching request for a file Idli doesn't know (or a question it hasn't "
                   "been taught): a copy of the file with fake values and the user's question with names removed. "
                   "Shows what would be sent; nothing is sent yet.",
                   {**FILE, "question": {"type": "string", "description": "The user's question, in their words"},
                    "share_labels": {"type": "array", "items": {"type": "string"},
                                     "description": "Columns whose category labels the user agreed to send as they are"}},
                   ["file", "question"]),
    "teach_send": (t_teach_send, "After the user agrees, send the teaching request to Claude in the Teach workspace.",
                   {"request_id": {"type": "string"}}, ["request_id"]),
}


def whoami():
    return "local files"
