"""Google site plugin: Gmail, Drive and Docs as tools, through the user's workspace-browser tabs.

Gmail and Docs block browser_evaluate (Trusted Types), so they are read from snapshots; Drive
allows evaluate. Deliberately missing: sending email, deleting, editing documents.
"""
import json
import os
import re
import time
import urllib.parse

from lib.accounts import account
from lib.browser import NotSignedIn, evaluate, page_url, paseo, q, snapshot, tab_for, tabs

_last_search = {"tab": None}


def acct():
    """The Google account to use: the test account's email in tests, else '' (the signed-in default)."""
    return account("google", "")


def au(sep="?"):
    """authuser query parameter (Google redirects it to the right /u/N/); empty for the default account."""
    a = acct()
    return f"{sep}authuser={urllib.parse.quote(a, safe='')}" if a else ""


def gmail_base():
    return "https://mail.google.com/mail/" + (au() or "u/0/")


def drive_url(path=""):
    return "https://drive.google.com/drive/" + path + au("&" if "?" in path else "?")


def signed_in_email(snap):
    m = re.search(r'Google Account: [^"]*\(([^)\s]+@[^)\s]+)\)', snap)
    return m.group(1) if m else None


def require_signed_in(snap, what):
    url = page_url(snap)
    if "accounts.google.com" in url or "ServiceLogin" in url or "workspace.google.com" in url:
        raise NotSignedIn(f"{what}: not signed in (the tab shows the Google sign-in page).")


# ---------------------------------------------------------------- Gmail parsing
ROW = re.compile(r'^\s*- row "(.*)"\s*$')
REF = re.compile(r"\[(?:[^\]]*\s)?ref=(@e\d+)")


def parse_gmail_rows(snap):
    rows, cur = [], None
    for line in snap.splitlines():
        m = ROW.match(line)
        if m:
            cur = {"label": q(m.group(1)), "ref": None, "cells": []}
            rows.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("- link ") and cur["ref"] is None and REF.search(s):
            cur["ref"] = REF.search(s).group(1)
        t = re.match(r'- text: "(.*)"$', s)
        if t:
            cur["cells"].append(q(t.group(1)))
    out = []
    for r in rows:
        if not r["ref"]:
            continue
        label = r["label"]
        unread = label.startswith("unread, ")
        if unread:
            label = label[len("unread, "):]
        sender = r["cells"][0] if r["cells"] else ""
        date = r["cells"][-1] if r["cells"] else ""
        rest = label[len(sender) + 2:] if label.startswith(sender + ", ") else label
        subject, _, snippet = rest.partition(", " + date + ", ")
        out.append({"n": len(out) + 1, "unread": unread, "from": sender, "subject": subject,
                    "date": date, "snippet": snippet[:110], "_ref": r["ref"]})
    return out


def parse_gmail_thread(snap):
    lines = snap.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "- main")
    except StopIteration:
        return None
    subject, msgs, cur = "", [], None
    skip = {"to", "me", "Show details", "Reply", "Forward", "Add reaction"}
    for line in lines[start + 1:]:
        s = line.strip()
        m = re.match(r'- heading "(.*)" \[level=(\d)\]', s)
        if m and m.group(2) == "2" and not subject:
            subject = q(m.group(1))
            continue
        if m and m.group(2) == "3":
            cur = {"from": q(m.group(1)), "date": "", "text": []}
            msgs.append(cur)
            continue
        if cur is None:
            continue
        g = re.match(r'- gridcell "(.*)"', s)
        if g and not cur["date"] and re.search(r"\d", g.group(1)):
            cur["date"] = q(g.group(1))
            continue
        t = re.match(r'- (?:text: |link )"(.*?)"', s)
        if t:
            val = q(t.group(1))
            if val not in skip and val != cur["from"]:
                cur["text"].append(val)
    for m in msgs:
        body = re.sub(r"\s+", " ", " ".join(m.pop("text"))).strip()
        m["body"] = body[:3500] + (" …[truncated]" if len(body) > 3500 else "")
    return {"subject": subject, "messages": msgs}


# ---------------------------------------------------------------- Drive / Docs
DRIVE_JS = ('() => { const seen = {}; const out = [];'
            ' for (const e of document.querySelectorAll("[data-id]")) {'
            '  const id = e.getAttribute("data-id"); const t = (e.innerText || "").trim();'
            '  if (!t || id.length < 20 || seen[id]) continue; seen[id] = 1;'
            '  const lines = t.split("\\n").map(s => s.trim()).filter(Boolean);'
            '  const label = e.getAttribute("aria-label") || "";'
            '  const kind = label.startsWith(lines[0]) ? label.slice(lines[0].length).trim() : "";'
            '  out.push({id, name: lines[0], kind}); }'
            ' return JSON.stringify(out.slice(0, 25)); }')


def kind_of(f):
    """Drive's own label, e.g. 'Google Sheets', 'Google Docs', 'PDF', 'Shared folder'."""
    k = re.split(r" (?:Shared|More info)", f.get("kind") or "")[0].strip()
    return {"Google Sheets": "Google Sheet", "Google Docs": "Google Doc", "Google Slides": "Google Slides"}.get(k, k)


def doc_text(tab, doc_id):
    paseo("browser_navigate", browserId=tab,
          url=f"https://docs.google.com/document/d/{doc_id}/mobilebasic" + au())
    snap = snapshot(tab, lambda s: s.count("- text:") > 2 or "accounts.google.com" in s)
    require_signed_in(snap, "Google Docs")
    title = (re.search(r"^Title: (.*)$", snap, re.M) or [None, ""])[1]
    paras = [q(m.group(1)) for m in re.finditer(r'^\s*- text: "(.*)"$', snap, re.M)]
    if paras and paras[0] == title:
        paras = paras[1:]
    paseo("browser_navigate", browserId=tab,
          url=f"https://docs.google.com/document/d/{doc_id}/edit" + au())
    return title, paras


# ---------------------------------------------------------------- tools
def t_list_tabs():
    return [{"title": t["title"], "url": t["url"], "active": t["active"]} for t in tabs()]


def t_gmail_search(query, max_results=10):
    tab = tab_for("mail.google.com", open_url=gmail_base())
    paseo("browser_navigate", browserId=tab, url=gmail_base() + "#search/" + urllib.parse.quote_plus(query))
    snap = snapshot(tab, lambda s: ("- row \"" in s and "link \"" in s) or "No messages matched" in s
                    or "accounts.google.com" in s)
    require_signed_in(snap, "Gmail")
    rows = parse_gmail_rows(snap)
    _last_search["tab"] = tab
    return {"query": query, "results": [{k: v for k, v in r.items() if k != "_ref"} for r in rows[:max_results]],
            "note": "Use gmail_open with n to read one." if rows else "No messages matched."}


def t_gmail_open(n):
    tab = _last_search["tab"] or tab_for("mail.google.com", open_url=gmail_base())
    rows = parse_gmail_rows(snapshot(tab, lambda s: "- row \"" in s))
    if not 1 <= n <= len(rows):
        return {"error": f"No result {n}; the current list has {len(rows)}. Run gmail_search again."}
    paseo("browser_click", browserId=tab, ref=rows[n - 1]["_ref"])
    thread = parse_gmail_thread(snapshot(tab, lambda s: "- main" in s and "[level=3]" in s))
    return thread or {"error": "Could not read the email."}


def t_gmail_read_open_email():
    tab = tab_for("mail.google.com", open_url=gmail_base())
    thread = parse_gmail_thread(snapshot(tab, lambda s: "- main" in s))
    return thread if thread and thread["messages"] else {"error": "No email is open in the Gmail tab."}


def t_gmail_draft_reply(text):
    tab = tab_for("mail.google.com", open_url=gmail_base())
    snap = snapshot(tab)
    refs = re.findall(r'- button "Reply" \[(?:[^\]]*\s)?ref=(@e\d+)', snap)
    if not refs:
        return {"error": "Open the email to reply to first (gmail_open or gmail_read_open_email)."}
    paseo("browser_click", browserId=tab, ref=refs[-1])
    box = None
    for _ in range(8):
        time.sleep(1)
        m = re.search(r'- textbox "Message Body"[^\n]*ref=(@e\d+)', snapshot(tab))
        if m:
            box = m.group(1)
            break
    if not box:
        return {"error": "The reply box did not open."}
    paseo("browser_type", browserId=tab, ref=box, text=text)
    return {"status": "Draft written in the Gmail tab and NOT sent. Gmail saves it to Drafts; "
                      "the user reviews and sends it themselves."}


def t_drive_search(query, max_wait=8):
    tab = tab_for("drive.google.com", "docs.google.com", open_url=drive_url())
    paseo("browser_navigate", browserId=tab,
          url=drive_url("search?q=" + urllib.parse.quote_plus(query)))
    files = []
    for _ in range(max(1, int(max_wait))):
        time.sleep(1)
        snap_url = next((t["url"] for t in tabs() if t["id"] == tab), "")
        if "accounts.google.com" in snap_url:
            raise NotSignedIn("Google Drive: not signed in (the tab shows the Google sign-in page).")
        files = evaluate(tab, DRIVE_JS) or []
        if files:
            break
    return {"query": query,
            "files": [{"n": i + 1, "id": f["id"], "name": f["name"], "type": kind_of(f)} for i, f in enumerate(files)],
            "note": "doc_read reads Google Docs; gsheet_read reads Google Sheets."}


def t_doc_read(doc_id=None):
    tab = tab_for("docs.google.com", "drive.google.com", open_url=drive_url())
    if not doc_id:
        cur = next((t for t in tabs() if t["id"] == tab), {})
        m = re.search(r"/document/(?:u/[^/]+/)?d/([\w-]{20,})", cur.get("url", ""))
        if not m:
            return {"error": "No doc id given and no Google Doc is open. Use drive_search first."}
        doc_id = m.group(1)
    title, paras = doc_text(tab, doc_id)
    if not paras or title in ("Page not found", "Google Docs: Sign-in"):
        return {"error": f"'{doc_id}' did not open as a Google Doc (it may be a Sheet, Slides or other file). "
                         "No tool here reads that kind of file."}
    text = "\n".join(paras)
    return {"title": title, "doc_id": doc_id, "paragraphs": len(paras),
            "text": text[:12000] + ("\n…[truncated]" if len(text) > 12000 else ""),
            "note": "Read-only. Suggest changes in chat; never edit the doc."}


# ---------------------------------------------------------------- Google Sheets
# The Sheets grid is a canvas and docs.google.com blocks browser_evaluate, so cells come from the
# Visualization API's HTML table (gviz/tq?tqx=out:html), read from a snapshot, a page at a time.
# Tab names come from the "Sheet tab bar" in the edit page's snapshot. A CSV copy goes into the
# workspace folder so the sheets site (sheet_profile / sheet_query) can do the maths.
SHEET_ID = re.compile(r"/spreadsheets/(?:u/[^/]+/)?d/([\w-]{20,})")
TOKEN = re.compile(r'^\s*- (row|cell)\b|- text: "((?:[^"\\]|\\.)*)"', re.M | re.S)
PAGE = 400
MAX_ROWS = 4000
NUM = re.compile(r"^\(?-?[$€£₹¥]?\s?-?[\d,]*\.?\d+\)?%?$")


def data_dir():
    return os.environ.get("COWORK_DATA_DIR") or os.getcwd()


def sheets_url(sheet_id, path):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/{path}" + au("&" if "?" in path else "?")


def page_problem(snap):
    title = (re.search(r"^Title: (.*)$", snap, re.M) or [None, ""])[1]
    if title == "Page not found" or "file you have requested does not exist" in snap:
        return "not found (check the id, or the account may not have access)"
    if "You need access" in snap or "Request access" in snap:
        return "no access with this account"
    return None


def parse_gviz_table(snap):
    rows, cur = [], None
    for m in TOKEN.finditer(snap):
        if m.group(1) == "row":
            cur = []
            rows.append(cur)
        elif m.group(1) == "cell" and cur is not None:
            cur.append("")
        elif m.group(2) is not None and cur:
            val = q(m.group(2)).replace("\\n", "\n")
            cur[-1] = (cur[-1] + " " + val).strip() if cur[-1] else val
    return rows


def sheet_tabs(tab, sheet_id):
    paseo("browser_navigate", browserId=tab, url=sheets_url(sheet_id, "edit"))
    snap = snapshot(tab, lambda s: "Sheet tab bar" in s or page_problem(s) or "accounts.google.com" in page_url(s),
                    tries=12)
    require_signed_in(snap, "Google Sheets")
    if page_problem(snap):
        raise ValueError(f"Google Sheet '{sheet_id}' {page_problem(snap)}.")
    title = (re.search(r"^Title: (.*?)(?: - Google Sheets)?$", snap, re.M) or [None, ""])[1]
    bar = snap.split('navigation "Sheet tab bar"', 1)[-1] if "Sheet tab bar" in snap else ""
    names = []
    for m in re.finditer(r'- button "[^"\n]*"[^\n]*\n\s*- text: "((?:[^"\\]|\\.)*)"', bar):
        n = q(m.group(1))
        if n not in names:
            names.append(n)
    return title, names


def clean_numbers(header, body):
    """Formatted numbers ('1,234', '$5.20', '(30)', '12%') -> plain numbers, per column, when the
    column is mostly numbers. Returns the names of columns that held percentages."""
    pct = []
    for j in range(len(header)):
        vals = [r[j] for r in body if j < len(r) and r[j] not in ("", "-")]
        if not vals or sum(bool(NUM.match(v)) for v in vals) < 0.9 * len(vals):
            continue
        if any(v.endswith("%") for v in vals):
            pct.append(header[j] or f"column {j + 1}")
        for r in body:
            v = r[j] if j < len(r) else ""
            if NUM.match(v):
                neg = v.startswith("(") and v.endswith(")")
                v = re.sub(r"[()$€£₹¥,%\s]", "", v)
                r[j] = ("-" + v.lstrip("-")) if neg else v
    return pct


def t_gsheet_read(sheet_id=None, tab=None, max_rows=15):
    btab = tab_for("docs.google.com", "drive.google.com", open_url=drive_url())
    if not sheet_id:
        cur = next((t for t in tabs() if t["id"] == btab), {})
        m = SHEET_ID.search(cur.get("url", ""))
        if not m:
            return {"error": "No sheet id given and no Google Sheet is open. Use drive_search to find its id."}
        sheet_id = m.group(1)
    sheet_id = (SHEET_ID.search(sheet_id) or [None, sheet_id])[1].strip()  # accept a full URL too
    try:
        title, names = sheet_tabs(btab, sheet_id)
    except ValueError as e:
        return {"error": f"{e} If drive_search says it is not a 'Google Sheet' (e.g. an uploaded .xlsx), "
                         "this tool cannot read it."}
    if tab:
        match = [n for n in names if n.lower() == tab.lower()]
        if names and not match:
            return {"error": f"No tab '{tab}'. Tabs: {names}"}
        tab = match[0] if match else tab
    else:
        tab = names[0] if names else None

    rows = []
    offset = 0
    while offset < MAX_ROWS:
        path = "gviz/tq?tqx=out:html&tq=" + urllib.parse.quote(f"select * limit {PAGE} offset {offset}")
        if tab:
            path += "&sheet=" + urllib.parse.quote(tab)
        paseo("browser_navigate", browserId=btab, url=sheets_url(sheet_id, path))
        snap = snapshot(btab, lambda s: "- table" in s or page_problem(s) or "accounts.google.com" in page_url(s)
                        or "Error" in s[:400])
        require_signed_in(snap, "Google Sheets")
        if page_problem(snap):
            return {"error": f"Google Sheet '{sheet_id}' {page_problem(snap)}."}
        page = parse_gviz_table(snap)
        if not page:
            break
        labels, data = page[0], page[1:]  # gviz always emits a label row first (blank if no header found)
        # Paseo cuts long snapshots (~20k chars) and ends them with "Snapshot truncated.": the last row
        # may be partial, so drop it and read on from there instead of taking a short page as the end.
        truncated = "Snapshot truncated" in snap[-200:]
        if truncated and data:
            data = data[:-1]
        if offset == 0:
            rows.append(labels)
        rows.extend(data)
        if not data or (not truncated and len(data) < PAGE):
            break
        offset += len(data)
    paseo("browser_navigate", browserId=btab, url=sheets_url(sheet_id, "edit"))  # leave the user on the sheet

    if len(rows) > 1 and not any(rows[0]):
        rows = rows[1:]  # gviz found no header row; the data's own first row stays
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return {"error": f"Tab '{tab}' looks empty."}
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    used = [j for j in range(width) if any(r[j] for r in rows)]
    rows = [[r[j] for j in used] for r in rows]
    header, body = [h or f"column_{j + 1}" for j, h in enumerate(rows[0])], rows[1:]
    hidden = {}
    for j, h in enumerate(header):  # Google types a mostly-numeric column as numbers and blanks any text in it
        vals = [r[j] for r in body]
        nums = sum(1 for v in vals if NUM.match(v.replace(" ", "")))
        blanks = sum(1 for v in vals if not v.strip())
        if blanks and nums >= 0.7 * max(1, len(vals) - blanks):
            hidden[h] = blanks
    pct = clean_numbers(header, body)

    import csv
    out_dir = os.path.join(data_dir(), "google_sheets")
    os.makedirs(out_dir, exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "_", (title or sheet_id).lower())[:50].strip("_") or "sheet"
    if tab and len(names) > 1:
        name += "__" + re.sub(r"[^a-z0-9]+", "_", tab.lower())[:30].strip("_")
    path = os.path.join(out_dir, name + ".csv")
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows([header] + body)
    rel = os.path.relpath(path, data_dir())
    side = path + ".hidden.json"  # travels with the copy so later answers repeat the caveat
    if hidden:
        with open(side, "w") as f:
            json.dump(hidden, f)
    elif os.path.exists(side):
        os.remove(side)

    shown = body[:max(0, min(max_rows, 50))]
    preview = [dict(zip(header, r)) for r in shown]
    while preview and len(json.dumps(preview, ensure_ascii=False)) > 2200:
        preview.pop()
    out = {"title": title, "sheet_id": sheet_id, "tab": tab, "tabs": names, "rows": len(body),
           "columns": header, "first_rows": preview, "saved_csv": rel,
           "note": (f"Showing {len(preview)} of {len(body)} rows. " if len(preview) < len(body) else "All rows shown. ")
           + f"Next call file_open(file='{rel}'): never total, average or count it yourself. "
           "Numbers had their formatting ($ , %) removed."
           + (f" Columns {pct} were percentages (12% is stored as 12)." if pct else "")
           + (" Use tab=... to read another tab." if len(names) > 1 else "")
           + " Read-only: never edit the sheet."}
    if hidden:
        out["warning"] = (f"Blank cells in number columns {hidden} may not be blank: Google's sheet export hides text in "
                          "a number column (e.g. 'Rs. 300', 'pending'). Tell the user totals may be missing those "
                          "values until the cells hold plain numbers.")
    if len(body) >= MAX_ROWS - 1:
        out["note"] += f" Stopped at {MAX_ROWS} rows."
    return out


def whoami():
    """For tests: the Google account the tabs are signed in as (raises NotSignedIn)."""
    tab = tab_for("mail.google.com", open_url=gmail_base())
    paseo("browser_navigate", browserId=tab, url=gmail_base() + "#inbox")
    snap = snapshot(tab, lambda s: signed_in_email(s) or "accounts.google.com" in s)
    require_signed_in(snap, "Gmail")
    email = signed_in_email(snap)
    if not email:
        raise NotSignedIn("Gmail: could not see which account is signed in.")
    return email


# ---------------------------------------------------------------- Drive index (lib/driveindex.py)
def t_drive_index():
    from lib import driveindex as di
    st = di.status()
    if st.get("phase") in ("starting", "listing", "reading", "summarising"):
        return {"started": False, "running": True, "say_to_user": "I'm already indexing your Drive: " + di.progress_line(st)}
    if os.path.exists(os.path.splitext(di.DB)[0] + ".dryrun"):  # test switch: time the chat without a rebuild
        return {"started": True, "dry_run": True, "say_to_user": "Indexing your Drive now (test run).",
                "then": "Write say_to_user. " + SWITCH_CARD + "Then call drive_index_wait."}
    import subprocess
    import sys
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log = os.path.join(os.path.dirname(di.STATE), "drive-index.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    env = dict(os.environ, IDLI_NOTIFY_AGENT=os.environ.get("PASEO_AGENT_ID", ""))
    subprocess.Popen([sys.executable, "-I", os.path.join(here, "lib", "driveindex.py"), "build"], env=env,
                     start_new_session=True, stdin=subprocess.DEVNULL, stdout=open(log, "a"), stderr=subprocess.STDOUT)
    shown = False
    try:  # a live progress page in a tab: the chat can't update itself while the index builds
        from sites.files import tools as ft
        port, token = ft._server()
        # *.localhost reaches this computer in Chromium, and the tab is labelled "drive-index.localhost" even
        # before it loads (background tabs load when clicked), instead of a bare 127.0.0.1
        url = f"http://drive-index.localhost:{port}/index?t={token}"
        old = next((t for t in tabs() if "drive-index.localhost" in t["url"]), None)
        if old:  # "rebuild index": reuse the tab
            paseo("browser_navigate", browserId=old["id"], url=url)
        else:
            paseo("browser_new_tab", url=url)
        shown = True
    except Exception:
        pass
    return {"started": True,
            "say_to_user": "Indexing your Drive now. It stays on this computer and takes 1 to 5 minutes."
                           + (" Watch it in the drive-index tab at the top." if shown else "")
                           + " I'll say here when it's done.",
            "then": "In this same reply: write say_to_user. " + (SWITCH_CARD if shown else "") + "Then call "
                    "drive_index_wait, and keep calling it (no need to write anything in between) until it says done; "
                    "then write its finish message."}


SWITCH_CARD = ('Then call AskUserQuestion with one question: header "Progress", question "Indexing has started. Switch '
               'to the progress tab to watch it?", options "Yes, show me" and "No, stay here". If they pick yes, call '
               'show_progress. ')


PEEK_STATE = os.path.expanduser("~/idli-insights/config/peek-tabs.json")


def _peek_url(fid, kind):
    if kind == "Google Sheets":
        return f"https://docs.google.com/spreadsheets/d/{fid}/preview"
    if kind == "Google Docs":
        return f"https://docs.google.com/document/d/{fid}/preview"
    if kind == "Google Slides":
        return f"https://docs.google.com/presentation/d/{fid}/preview"
    return f"https://drive.google.com/file/d/{fid}/view"


def t_file_peek(id, name=""):
    """After the person said yes on the card: open the file read-only in a tab in this workspace and bring it
    forward. One peek tab per workspace, reused for the next file."""
    from lib import driveindex as di
    from lib import uiswitch
    kind, title = "", name
    try:
        row = di._read("SELECT name, kind FROM files WHERE id = ?", [id]) if os.path.exists(di.DB) else []
        if row:
            title, kind = title or row[0][0], row[0][1]
    except Exception:
        pass
    url = _peek_url(id, kind)
    ws = os.environ.get("PASEO_WORKSPACE_ID") or os.getcwd()
    try:
        with open(PEEK_STATE) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    open_ids = {t["id"] for t in tabs()}
    tab = state.get(ws)
    if tab in open_ids:
        paseo("browser_navigate", browserId=tab, url=url)
    else:
        out = paseo("browser_new_tab", url=url)
        m = re.search(r"browserId=(\S+)", out) or re.search(r'"browserId"\s*:\s*"([^"]+)"', out)
        tab = m.group(1) if m else None
        state[ws] = tab
        os.makedirs(os.path.dirname(PEEK_STATE), exist_ok=True)
        with open(PEEK_STATE, "w") as f:
            json.dump(state, f)
    time.sleep(1.5)
    host = urllib.parse.urlparse(url).hostname
    got = uiswitch.show_tab([f"{title}*" if title else host, host])
    return {"opened": True, "shown": got["ok"], "say_to_user": (
        f"It's open in the tab at the top (read only)." if got["ok"]
        else f"It's open in a new tab at the top ({host}); click it to take a look (read only).")}


def t_show_progress():
    """After the person said yes on the card: bring the drive-index progress tab to the front."""
    from lib import uiswitch
    got = uiswitch.show_tab("drive-index.localhost")
    if got["ok"]:
        return {"shown": True}
    return {"shown": False, "say_to_user": "Click the drive-index tab at the top to watch it."}


def t_drive_index_status():
    from lib import driveindex as di
    st = di.status()
    if st.get("phase") == "done":
        return {"status": st, "done": True, "finish": di.progress_line(st) + " " + NEXT_STEPS,
                "say_to_user": di.progress_line(st)}
    return {"status": st, "say_to_user": di.progress_line(st), "running": st.get("phase") in ("starting", "listing", "reading", "summarising")}
    words = {"none": "Drive hasn't been indexed yet.", "listing": f"Listing files: {st.get('files', 0)} so far.",
             "reading": f"Reading inside Sheets and Docs ({st.get('peeked', 0)} done).",
             "summarising": f"Summarising: {st.get('summarised', 0)} of {st.get('files', 0)} files. Search works already.",
             "done": f"Done: {st.get('files', 0)} files indexed at {st.get('finished', '')}.",
             "failed": f"Indexing failed: {st.get('error')}", "stopped": "Indexing stopped before it finished."}
    return {"status": st, "say_to_user": words.get(st.get("phase"), str(st.get("phase")))}


NEXT_STEPS = ("Next: go to Idli in the left sidebar and ask about any file, for example \"find the volunteer "
              "register\" or \"how much did we disburse last quarter\". To refresh this later, come back here and "
              "say \"rebuild index\".")


def t_drive_index_wait(seconds=20):
    """Wait (up to `seconds`) for the Drive index to make progress, then say where it is."""
    from lib import driveindex as di
    t0, start = time.time(), di.status()
    key = lambda st: (st.get("phase"), st.get("files"), st.get("peeked"), st.get("summarised"))
    st = start
    while time.time() - t0 < max(5, min(int(seconds or 20), 60)):
        time.sleep(2)
        st = di.status()
        if st.get("phase") in ("done", "failed", "stopped", "none"):
            break
        if st.get("phase") != start.get("phase") and time.time() - t0 > 6:
            break
    done = st.get("phase") in ("done", "failed", "stopped", "none")
    out = {"done": done, "progress_line": di.progress_line(st)}
    if st.get("phase") == "done":
        out["finish"] = di.progress_line(st) + " " + NEXT_STEPS
        out["then"] = "Write `finish` to the user, as is. Stop calling drive_index_wait."
    elif done:
        out["then"] = "Tell the user, and offer to try again (say \"rebuild index\")."
    else:
        out["then"] = "Call drive_index_wait again (nothing to write yet). Don't end your turn before done."
    return out


def t_drive_find(query):
    from lib import driveindex as di
    t0 = time.time()
    r = di.search(query)
    r["ms"] = int((time.time() - t0) * 1000)
    if r["status"] == "no_index":
        r["say_to_user"] = ("I haven't indexed your Drive yet, so finding files is slow. Can I take 1 to 5 minutes to "
                            "index it? It stays on this computer.")
        r["then"] = "If they agree, call drive_index. If not, use drive_search."
        return r
    if r["status"] in ("none", "choose") and (r["status"] == "none" or r["results"][0]["score"] < 0.6):
        # Drive's own search reads the full text of every file (the index has names, folders, dates and first
        # rows). Drive matches all words, so try the two most distinctive words one at a time, briefly, once.
        from lib.driveindex import KIND_WORDS, STOP, _tokens
        dates = {"january", "february", "march", "april", "june", "july", "august", "september", "october", "november",
                 "december", "last", "this", "month", "year", "week"}
        cand = {t for t in _tokens(query) if t not in STOP and t not in KIND_WORDS and t not in dates
                and len(t) >= 4 and not t.isdigit()}
        rare = di.rarity(cand)
        words = sorted(cand, key=lambda w: (rare[w], -len(w)))[:3]  # rarest in this Drive first
        per, missed = {}, []
        for w in words:
            try:
                live = t_drive_search(w, max_wait=4).get("files", [])
            except Exception:
                live = []
            if not live:
                missed.append(w)
                continue
            per[w] = live
            if len(live) <= 3:  # a specific word: stop here
                break
        best = min(per, key=lambda w: len(per[w])) if per else None  # the word that matched the fewest files
        hits = [(best, f) for f in per[best][:4]] if best and len(per[best]) <= 3 else []
        common = {w: len(v) for w, v in per.items() if len(v) > 3}
        if hits:
            seen, res = set(), []
            for w, f in hits:
                if f["id"] not in seen:
                    seen.add(f["id"])
                    res.append({"id": f["id"], "name": f["name"], "kind": f["type"], "folder": f"(contains '{w}')",
                                "score": None})
            r.update(status="choose", results=res[:5], drive_search={"matched": sorted({w for w, _ in hits}),
                                                                     "no_file_mentions": missed})
            r["say_to_user"] = (("No file mentions " + ", ".join(f"'{m}'" for m in missed) + ". " if missed else "")
                                + "Ask whether it's one of these (the word each contains is in 'folder'), in one short "
                                  "message.")
            r["then"] = "Don't search again unless they give new words."
            r["ms"] = int((time.time() - t0) * 1000)
            return r
        r["drive_search"] = {"no_file_mentions": missed, "in_many_files": common}
        r["say_to_user"] = (("No file in Drive mentions " + ", ".join(f"'{m}'" for m in missed) + ". " if missed else "")
                            + ("".join(f"'{w}' is in many files. " for w in common))
                            + "Ask for another word from the file's name, its folder, or something written in it "
                              "(a place, a person, a species, a project).")
        r["then"] = "Don't keep searching until they answer."
        r["ms"] = int((time.time() - t0) * 1000)
        r["status"] = "none"
        r["results"] = []
        return r
    if r["status"] == "found":
        best = r["results"][0]
        r["then"] = (f"Tell the user you found '{best['name']}' ({best['kind']}, in {best['folder']}). For a spreadsheet, "
                     f"call file_get with link '{best['id']}' next.")
    elif r["status"] == "choose":
        r["say_to_user"] = "Ask which one they mean, listing these (name, kind, folder) in one short message."
        r["then"] = "Don't search again unless they give new words."
    else:
        r["say_to_user"] = ("Say nothing in the index matches, and ask for another word from the file's name, its "
                            "folder, or what's in it.")
        r["then"] = "Don't keep searching. If the index might be old, offer drive_index to refresh it."
    return r


TOOLS = {
    "drive_find": (t_drive_find, "Find a file in the user's Drive from their words, using Idli's local index (fast). "
                   "Use this first to find any Drive file. Says found / choose / none.",
                   {"query": {"type": "string", "description": "The user's words for the file"}}, ["query"]),
    "drive_index": (t_drive_index, "Start indexing the user's Drive in the background (1-5 minutes, stays on this "
                    "computer). Only after the user agrees.", {}, []),
    "file_peek": (t_file_peek, "Open a Drive file read-only in a tab in this workspace and bring that tab forward, "
                  "so the user can take a quick look. Only after the user said yes on the card. Nothing is downloaded.",
                  {"id": {"type": "string", "description": "The file id from drive_find"},
                   "name": {"type": "string", "description": "The file name from drive_find"}}, ["id"]),
    "show_progress": (t_show_progress, "Bring the drive-index progress tab to the front. Only after the user said "
                      "yes on the card.", {}, []),
    "drive_index_status": (t_drive_index_status, "How far the Drive index has got.", {}, []),
    "drive_index_wait": (t_drive_index_wait, "Wait up to ~20 s for the Drive index to progress; returns a one-line "
                         "progress_line to show the user, and done/finish at the end.",
                         {"seconds": {"type": "integer", "description": "How long to wait, default 20"}}, []),
    "list_tabs": (t_list_tabs, "List the browser tabs the user has open in Paseo (title, url, which is active).", {}, []),
    "gmail_search": (t_gmail_search, "Search the user's Gmail (Gmail search syntax works, e.g. from:aws "
                     "newer_than:2m payment). Shows the results in the user's Gmail tab and returns a short list.",
                     {"query": {"type": "string"}, "max_results": {"type": "integer"}}, ["query"]),
    "gmail_open": (t_gmail_open, "Open result n from the last gmail_search and return the email text.",
                   {"n": {"type": "integer"}}, ["n"]),
    "gmail_read_open_email": (t_gmail_read_open_email, "Read the email the user currently has open in Gmail.", {}, []),
    "gmail_draft_reply": (t_gmail_draft_reply, "Write a reply to the open email as a DRAFT in the user's Gmail "
                          "tab. It is never sent; the user reviews it.", {"text": {"type": "string"}}, ["text"]),
    "drive_search": (t_drive_search, "Live Google Drive search (slow). Only when drive_find has no index or the user "
                     "asks to search Drive directly.",
                     {"query": {"type": "string"}}, ["query"]),
    "doc_read": (t_doc_read, "Read the text of a Google Doc (by id from drive_search, or the doc open in the "
                 "user's tab when no id is given). Read-only. Google Docs only.", {"doc_id": {"type": "string"}}, []),
    "gsheet_read": (t_gsheet_read, "Read the cells of a Google Sheet through Google's quick export (id from drive_search, or "
                    "the sheet open in the user's tab when no id is given). Prefer file_get, which downloads the real "
                    "file; the quick export hides text in number columns. Returns the tab names, columns and first rows, and saves the "
                    "whole tab as a CSV in the workspace folder for sheet_profile / sheet_query. Read-only.",
                    {"sheet_id": {"type": "string"}, "tab": {"type": "string", "description": "Tab name; default "
                     "the first tab"}, "max_rows": {"type": "integer", "description": "Rows to show (default 15)"}},
                    []),
}
