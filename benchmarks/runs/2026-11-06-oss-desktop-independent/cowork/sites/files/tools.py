"""Files site: the form for a spreadsheet Idli has been taught, and asking to be taught new ones.

Idli never computes numbers. For a spreadsheet it calls file_open, which recognises the file by its
headers (whatever its name), runs the contract test and the taught checks, and opens the file's
**form** in a browser tab: dropdowns built from the file skill and the data. A typed question becomes
a form spec for file_ask; the form tab follows along, so the person sees exactly what was counted.
An unknown file, or one whose layout changed, goes to teach_file / teach_send (Claude in the Teach
workspace, from a junk-data mock). Originals are never changed: checks go into "<name> - checked.xlsx".
file_get downloads the real file from a Google Sheets or Drive link (Google's quick export hides text in
number columns, so a download is better).
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from lib import filekit as fk
from lib import formkit as fm
from lib import formserver
from sites.sheets import tools as sh

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_files = None  # formserver.Files for this workspace (same code the page uses)
_last_get = {}  # link -> time the download was started


def files():
    global _files
    if _files is None or _files.data_dir != os.path.realpath(sh.data_dir()):
        _files = formserver.Files(sh.data_dir())
    return _files


# ---------------------------------------------------------------- the form server
def _server():
    """(port, token) of this workspace's form server, starting it if needed."""
    sf = formserver.state_file(sh.data_dir())
    def alive(st):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{st['port']}/api/form?t={st['token']}&file=_", timeout=2):
                return True
        except urllib.error.HTTPError as e:
            return e.code == 400  # the server answered with our token: it's ours
        except OSError:
            return False
    try:
        with open(sf) as f:
            st = json.load(f)
        if alive(st):
            return st["port"], st["token"]
    except (OSError, ValueError, KeyError):
        pass
    import socket
    port = None
    for p in range(formserver.PORT, formserver.PORT + 20):
        with socket.socket() as so:
            if so.connect_ex(("127.0.0.1", p)) != 0:
                port = p
                break
    if port is None:
        raise RuntimeError("No free port for the form page.")
    if os.path.exists(sf):
        os.remove(sf)
    env = {k: v for k, v in os.environ.items() if not k.startswith("PASEO_")}
    subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "lib", "formserver.py"), sh.data_dir(), str(port)],
                     start_new_session=True, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=open(os.path.join(os.path.dirname(sf) if os.path.isdir(os.path.dirname(sf)) else "/tmp",
                                              "form-server.log"), "a"))
    for _ in range(40):
        time.sleep(0.25)
        try:
            with open(sf) as f:
                st = json.load(f)
            if alive(st):
                return st["port"], st["token"]
        except (OSError, ValueError, KeyError):
            pass
    raise RuntimeError("The form page did not start.")


def form_url(file, tab=None, spec=None):
    port, token = _server()
    q = {"t": token, "file": file}
    if tab:
        q["tab"] = tab
    if spec:
        q["spec"] = json.dumps(spec, separators=(",", ":"))
    # *.localhost reaches this computer; the tab reads "dashboard.localhost" until it loads (then the file's title),
    # instead of a bare 127.0.0.1 nobody recognises
    return f"http://dashboard.localhost:{port}/?" + urllib.parse.urlencode(q)


def _show(url, file):
    """Open the form in a Paseo browser tab (reusing this file's form tab). Best effort: never fails the tool."""
    try:
        from lib.browser import paseo, tabs
        port = urllib.parse.urlparse(url).port
        # this file's dashboard tab, even one left from an earlier run of the server (another port)
        mine = [t for t in tabs() if urllib.parse.urlparse(t["url"]).hostname in ("127.0.0.1", "dashboard.localhost")
                and urllib.parse.parse_qs(urllib.parse.urlparse(t["url"]).query).get("file", [""])[0] == file]
        if mine:
            paseo("browser_navigate", browserId=mine[0]["id"], url=url)
        else:
            paseo("browser_new_tab", url=url)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- getting the real file
LINK = re.compile(r"(?:/spreadsheets/(?:u/\d+/)?d/|/file/(?:u/\d+/)?d/|[?&]id=)([\w-]{20,})")


def _download_dirs():
    out = [p for p in (os.environ.get("IDLI_DOWNLOAD_DIRS") or "").split(os.pathsep) if p]
    try:
        x = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        if x:
            out.append(x)
    except (OSError, subprocess.SubprocessError):
        pass
    out += [os.path.expanduser("~/Downloads"), sh.data_dir()]
    out += _recent_dirs()
    seen = []
    for p in out:
        if os.path.isdir(p) and os.path.realpath(p) not in seen:
            seen.append(os.path.realpath(p))
    return seen


def _recent_dirs(limit=6):
    """Folders the desktop's Save dialog recently saved spreadsheets into (it reopens the last one used),
    from GTK's recently-used list. Only folders are taken, and only for .xlsx/.csv entries."""
    import html
    p = os.path.expanduser("~/.local/share/recently-used.xbel")
    try:
        with open(p, encoding="utf-8", errors="ignore") as f:
            text = f.read()[-400000:]
    except OSError:
        return []
    dirs = []
    for m in re.finditer(r'href="file://([^"]+?\.(?:xlsx|csv))"', text):
        d = os.path.dirname(urllib.parse.unquote(html.unescape(m.group(1))))
        if d in dirs:
            dirs.remove(d)
        dirs.append(d)
    return list(reversed(dirs))[:limit]


def _raise_save_dialog():
    """Bring the browser's Save dialog to the front (Linux/X11 with xdotool). Its title is the download URL,
    so people don't recognise it, and it can open behind the Paseo window. Best effort."""
    if not shutil.which("xdotool"):
        return False
    try:
        ids = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "^https://doc-.*googleusercontent"],
                             capture_output=True, text=True, timeout=5).stdout.split()
        if ids:
            subprocess.run(["xdotool", "windowactivate", ids[-1]], capture_output=True, timeout=5)
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def _new_download(since, title):
    """A finished .xlsx/.csv saved after `since`, preferring one named like the sheet."""
    found = []
    for d in _download_dirs():
        for p in glob.glob(os.path.join(d, "*.xlsx")) + glob.glob(os.path.join(d, "*.csv")):
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_mtime >= since - 2 and st.st_size > 0 and "/checked/" not in p:
                name = os.path.splitext(os.path.basename(p))[0]
                score = 2 if title and fk.slug(name).startswith(fk.slug(title)[:20]) else 1
                found.append((score, st.st_mtime, p))
    if not found:
        return None
    p = max(found)[2]
    size = os.path.getsize(p)
    time.sleep(1)
    return p if os.path.getsize(p) == size else None


def t_file_get(link, wait_seconds=45):
    m = LINK.search(link or "")
    fid = m.group(1) if m else (link.strip() if re.fullmatch(r"[\w-]{20,}", (link or "").strip()) else None)
    if not fid:
        return {"error": "That doesn't look like a Google Sheets or Drive link. Use drive_search to find the file."}
    from lib.browser import paseo, tab_for
    from sites.google import tools as g
    sheet = "/spreadsheets/" in link or "/file/" not in link
    btab = tab_for("docs.google.com", "drive.google.com", open_url=g.drive_url())
    title = ""
    if sheet:
        try:
            title, _ = g.sheet_tabs(btab, fid)
        except ValueError as e:
            if "/spreadsheets/" in link:
                return {"error": str(e)}
            sheet = False
    since = _last_get.get(fid)
    got = _new_download(since, title) if since else None
    silent = None
    if not got:
        since = time.time()
        _last_get[fid] = since
        from lib import uiswitch
        incoming = os.path.join(sh.data_dir(), "drive", "incoming", str(int(since)))
        os.makedirs(incoming, exist_ok=True)
        quiet = uiswitch.QuietDownloads(incoming)  # dev builds: no Save box (shipping: Paseo patch P1)
        if quiet.ok:
            silent = incoming
            os.environ["IDLI_DOWNLOAD_DIRS"] = os.pathsep.join(
                [incoming] + [p for p in (os.environ.get("IDLI_DOWNLOAD_DIRS") or "").split(os.pathsep) if p])
        url = (g.sheets_url(fid, "export?format=xlsx") if sheet else
               "https://drive.google.com/uc?export=download&id=" + fid + g.au("&"))
        try:
            paseo("browser_navigate", browserId=btab, url=url)
        except RuntimeError:
            pass  # the page load is cancelled because the response is a file; the download goes on
        deadline = since + max(10, min(int(wait_seconds or 120), 300))
        raised = False
        while time.time() < deadline and not got:
            time.sleep(1.5)
            got = _new_download(since, title)
            if not got and not raised and not silent and time.time() - since > 3:
                raised = _raise_save_dialog()
        quiet.close()
        if sheet:
            try:
                paseo("browser_navigate", browserId=btab, url=g.sheets_url(fid, "edit"))
            except RuntimeError:
                pass
    if not got:
        return {"downloaded": False,
                "say_to_user": "I've asked the browser to download the file. A Save box should be open (its title is "
                               "a long Google address; it may be behind this window). Click Save, then tell me 'done'.",
                "then": "When they say done (or that they saved it), call file_get again with the same link. Only if "
                        "they can't download it, use gsheet_read, and tell them totals may be low because Google's "
                        "quick export hides text in number columns."}
    out_dir = os.path.join(sh.data_dir(), "drive")
    os.makedirs(out_dir, exist_ok=True)
    title = re.sub(r"(?i)\.(xlsx|xls|csv)$", "", title or "")  # uploaded Excel files keep .xlsx in their Drive name
    name = (re.sub(r"[^\w .()-]+", "_", title).strip() or os.path.splitext(os.path.basename(got))[0])[:80]
    dest = os.path.join(out_dir, name + os.path.splitext(got)[1])
    if os.path.realpath(got) != os.path.realpath(dest):
        shutil.copy2(got, dest)
    with open(dest + ".source.json", "w") as f:
        json.dump({"id": fid, "url": (g.sheets_url(fid, "edit") if sheet else f"https://drive.google.com/file/d/{fid}/view")}, f)
    _last_get.pop(fid, None)
    rel = os.path.relpath(dest, sh.data_dir())
    return {"downloaded": True, "file": rel, "title": title or name,
            "then": f"Call file_open(file='{rel}')."}


# ---------------------------------------------------------------- the form
def _brief(f):
    """What the model needs to fill a spec for one tab, kept short."""
    def vals(x):
        v = x.get("values") or []
        return v if len(v) <= 15 else v[:15] + [f"... {len(v) - 15} more"]
    return {"tab": f["tab"], "row_noun": f["row_noun"], "summary": f.get("summary", ""),
            "measures": {m["id"]: m["label"] for m in f["measures"]},
            "group_by": {g["id"]: g["label"] for g in f["group_by"]},
            "filters": {x["column"]: ({"label": x["label"], "values": vals(x)} if x["kind"] == "choice" else
                                      {"label": x["label"], "kind": x["kind"], "min": x.get("min"), "max": x.get("max")})
                        for x in f["filters"]},
            "presets": {p["id"]: p["label"] for p in f["presets"]},
            "date_columns": f["date_columns"]}


def t_file_open(file, show_form=True):
    meta = files().meta(file)
    if not meta["known"]:
        return {"file": file, "known": False,
                "then": "Idli hasn't been taught this file. Call teach_file now with the user's request as the question "
                        "(it only prepares a copy with fake values; nothing is sent until they say yes on its card). "
                        "Don't work out numbers from this file yourself."}
    c = meta["contract"]
    url = form_url(file)
    shown = _show(url, file) if show_form and c["status"] != "changed" else False
    e = files().open(file)
    kinds = {}
    for p in e["problems"]:
        if p.get("skipped"):
            continue
        k = kinds.setdefault((p["tab"], p["column"], p["problem"]), {"tab": p["tab"], "column": p["column"],
                                                                    "problem": p["problem"], "rows": []})
        if len(k["rows"]) < 4:
            k["rows"].append(p["row"])
    out = {"file": file, "title": meta["title"], "known": True, "today": fm.today(),
           "layout": c["status"], "layout_changes": c["messages"],
           "problems": len([p for p in e["problems"] if not p.get("skipped")]), "problem_kinds": list(kinds.values())[:12],
           "checked_copy": meta["checked_copy"], "form_link": url, "form_opened": shown,
           "tabs": [_brief(f) for f in e["forms"].values()]}
    if meta.get("hidden_cells"):
        out["warning"] = ("This copy came from Google's quick export, which hides text in number columns: "
                          + ", ".join(f"{k} ({v} cells)" for k, v in meta["hidden_cells"].items())
                          + ". Offer to download the real file with file_get.")
    if c["status"] == "changed":
        out["say_to_user"] = ("This file has changed since I was taught it: " + " ".join(c["messages"])
                              + " I'd like you to teach me the new layout before I answer. Is that OK?")
        out["then"] = "If they agree, call teach_file with their question (it updates the taught version)."
    else:
        bits = [f"I've opened the form for {meta['title']}" + (" in a new tab." if shown else f": {url}")]
        if meta.get("hidden_cells"):
            bits.append("Careful: this copy came from Google's quick export, which leaves some cells blank ("
                        + ", ".join(f"{k}: {v}" for k, v in meta["hidden_cells"].items())
                        + "), so totals from those columns may be low. I can download the real file instead.")
        if c["status"] == "drift":
            bits.append("It has changed a little since I was taught it: " + " ".join(c["messages"]))
        real = [p for p in e["problems"] if not p.get("skipped")]
        if real:
            fixable = sum(1 for p in real if (p.get("suggestion") or {}).get("to") is not None
                          or (p.get("suggestion") or {}).get("action"))
            bits.append(f"The checks found {len(real)} problem{'s' if len(real) > 1 else ''}; {fixable} have a suggested fix "
                        "you can accept or reject in the dashboard (the original is unchanged).")
        out["say_to_user"] = " ".join(bits)
        out["then"] = ("For a question about this file, call file_ask with a spec built only from these tabs' measures, "
                       "group_by, filters and presets. Ask the user if a value is unclear. If no measure or filter fits "
                       "the question, offer teach_file.")
        if shown:
            out["card"] = {"questions": [{"header": "Dashboard", "multiSelect": False,
                                          "question": f"The dashboard for {meta['title']} is open in a tab. Switch to it?",
                                          "options": [{"label": "Yes, show it", "description": "Pick what to see with "
                                                       "tick-boxes and dropdowns; answers show there too"},
                                                      {"label": "Stay here", "description": "Ask me in the chat"}]}]}
            out["then"] = ("Call AskUserQuestion with exactly `card` (don't write anything first); on \"Yes, show it\" "
                           "call show_dashboard. Then: " + out["then"])
    return out


def t_show_dashboard(file=None):
    """After the person said yes on the card: bring the file's dashboard tab to the front."""
    from lib import uiswitch
    title = ""
    if file:
        try:
            title = files().meta(file)["title"]
        except Exception:
            pass
    got = uiswitch.show_tab(([f"{title} - dashboard*"] if title else []) + ["dashboard.localhost", "Dashboard"])
    return {"shown": True} if got["ok"] else {"shown": False, "say_to_user": "Click the dashboard tab at the top."}


def t_file_ask(file, spec, tab=None):
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except ValueError:
            return {"error": "spec must be a JSON object."}
    try:
        res = files().run(file, tab, spec or {})
    except fm.SpecError as e:
        return {"error": str(e), "hint": "Use only ids from file_open's tabs. If nothing fits, offer teach_file."}
    except ValueError as e:
        msg = str(e)
        if "changed since" in msg:
            return {"error": msg, "then": "Offer teach_file to re-teach the new layout."}
        if "taught" in msg:
            return {"error": msg, "then": "Call file_open first; offer teach_file if Idli doesn't know the file."}
        return {"error": msg}
    url = form_url(file, res["tab"], spec)
    shown = _show(url, file)
    meta = files().meta(file)
    note = ""
    if meta.get("hidden_cells"):
        used = [k for k in meta["hidden_cells"] if fk.slug(k) in res["sql"]]
        if used:
            note = (" Say: " + ", ".join(used) + " may be missing values because this copy came from Google's quick "
                    "export; offer to download the real file with file_get.")
    if meta["contract"]["status"] == "drift":
        note += " Mention: " + " ".join(meta["contract"]["messages"])
    n_prob = meta.get("problem_count") or 0
    return {"answer": res["text"], "form_link": url, "form_updated": shown,
            "say_to_user": "Give the answer exactly as written (numbers unchanged), in a sentence or a short list. "
                           + ("Say the form tab now shows it." if shown else "Share the form link.")
                           + (" Rows that failed checks are included." if n_prob else "") + note}


_teach_src = {}  # request_id -> (path, question), so teach_send can remake the copy with the labels they allowed


def t_teach_file(file, question, share_labels=None, missing=None):
    path = sh.resolve(file)
    req, mock, preview = fk.make_mock(path, question, caller_agent=os.environ.get("PASEO_AGENT_ID"),
                                      share_labels=share_labels or (), missing=missing)
    _teach_src[req["id"]] = (path, question, missing)
    cols = list(req["columns"][req["main_sheet"]])
    tabs = list(req["columns"])
    labels = {c: v for c, v in fk.label_columns(path).items() if c not in (req.get("real_labels") or [])}
    title = req["title"]
    col_text = ", ".join(cols[:12]) + (f" and {len(cols) - 12} more" if len(cols) > 12 else "")
    questions = [{
        "header": "Claude",
        "question": ((f"The dashboard for {title} can't do this yet: {req['missing']}. Claude can add it" if req.get("missing")
                      and req["existing_skill"] else f"I haven't seen {title} before. Claude can build its dashboard with you")
                     + f" from a copy with fake values: same {'tabs and ' if len(tabs) > 1 else ''}columns ({col_text}), "
                     f"every value made up, and your question with names removed. Send it and switch to Claude?"),
        "multiSelect": False,
        "options": [{"label": "Yes, send and switch", "description": "Claude asks a few questions about the columns there"},
                    {"label": "Not now", "description": "Nothing is sent"}]}]
    shareable = list(labels.items())[:4]
    if shareable:
        questions.append({
            "header": "Labels",
            "question": "These columns hold labels. Tick any Claude may see as they are (helps it; leave people's and "
                        "places' names unticked). Untick all to keep every label fake.",
            "multiSelect": True,
            "options": [{"label": c, "description": "e.g. " + ", ".join(str(x) for x in v[:4])} for c, v in shareable]})
    return {"request_id": req["id"], "updating": req["existing_skill"], "card": {"questions": questions},
            "then": ("Call AskUserQuestion with exactly `card` (don't write anything first). If they pick \"Yes, send "
                     "and switch\", call teach_send with request_id and share_labels = the label columns they ticked "
                     "([] if none). If not, say nothing was sent and offer it again any time.")}


def t_teach_send(request_id, share_labels=None, switch=True):
    if share_labels and request_id in _teach_src:  # remake the copy with the labels they allowed, as one request
        path, question, missing = _teach_src.pop(request_id)
        req, _, _ = fk.make_mock(path, question, caller_agent=os.environ.get("PASEO_AGENT_ID"), share_labels=share_labels,
                                 missing=missing)
        shutil.rmtree(os.path.join(fk.TEACH_DIR, request_id), ignore_errors=True)
        request_id = req["id"]
    out = _teach_send(request_id)
    if out.get("started") and switch:
        try:
            with open(os.path.join(fk.TEACH_DIR, request_id, "teach_agent.json")) as f:
                agent = json.load(f)["agent"]
            from lib import uiswitch
            out["switched"] = uiswitch.show_agent(agent)["ok"]
        except (OSError, ValueError, KeyError):
            out["switched"] = False
        out["tell_the_user"] = ("Say in one line: sent a copy with fake values to Claude"
                                + (", and switched there to answer its questions." if out["switched"] else
                                   f"; open the Claude workspace (chat '{out['teach_chat']}') to answer its questions.")
                                + " This chat carries on when teaching is done.")
    return out


def _paseo():
    for p in (shutil.which("paseo"), os.path.expanduser("~/.local/bin/paseo"), "/usr/local/bin/paseo", "/usr/bin/paseo"):
        if p and os.path.exists(p):
            return p
    raise RuntimeError("The paseo command was not found on this computer.")


def _teach_send(request_id):
    rdir = os.path.join(fk.TEACH_DIR, request_id)
    with open(os.path.join(rdir, "request.json")) as f:
        req = json.load(f)
    prompt = (f"Idli asked to be taught a file. The request is in teach/inbox/{request_id}/ (mock.xlsx with fake data "
              f"and a hidden _idli_teach sheet, plus request.json). Question: \"{req['question']}\". "
              + (f"Idli already has a form for this file; it couldn't do this: \"{req['missing']}\". "
                 if req.get("missing") else "")
              + "Use the teach-file skill.")
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
    with open(os.path.join(rdir, "teach_agent.json"), "w") as f:
        json.dump({"agent": agent}, f)
    return {"started": True, "teach_chat": f"Teach: {req['title']}"}


def t_show_teach_chat(request_id):
    """After the person said yes on the card: switch Paseo to the Teach chat in the Claude workspace."""
    from lib import uiswitch
    try:
        with open(os.path.join(fk.TEACH_DIR, request_id, "teach_agent.json")) as f:
            agent = json.load(f)["agent"]
    except (OSError, ValueError, KeyError):
        return {"shown": False, "say_to_user": "Open the Claude workspace in the left sidebar to answer its questions."}
    got = uiswitch.show_agent(agent)
    return {"shown": got["ok"]} if got["ok"] else {
        "shown": False, "say_to_user": "Open the Claude workspace in the left sidebar to answer its questions."}


FILE = {"file": {"type": "string", "description": "Path in the workspace folder, from file_get, gsheet_read's "
                                                  "saved_csv or sheet_list"}}
SPEC = {"type": "object", "description":
        "Form spec, using ids from file_open's tab. Keys (all optional): measures [ids], group_by [up to 2 ids], "
        "filters {column: [values]} or {column: {min, max}} or {column: {not: [values]}} or {column: {blank: true}} "
        "(empty or unreadable), preset [ids], "
        "date {column, period} or {column, from, to}; period is one of " + ", ".join(fm.PERIODS)
        + "; from/to are YYYY-MM-DD or a month like 2026-09. "
        "sort {by: id, dir: desc|asc}, limit n. "
        "measures [] lists the matching rows: use it for who/which questions. Example: {\"measures\": [\"amount\"], \"group_by\": [\"employee\"], "
        "\"filters\": {\"category\": [\"Hardware\"]}, \"date\": {\"period\": \"this_year\"}}"}
TOOLS = {
    "file_get": (t_file_get, "Download the real spreadsheet from a Google Sheets or Drive link into this folder (better "
                 "than gsheet_read: Google's quick export hides text in number columns). The browser may show a Save "
                 "dialog; the user clicks Save. Then call file_open.",
                 {"link": {"type": "string", "description": "A docs.google.com/spreadsheets or drive.google.com link, or "
                                                            "a file id from drive_search"}}, ["link"]),
    "file_open": (t_file_open, "Open a spreadsheet's form: says whether Idli has been taught this file, whether its "
                  "layout changed, the problems the checks found, and what the form can answer (measures, group_by, "
                  "filters, presets per tab). Opens the form in a browser tab. Always call this before answering "
                  "anything about a spreadsheet.", {**FILE, "show_form": {"type": "boolean",
                                                                          "description": "Open the form tab (default true)"}},
                  ["file"]),
    "show_dashboard": (t_show_dashboard, "Bring the file's dashboard (form) tab to the front. Only after the user "
                       "said yes on the card.", {"file": {"type": "string", "description": "The file from file_open"}}, []),
    "file_ask": (t_file_ask, "Answer a question about an opened file by filling its form. The numbers come from the "
                 "data, never from you; the form tab shows the same answer.",
                 {**FILE, "spec": SPEC, "tab": {"type": "string", "description": "Tab name from file_open (default: "
                                                                                  "the first)"}}, ["file", "spec"]),
    "teach_file": (t_teach_file, "Prepare a teaching request for a file Idli doesn't know, or whose layout changed, or a "
                   "question the form can't answer: a copy of the file with fake values and the user's question with "
                   "names removed. Shows what would be sent; nothing is sent yet.",
                   {**FILE, "question": {"type": "string", "description": "The user's question, in their words"},
                    "missing": {"type": "string", "description": "For a file Idli already has a form for: what the "
                                "form couldn't do and what you tried, e.g. 'list sheet row numbers for matching trees; "
                                "file_ask lists the trees without row numbers'"},
                    "share_labels": {"type": "array", "items": {"type": "string"},
                                     "description": "Columns whose category labels the user agreed to send as they are"}},
                   ["file", "question"]),
    "teach_send": (t_teach_send, "After the user said yes on teach_file's card: send the fake copy to Claude in the "
                   "Claude workspace and switch the app there.",
                   {"request_id": {"type": "string"},
                    "share_labels": {"type": "array", "items": {"type": "string"},
                                     "description": "Label columns the user ticked on the card ([] for none)"}},
                   ["request_id"]),
}


def whoami():
    return "local files"
