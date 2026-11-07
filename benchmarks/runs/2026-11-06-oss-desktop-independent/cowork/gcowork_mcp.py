#!/usr/bin/env python3
"""gcowork: "UI as API" tools for Gmail and Google Drive inside Paseo's browser tabs.

A tiny stdio MCP server (no dependencies). Each tool drives the user's logged-in Paseo
browser tab through Paseo's own browser tools (daemon endpoint /mcp/agents), parses the
page snapshot, and returns only a compact result, so a small model never sees a whole page.

Deliberately missing: any way to send email, delete, or edit a document. Drafting a reply
types into Gmail's reply box and leaves it as a draft for the user to review.

Env: PASEO_AGENT_ID (set by Paseo for every agent), PASEO_MCP_URL (optional).
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

MCP_URL = os.environ.get("PASEO_MCP_URL", "http://127.0.0.1:6767/mcp/agents")
AGENT_ID = os.environ.get("PASEO_AGENT_ID", "")
LOG = os.environ.get("GCOWORK_LOG")  # optional debug log path

_last_search = {"tab": None, "query": None}


def log(*a):
    if LOG:
        with open(LOG, "a") as f:
            print(time.strftime("%H:%M:%S"), *a, file=f)


# ---------------------------------------------------------------- Paseo browser calls
def paseo(tool, **args):
    url = MCP_URL + "?" + urllib.parse.urlencode({"callerAgentId": AGENT_ID})
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    req = urllib.request.Request(url, body, {"content-type": "application/json",
                                             "accept": "application/json, text/event-stream"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    msg = None
    for line in raw.splitlines():
        if line.startswith("data:"):
            msg = json.loads(line[5:])
    msg = msg or json.loads(raw)
    res = msg.get("result", {})
    text = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
    if res.get("isError") or "error" in msg:
        raise RuntimeError(text or json.dumps(msg.get("error")))
    log(tool, json.dumps(args)[:200], "->", len(text), "chars")
    return text


def tabs():
    out = []
    for m in re.finditer(r'browserId=(\S+)( active)? title="(.*)" url=(\S+)', paseo("browser_list_tabs")):
        out.append({"id": m.group(1), "active": bool(m.group(2)), "title": m.group(3), "url": m.group(4)})
    return out


def tab_for(*hosts):
    """Reuse the user's tab for this site (prefer the active one), else open one."""
    ts = [t for t in tabs() if any(h in t["url"] for h in hosts)]
    ts.sort(key=lambda t: not t["active"])
    if ts:
        return ts[0]["id"]
    m = re.search(r"browserId=(\S+)", paseo("browser_new_tab", url="https://" + hosts[0]))
    return m.group(1)


def snapshot(tab, ready=None, tries=8):
    """Snapshot until `ready(snap)` is true (pages render after navigation)."""
    snap = ""
    for _ in range(tries):
        snap = paseo("browser_snapshot", browserId=tab)
        if ready is None or ready(snap):
            return snap
        time.sleep(1)
    return snap


def q(s):  # unescape a quoted snapshot label
    return s.replace('\\"', '"')


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


# ---------------------------------------------------------------- Drive parsing
def drive_files(tab):
    js = ('() => { const seen = {}; const out = [];'
          ' for (const e of document.querySelectorAll("[data-id]")) {'
          '  const id = e.getAttribute("data-id"); const t = (e.innerText || "").trim();'
          '  if (!t || id.length < 20 || seen[id]) continue; seen[id] = 1;'
          '  const lines = t.split("\\n").map(s => s.trim()).filter(Boolean);'
          '  out.push({id, name: lines[0], info: lines.slice(1, 4).join(" | ")}); }'
          ' return JSON.stringify(out.slice(0, 25)); }')
    raw = paseo("browser_evaluate", browserId=tab, function=js)
    payload = raw.split("returned:", 1)[-1].strip()  # a JSON string holding our JSON array
    try:
        val = json.loads(payload)
        return json.loads(val) if isinstance(val, str) else val
    except ValueError:
        return []


def doc_text(tab, doc_id):
    paseo("browser_navigate", browserId=tab,
          url=f"https://docs.google.com/document/d/{doc_id}/mobilebasic")
    snap = snapshot(tab, lambda s: s.count("- text:") > 2)
    title = (re.search(r"^Title: (.*)$", snap, re.M) or [None, ""])[1]
    paras = [q(m.group(1)) for m in re.finditer(r'^\s*- text: "(.*)"$', snap, re.M)]
    if paras and paras[0] == title:
        paras = paras[1:]
    # put the normal doc back in front of the user
    paseo("browser_navigate", browserId=tab, url=f"https://docs.google.com/document/d/{doc_id}/edit")
    return title, paras


# ---------------------------------------------------------------- tools
def t_list_tabs():
    return [{"title": t["title"], "url": t["url"], "active": t["active"]} for t in tabs()]


def t_gmail_search(query, max_results=10):
    tab = tab_for("mail.google.com")
    paseo("browser_navigate", browserId=tab,
          url="https://mail.google.com/mail/u/0/#search/" + urllib.parse.quote_plus(query))
    snap = snapshot(tab, lambda s: ("- row \"" in s and "link \"" in s) or "No messages matched" in s)
    rows = parse_gmail_rows(snap)
    _last_search.update(tab=tab, query=query)
    return {"query": query, "results": [{k: v for k, v in r.items() if k != "_ref"}
                                        for r in rows[:max_results]],
            "note": "Use gmail_open with n to read one." if rows else "No messages matched."}


def t_gmail_open(n):
    tab = _last_search["tab"] or tab_for("mail.google.com")
    rows = parse_gmail_rows(snapshot(tab, lambda s: "- row \"" in s))
    if not 1 <= n <= len(rows):
        return {"error": f"No result {n}; the current list has {len(rows)}. Run gmail_search again."}
    paseo("browser_click", browserId=tab, ref=rows[n - 1]["_ref"])
    thread = parse_gmail_thread(snapshot(tab, lambda s: "- main" in s and "[level=3]" in s))
    return thread or {"error": "Could not read the email."}


def t_gmail_read_open_email():
    tab = tab_for("mail.google.com")
    thread = parse_gmail_thread(snapshot(tab, lambda s: "- main" in s))
    return thread if thread and thread["messages"] else {"error": "No email is open in the Gmail tab."}


def t_gmail_draft_reply(text):
    tab = tab_for("mail.google.com")
    snap = snapshot(tab)
    refs = re.findall(r'- button "Reply" \[(?:[^\]]*\s)?ref=(@e\d+)', snap)
    if not refs:
        return {"error": "Open the email to reply to first (gmail_open or gmail_read_open_email)."}
    paseo("browser_click", browserId=tab, ref=refs[-1])
    box = None
    for _ in range(8):
        time.sleep(1)
        s = snapshot(tab)
        m = re.search(r'- textbox "Message Body"[^\n]*ref=(@e\d+)', s)
        if m:
            box = m.group(1)
            break
    if not box:
        return {"error": "The reply box did not open."}
    paseo("browser_type", browserId=tab, ref=box, text=text)
    return {"status": "Draft written in the Gmail tab and NOT sent. Gmail saves it to Drafts; "
                      "the user reviews and sends it themselves."}


def t_drive_search(query):
    tab = tab_for("drive.google.com", "docs.google.com")
    paseo("browser_navigate", browserId=tab,
          url="https://drive.google.com/drive/search?q=" + urllib.parse.quote_plus(query))
    files = []
    for _ in range(8):
        time.sleep(1)
        files = drive_files(tab)
        if files:
            break
    return {"query": query, "files": [dict(n=i + 1, **f) for i, f in enumerate(files)],
            "note": "Use doc_read with the id of a Google Doc to read it."}


def t_doc_read(doc_id=None):
    tab = tab_for("docs.google.com", "drive.google.com")
    if not doc_id:
        cur = next((t for t in tabs() if t["id"] == tab), {})
        m = re.search(r"/document/d/([\w-]{20,})", cur.get("url", ""))
        if not m:
            return {"error": "No doc id given and no Google Doc is open. Use drive_search first."}
        doc_id = m.group(1)
    title, paras = doc_text(tab, doc_id)
    text = "\n".join(paras)
    return {"title": title, "doc_id": doc_id, "paragraphs": len(paras),
            "text": text[:12000] + ("\n…[truncated]" if len(text) > 12000 else ""),
            "note": "Read-only. Suggest changes in chat; never edit the doc."}


TOOLS = {
    "list_tabs": (t_list_tabs, "List the browser tabs the user has open in Paseo (title, url, which is active).",
                  {}),
    "gmail_search": (t_gmail_search, "Search the user's Gmail (Gmail search syntax works, e.g. from:aws "
                     "newer_than:2m payment). Shows the results in the user's Gmail tab and returns a short list.",
                     {"query": {"type": "string"}, "max_results": {"type": "integer"}}),
    "gmail_open": (t_gmail_open, "Open result n from the last gmail_search and return the email text.",
                   {"n": {"type": "integer"}}),
    "gmail_read_open_email": (t_gmail_read_open_email, "Read the email the user currently has open in Gmail.", {}),
    "gmail_draft_reply": (t_gmail_draft_reply, "Write a reply to the open email as a DRAFT in the user's Gmail "
                          "tab. It is never sent; the user reviews it.", {"text": {"type": "string"}}),
    "drive_search": (t_drive_search, "Search the user's Google Drive by name or content; returns files with ids.",
                     {"query": {"type": "string"}}),
    "doc_read": (t_doc_read, "Read the text of a Google Doc (by id from drive_search, or the doc open in the "
                 "user's tab when no id is given). Read-only.", {"doc_id": {"type": "string"}}),
}
REQUIRED = {"gmail_search": ["query"], "gmail_open": ["n"], "gmail_draft_reply": ["text"], "drive_search": ["query"]}


# ---------------------------------------------------------------- stdio MCP
def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        if mid is None:
            continue  # notification
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}}, "serverInfo": {"name": "gcowork", "version": "0.1"}}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [
                {"name": n, "description": d, "inputSchema": {"type": "object", "properties": p,
                                                              "required": REQUIRED.get(n, [])}}
                for n, (_, d, p) in TOOLS.items()]}})
        elif method == "tools/call":
            name, args = msg["params"]["name"], msg["params"].get("arguments") or {}
            try:
                out = TOOLS[name][0](**args)
                res = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)}]}
            except Exception as e:  # report, don't crash
                log("ERROR", name, repr(e))
                res = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
            send({"jsonrpc": "2.0", "id": mid, "result": res})
        else:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--call":  # dev: gcowork_mcp.py --call tool '{json}'
        print(json.dumps(TOOLS[sys.argv[2]][0](**json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")),
                         ensure_ascii=False, indent=1))
    else:
        main()
