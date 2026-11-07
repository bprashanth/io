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


def t_drive_search(query):
    tab = tab_for("drive.google.com", "docs.google.com", open_url=drive_url())
    paseo("browser_navigate", browserId=tab,
          url=drive_url("search?q=" + urllib.parse.quote_plus(query)))
    files = []
    for _ in range(8):
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
    for offset in range(0, MAX_ROWS, PAGE):
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
        if offset == 0:
            rows.append(labels)
        rows.extend(data)
        if len(data) < PAGE:
            break
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

    shown = body[:max(0, min(max_rows, 50))]
    preview = [dict(zip(header, r)) for r in shown]
    while preview and len(json.dumps(preview, ensure_ascii=False)) > 2200:
        preview.pop()
    out = {"title": title, "sheet_id": sheet_id, "tab": tab, "tabs": names, "rows": len(body),
           "columns": header, "first_rows": preview, "saved_csv": rel,
           "note": (f"Showing {len(preview)} of {len(body)} rows. " if len(preview) < len(body) else "All rows shown. ")
           + f"For totals, averages, sorting or filtering call sheet_profile(file='{rel}') then sheet_query. "
           "Numbers had their formatting ($ , %) removed."
           + (f" Columns {pct} were percentages (12% is stored as 12)." if pct else "")
           + (" Use tab=... to read another tab." if len(names) > 1 else "")
           + " Read-only: never edit the sheet."}
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


TOOLS = {
    "list_tabs": (t_list_tabs, "List the browser tabs the user has open in Paseo (title, url, which is active).", {}, []),
    "gmail_search": (t_gmail_search, "Search the user's Gmail (Gmail search syntax works, e.g. from:aws "
                     "newer_than:2m payment). Shows the results in the user's Gmail tab and returns a short list.",
                     {"query": {"type": "string"}, "max_results": {"type": "integer"}}, ["query"]),
    "gmail_open": (t_gmail_open, "Open result n from the last gmail_search and return the email text.",
                   {"n": {"type": "integer"}}, ["n"]),
    "gmail_read_open_email": (t_gmail_read_open_email, "Read the email the user currently has open in Gmail.", {}, []),
    "gmail_draft_reply": (t_gmail_draft_reply, "Write a reply to the open email as a DRAFT in the user's Gmail "
                          "tab. It is never sent; the user reviews it.", {"text": {"type": "string"}}, ["text"]),
    "drive_search": (t_drive_search, "Search the user's Google Drive by name or content; returns files with ids and types.",
                     {"query": {"type": "string"}}, ["query"]),
    "doc_read": (t_doc_read, "Read the text of a Google Doc (by id from drive_search, or the doc open in the "
                 "user's tab when no id is given). Read-only. Google Docs only.", {"doc_id": {"type": "string"}}, []),
    "gsheet_read": (t_gsheet_read, "Read the cells of a Google Sheet (id from drive_search, or the sheet open in the "
                    "user's tab when no id is given). Returns the tab names, columns and first rows, and saves the "
                    "whole tab as a CSV in the workspace folder for sheet_profile / sheet_query. Read-only.",
                    {"sheet_id": {"type": "string"}, "tab": {"type": "string", "description": "Tab name; default "
                     "the first tab"}, "max_rows": {"type": "integer", "description": "Rows to show (default 15)"}},
                    []),
}
