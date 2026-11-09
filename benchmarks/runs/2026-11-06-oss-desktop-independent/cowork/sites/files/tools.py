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


def t_file_get(link, wait_seconds=45, open_after=True, goal=None):
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
    src = {}
    try:
        with open(dest + ".source.json") as f:
            src = json.load(f)
    except (OSError, ValueError):
        pass
    if src.get("id") != fid:
        src = {}
    src.update(id=fid, url=(g.sheets_url(fid, "edit") if sheet else f"https://drive.google.com/file/d/{fid}/view"))
    with open(dest + ".source.json", "w") as f:
        json.dump(src, f)
    _last_get.pop(fid, None)
    rel = os.path.relpath(dest, sh.data_dir())
    claim_chat(("Clean: " if (goal or "").startswith("clean") else "Analyse: ") + (title or name))
    if not open_after:
        return {"downloaded": True, "file": rel, "title": title or name}
    out = t_file_open(rel, goal=goal)  # one model turn fewer: the form opens with the download
    out["downloaded"] = True
    return out


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


def t_file_open(file, show_form=True, goal=None):
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
        src = files().source(file) or {}
        wc = src.get("working_copy")
        is_copy = bool(src.get("copy_of")) or "Idli working copy" in os.path.basename(file)
        from lib import chartkit
        out["charts"] = [{"id": x["id"], "title": x["title"]} for x in chartkit.charts_of(e["skill"])]
        if is_copy:
            bits.append(f"This is your checked working copy (the cleaned version): {len(real)} problem"
                        f"{'s' if len(real) != 1 else ''} left.")
        elif real:
            bits.append(f"The checks found {len(real)} problem{'s' if len(real) > 1 else ''} in "
                        f"{len({(p['tab'], p['column'], p['rule']) for p in real})} kinds"
                        + (f"; you marked them in a working copy on {wc.get('made', '')[:10]}." if wc else
                           "; the original is unchanged."))
        else:
            bits.append("The checks found no problems.")
        out["say_to_user"] = " ".join(bits)
        ask = ("For a question about this file, call file_ask with a spec built only from these tabs' measures, "
               "group_by, filters and presets (chart=true when they ask for a graph or picture). Ask the user if a value "
               "is unclear. If no measure or filter fits the question, call teach_file with `missing`. For a chart the "
               "form can't draw, call chart_request. Charts already made for this file: chart_show.")
        start = {"header": "Start", "multiSelect": False, "question": "How would you like to start?",
                 "options": [{"label": "I have a question", "description": "Ask in the chat; answers come from the form, "
                                                                           "with a chart when it helps"},
                             {"label": "Suggest analyses", "description": "Claude looks at a fake copy and suggests "
                                                                         "what to look at and how to chart it"}]}
        if out["charts"]:
            start["options"].append({"label": "Show the saved charts", "description": ", ".join(
                x["title"] for x in out["charts"][:3])})
        start_then = ('On "I have a question": ask in one short line what they want to know. On "Suggest analyses": '
                      "call chart_request with question \"\". On \"Show the saved charts\": call chart_show once with every "
                      "id in `charts`. ")
        goal = (goal or "analyse").lower()
        opts, act = [], []
        if goal.startswith("clean"):
            if is_copy:
                opts = [{"label": "Analyse it now", "description": "Questions and charts from this checked copy"},
                        {"label": "Stay here", "description": "Keep fixing; tell me when you're ready"}]
                act.append('On "Analyse it now": call AskUserQuestion with `start_card`. ' + start_then)
            elif wc:
                opts = [{"label": "Open my working copy", "description": wc.get("name", "")},
                        {"label": "Make a fresh copy", "description": "Marks the problems again from the latest original"},
                        {"label": "Not now", "description": "Nothing changes"}]
                act.append('On "Open my working copy": call working_copy. On "Make a fresh copy": call working_copy '
                           "with fresh=true. ")
            elif real and src.get("id"):
                opts = [{"label": "Yes, mark them in Drive", "description": "A copy next to the original: problem cells "
                         "in red, one comment on each kind of problem. You fix them there"},
                        {"label": "Not now", "description": "Nothing is written to Drive"}]
                act.append('On "Yes, mark them in Drive": call working_copy and stop there (analysis waits until they '
                           "say they're ready). ")
                out["say_to_user"] += " Mark them in a copy in your Drive?"
            else:
                opts = [{"label": "Analyse it now", "description": "Questions and charts"},
                        {"label": "Stay here", "description": ""}]
                act.append('On "Analyse it now": call AskUserQuestion with `start_card`. ' + start_then)
        else:
            if wc and not is_copy:
                opts = [{"label": "Use the checked copy", "description": f"{wc.get('name', '')} (the cleaned version; "
                                                                         "Recommended)"},
                        {"label": "Use the original", "description": "Answers include the problems the checks found"}]
                act.append('On "Use the checked copy": call working_copy_ready (it downloads the copy; then follow its '
                           'then). On "Use the original": call AskUserQuestion with `start_card`. ' + start_then)
                out["say_to_user"] += " You have a checked working copy. Analyse that one?"
            else:
                opts = list(start["options"])
                start_q = start["question"]
                if real and not is_copy:
                    out["say_to_user"] += " It hasn't been cleaned yet, so answers include those problems."
                    if src.get("id") and len(opts) < 4:
                        opts.append({"label": "Clean it first", "description": "Mark the problems in a copy in your "
                                                                               "Drive and fix them there"})
                        act.append('On "Clean it first": call working_copy and stop there. ')
                out["say_to_user"] += " " + start_q
                act.append(start_then)
        out["start_card"] = {"questions": [start]}
        out["card"] = {"questions": [{"header": "Next", "multiSelect": False, "question": out["say_to_user"],
                                      "options": opts}]}
        out["then"] = ("Call AskUserQuestion with exactly `card` now (it already says say_to_user; write nothing before "
                       "it). " + "".join(act) + "Afterwards: " + ask)
        if wc:
            out["working_copy"] = wc
            out["then"] += (" They have a working copy in Drive (" + wc.get("name", "") + "): when they say they're "
                            "ready or done fixing, call working_copy_ready.")
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


def t_file_ask(file, spec, tab=None, chart=False):
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except ValueError:
            return {"error": "spec must be a JSON object."}
    if isinstance(spec, dict) and "chart" in spec:  # the model often puts the flag inside the spec
        spec = dict(spec)
        chart = bool(spec.pop("chart")) or chart
    if isinstance(chart, str):
        chart = chart.lower() in ("true", "yes", "1")
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
    pic = None
    if chart:
        from lib import chartkit
        import hashlib
        key = hashlib.sha1(json.dumps([file, res["tab"], spec], sort_keys=True).encode()).hexdigest()[:10]
        out = os.path.join(_charts_dir(file), f"quick-{key}.svg")
        try:
            pic = chartkit.bar_svg(res, res["described"], out)
        except Exception as e:  # never lose the answer over a picture
            pic = None
            note += f" (No chart: {type(e).__name__}.)"
        if pic:
            with open(out[:-4] + ".json", "w") as f:
                json.dump({"title": res["described"], "tab": res["tab"], "spec": spec, "kind": "quick"}, f)
    if chart and pic:
        return {"answer": res["text"], "chart_markdown": f"![{res['described']}]({pic})", "form_link": url,
                "form_updated": shown,
                "say_to_user": "Write chart_markdown exactly, on its own line, then the answer in one or two short lines "
                               "(numbers unchanged). Then this line: \"The dashboard tab has it too. For a fuller "
                               "chart, say 'ask Claude' and I'll send Claude a copy with fake values to design it.\"" + note,
                "then": "If they then say 'ask Claude' (or want it drawn differently than the form can), call "
                        "chart_request with what they want the chart to show."}
    if chart and not pic:
        note += (" This answer has no breakdown to draw. If they wanted a picture, call chart_request with their "
                 "question (Claude designs it on fake data).")
    return {"answer": res["text"], "form_link": url, "form_updated": shown,
            "say_to_user": "Give the answer exactly as written (numbers unchanged), in a sentence or a short list. "
                           + ("Say the form tab now shows it." if shown else "Share the form link.")
                           + (" Rows that failed checks are included." if n_prob else "") + note}


_teach_src = {}  # request_id -> (path, question), so teach_send can remake the copy with the labels they allowed


def t_teach_file(file, question, share_labels=None, missing=None, chart=None):
    path = sh.resolve(file)
    req, mock, preview = fk.make_mock(path, question, caller_agent=os.environ.get("PASEO_AGENT_ID"),
                                      share_labels=share_labels or (), missing=missing, chart=chart)
    _teach_src[req["id"]] = (path, question, missing, chart)
    cols = list(req["columns"][req["main_sheet"]])
    tabs = list(req["columns"])
    labels = {c: v for c, v in fk.label_columns(path).items() if c not in (req.get("real_labels") or [])}
    title = re.sub(r"\s*-\s*Idli working copy.*$", "", req["title"])
    col_text = ", ".join(cols[:12]) + (f" and {len(cols) - 12} more" if len(cols) > 12 else "")
    questions = [{
        "header": "Claude",
        "question": ((("Claude can suggest analyses and charts for " + title) if chart == "" else
                      (f"Claude can design this chart for {title} with you") if chart is not None else
                      f"The dashboard for {title} can't do this yet: {req['missing']}. Claude can add it" if req.get("missing")
                      and req["existing_skill"] else f"I haven't seen {title} before. Claude can learn it with you (what "
                      "each column means, the checks for mistakes)")
                     + f" from a copy with fake values: same {'tabs and ' if len(tabs) > 1 else ''}columns ({col_text}), "
                     f"every value made up" + ("" if chart == "" else ", and your question with names removed") + "."
                     + (" Idli then draws it here from your real data." if chart is not None else "")
                     + " Send it and switch to Claude?"),
        "multiSelect": False,
        "options": [{"label": "Yes, send and switch", "description": ("Agree the chart with Claude there; you'll get a "
                                                                      "card to come back" if chart is not None else
                                                                      "Claude asks a few questions there, one at a time; "
                                                                      "you'll get a card to come back")},
                    {"label": "Not now", "description": "Nothing is sent"}]}]
    shareable = list(labels.items())[:3]
    if shareable:
        questions.append({
            "header": "Labels",
            "question": "Should Claude see any of these labels as they are? It helps Claude read codes such as species "
                        "or statuses; never tick people's or places' names. \"None\" keeps the whole copy fake.",
            "multiSelect": True,
            "options": [{"label": "None (Recommended)", "description": "Every value stays made up"}]
                       + [{"label": c, "description": "e.g. " + ", ".join(str(x) for x in v[:4])} for c, v in shareable]})
    if _show_mock(req["id"], title):
        questions[0]["question"] += " (The fake copy is open in the \"Fake copy\" tab if you want to look first.)"
    return {"request_id": req["id"], "updating": req["existing_skill"], "card": {"questions": questions},
            "then": ("Call AskUserQuestion with exactly `card` (don't write anything first). If they pick \"Yes, send "
                     "and switch\", call teach_send with request_id and share_labels = the label columns they ticked "
                     "([] for \"None\" or nothing ticked). If not, say nothing was sent and offer it again any time.")}


def t_teach_send(request_id, share_labels=None, switch=True):
    share_labels = [x for x in (share_labels or []) if not str(x).lower().startswith("none")]
    if share_labels and request_id in _teach_src:  # remake the copy with the labels they allowed, as one request
        path, question, missing, chart = _teach_src.pop(request_id)
        req, _, _ = fk.make_mock(path, question, caller_agent=os.environ.get("PASEO_AGENT_ID"), share_labels=share_labels,
                                 missing=missing, chart=chart)
        shutil.rmtree(os.path.join(fk.TEACH_DIR, request_id), ignore_errors=True)
        request_id = req["id"]
        _show_mock(request_id, req["title"])
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


def _show_mock(request_id, title):
    """Open (or update) a "Fake copy" tab showing exactly what Claude will get. Best effort."""
    try:
        from lib.browser import paseo, tabs
        port, token = _server()
        url = f"http://dashboard.localhost:{port}/mock?" + urllib.parse.urlencode({"t": token, "id": request_id})
        old = next((t for t in tabs() if "/mock?" in t["url"] and "dashboard.localhost" in t["url"]), None)
        if old:
            paseo("browser_navigate", browserId=old["id"], url=url)
        else:
            paseo("browser_new_tab", url=url)
        return True
    except Exception:
        return False


def _paseo():
    for p in (shutil.which("paseo"), os.path.expanduser("~/.local/bin/paseo"), "/usr/local/bin/paseo", "/usr/bin/paseo"):
        if p and os.path.exists(p):
            return p
    raise RuntimeError("The paseo command was not found on this computer.")


def _teach_send(request_id):
    rdir = os.path.join(fk.TEACH_DIR, request_id)
    with open(os.path.join(rdir, "request.json")) as f:
        req = json.load(f)
    if req.get("chart") is not None:
        prompt = (f"Idli asks for {'suggested analyses and charts' if not req['chart'] else 'a chart'} for "
                  f"{req['title']} (taught as file-skills/{req['existing_skill']}). The request is in "
                  f"teach/inbox/{request_id}/ (mock.xlsx with fake data, request.json). "
                  + (f"The chart they asked for: \"{req['chart']}\". " if req["chart"] else
                     "They want you to suggest what to look at. ")
                  + "Use the teach-file skill, section 'Chart requests'.")
    else:
        prompt = None
    prompt = prompt or (f"Idli asked to be taught a file. The request is in teach/inbox/{request_id}/ (mock.xlsx with fake data "
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
                        "--title", ("Chart: " if req.get("chart") is not None else "Teach: ") + req["title"], "--no-wait", "--json", prompt],
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
    return {"started": True, "teach_chat": ("Chart: " if req.get("chart") is not None else "Teach: ") + req["title"]}


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


# ---------------------------------------------------------------- a working copy in Drive, problems marked
def t_working_copy(file, fresh=False):
    """After the person said yes: put a copy of the file next to the original in their Drive, with the problems
    marked (lib/workcopy.py), and open it in a tab. The only write Idli makes to Drive, and only a new file."""
    from lib import uiswitch
    from lib import workcopy
    from lib.browser import paseo
    meta, e = files().meta(file), files().open(file)
    if not meta["known"]:
        return {"error": "Idli hasn't been taught this file yet.", "then": "Call teach_file with the user's request."}
    src = files().source(file) or {}
    if not src.get("id"):
        return {"error": "I don't know where this file is in Drive.", "then": "Ask for the file's Google link and "
                "call file_get with it, then working_copy."}
    if src.get("working_copy") and not fresh:
        wc = src["working_copy"]
        try:
            paseo("browser_new_tab", url=wc["url"])
        except Exception:
            pass
        return {"exists": True, "working_copy": wc,
                "say_to_user": f"You already have a working copy: {wc['name']} (opened in a tab). Fix the red cells "
                               "there and tell me when you're ready.",
                "then": "Write say_to_user. If they want a new copy instead, call working_copy with fresh=true."}
    if not e["path"].lower().endswith(".xlsx"):
        return {"error": "Working copies need an Excel or Google Sheets file."}
    problems = [p for p in e["problems"]]
    stamp = time.strftime("%d %b %H%M")
    stem = re.sub(r"\s*-\s*Idli working copy.*$", "", os.path.splitext(os.path.basename(e["path"]))[0])
    name = f"{stem} - Idli working copy {stamp}"
    out_dir = os.path.join(sh.data_dir(), "drive", "working")
    os.makedirs(out_dir, exist_ok=True)
    local = os.path.join(out_dir, name + ".xlsx")
    made = workcopy.build(e["path"], e["skill"], problems, local)
    from lib import driveindex as di
    folder = di.folder_of(src["id"]) or ("my-drive", "My Drive")
    from sites.google import tools as g
    folder_url = g.drive_url("my-drive" if folder[0] == "my-drive" else f"folders/{folder[0]}")
    manual = {"uploaded": False, "local_copy": os.path.relpath(local, sh.data_dir()),
              "say_to_user": f"I made the working copy but couldn't put it in your Drive. It's saved at {local}: drag "
                             f"it into the {folder[1]} folder in Drive, open it, and tell me when you're ready."}
    before = uiswitch.webview_ids()
    if not before:
        return manual  # no DevTools port (not our dev launcher): Paseo patch P9
    try:
        out = paseo("browser_new_tab", url=folder_url)
        m = re.search(r"browserId=(\S+)", out) or re.search(r'"browserId"\s*:\s*"([^"]+)"', out)
        bid = m and m.group(1)
    except RuntimeError:
        bid = None
    uiswitch.show_tab([f"{folder[1]} - Google Drive*", "drive.google.com*"])
    tid = uiswitch.new_page(before)
    if not tid:
        return manual
    page = uiswitch.Page(tid)
    try:
        end = time.time() + 20
        while time.time() < end and not page.eval("document.readyState === 'complete' && "
                                                  "!!document.querySelector('[data-id], [role=main]')"):
            time.sleep(0.5)
        time.sleep(2)
        if not page.drop_file(local):
            return manual
        fid, end = None, time.time() + 120
        find = ("(n => { const e = [...document.querySelectorAll('[data-id]')].find(e => (e.innerText || '').includes(n));"
                " return e ? e.getAttribute('data-id') : null; })(%s)" % json.dumps(name))
        done = "/(\\d+ )?uploads? complete/i.test(document.body.innerText)"
        while time.time() < end and not fid and not page.eval(done):
            time.sleep(1.5)
            fid = page.eval(find)
        # a narrow tab lists files without their ids in view: look the new file up by its exact name
        for _ in range(3):
            if fid:
                break
            page.c.call("Page.navigate", {"url": g.drive_url("search?q=" + urllib.parse.quote(name))})
            t_end = time.time() + 25
            while time.time() < t_end and not fid:
                time.sleep(1.5)
                fid = page.eval(find)
    finally:
        page.close()
    if not fid:
        return manual
    url = g.sheets_url(fid, "edit")
    if bid:
        try:
            paseo("browser_navigate", browserId=bid, url=url)
        except RuntimeError:
            pass
    src["working_copy"] = {"id": fid, "url": url, "name": name, "folder": folder[1], "made": time.strftime("%Y-%m-%d %H:%M"),
                           "problems": made["cells"]}
    with open(files().resolve(file) + ".source.json", "w") as f:
        json.dump(src, f)
    return {"uploaded": True, "working_copy": src["working_copy"],
            "say_to_user": f"I put \"{name}\" next to the original in {folder[1]} and opened it in a tab. Red cells are "
                           "problems and turn white once fixed; each kind of problem has one comment on its first cell "
                           "(the number on each tab's name), and the last tab, Idli checks, lists them all. The original "
                           "is unchanged. Fix what you can, then tell me you're ready and I'll analyse the copy.",
            "then": "Write say_to_user, nothing else. Don't answer questions about the file until they say they're ready "
                    "(then call working_copy_ready) or ask you to go ahead with the original."}


def t_working_copy_ready(file):
    """The person says they've fixed what they can: download the working copy and open its form."""
    from lib import workcopy
    src = files().source(file) or {}
    wc = src.get("working_copy")
    if not wc:  # called on the copy itself, or no copy yet
        return {"error": "No working copy for this file.", "then": "Offer working_copy, or answer from the original."}
    got = t_file_get(wc["url"], open_after=False)
    if not got.get("downloaded"):
        return got
    workcopy.strip(files().resolve(got["file"]))
    cs = files().resolve(got["file"]) + ".source.json"
    try:
        with open(cs) as f:
            csrc = json.load(f)
    except (OSError, ValueError):
        csrc = {}
    csrc.update(copy_of=file, problems_before=wc.get("problems"))
    with open(cs, "w") as f:
        json.dump(csrc, f)
    out = t_file_open(got["file"], show_form=True, goal="analyse")
    fixed = (wc.get("problems") or 0) - (out.get("problems") or 0)
    out["say_to_user"] = (("Checked your working copy again: you fixed " + str(fixed) + ". " if fixed > 0 else
                           "Checked your working copy again. ") + out.get("say_to_user", ""))
    if out.get("card"):
        out["card"]["questions"][0]["question"] = out["say_to_user"]
    out["then"] = ("From now on use the file '" + got["file"] + "' (the working copy) for every tool. If they asked a "
                   "question while fixing, answer it now with file_ask instead of the card. Otherwise: " + out.get("then", ""))
    return out


# ---------------------------------------------------------------- charts
def _charts_dir(file):
    stem = re.sub(r"[^\w.-]+", "_", os.path.splitext(os.path.basename(file))[0])
    d = os.path.join(sh.data_dir(), "charts", stem)
    os.makedirs(d, exist_ok=True)
    return d


def t_chart_request(file, question=""):
    """Send a fake copy to Claude to design a chart (or suggest analyses when question is empty)."""
    meta = files().meta(file)
    if not meta["known"]:
        return {"error": "Idli hasn't been taught this file yet.",
                "then": "Call teach_file first (Claude learns the file), then ask for the chart."}
    out = t_teach_file(file, question or "suggest analyses", chart=question or "")
    return out


def t_chart_show(file, chart=None, charts=None):
    """Draw the file's charts (written by Claude on fake data) from the real data, here. One id, or several."""
    want = [c for c in (charts or []) if c] or ([chart] if chart else [])
    if isinstance(charts, str):
        want = [x.strip() for x in charts.split(",") if x.strip()]
    if len(want) > 1:
        outs = [t_chart_show(file, c) for c in want]
        ok = [o for o in outs if o.get("chart_markdown")]
        return {"chart_markdown": "\n\n".join(o["chart_markdown"] for o in ok),
                "titles": [o["title"] for o in ok], "errors": [o["error"] for o in outs if o.get("error")],
                "say_to_user": "Write chart_markdown exactly (every image, each on its own line), then one short line "
                               "per chart on what it shows (no numbers you didn't get from a tool). Say they're also on "
                               "the dashboard tab."}
    chart = want[0] if want else None
    from lib import chartkit
    e = files().open(file)
    if not e["skill"]:
        return {"error": "Idli hasn't been taught this file yet."}
    ids = {c["id"]: c for c in chartkit.charts_of(e["skill"])}
    if chart not in ids:
        return {"error": f"No chart '{chart}'. Charts for this file: {sorted(ids) or 'none yet'}.",
                "then": "Call chart_request to have Claude design one."}
    out = os.path.join(_charts_dir(file), chart + ".svg")
    r = chartkit.render(e["skill"]["_dir"], chart, e["path"], out)
    if not r["ok"]:
        return {"error": "The chart didn't draw on the real data: " + r["error"][-300:],
                "then": "Say the chart failed on the real data and offer chart_request to have Claude fix it."}
    title = ids[chart]["title"] or chart
    with open(out[:-4] + ".json", "w") as f:
        json.dump({"title": title, "chart": chart, "kind": "claude"}, f)
    return {"chart_markdown": f"![{title}]({out})", "title": title,
            "say_to_user": "Write chart_markdown exactly, on its own line, then one short line on what it shows "
                           "(no numbers you didn't get from a tool). Say it's also on the dashboard tab."}


def t_show_skills():
    """Open the page that lists what Idli has learned (one skill per file) and lets the person delete one."""
    port, token = _server()
    url = f"http://dashboard.localhost:{port}/skills?t={token}"
    try:
        from lib.browser import paseo, tabs
        old = next((t for t in tabs() if "/skills" in t["url"] and "dashboard.localhost" in t["url"]), None)
        if old:
            paseo("browser_navigate", browserId=old["id"], url=url)
        else:
            paseo("browser_new_tab", url=url)
    except Exception:
        pass
    from lib import uiswitch
    uiswitch.show_tab(["What Idli has learned*", "dashboard.localhost"])
    return {"say_to_user": "The page listing what Idli has learned is open in a tab; delete a file's skill there to "
                           "teach it again from scratch."}


# ---------------------------------------------------------------- the start of an Idli chat
def t_start():
    """The first card of an Idli chat: clean up a file, or analyse one."""
    from lib import driveindex as di
    st = di.status()
    if not st.get("phase") and not os.path.exists(di.DB):
        return {"indexed": False, "say_to_user": "I can't find your files yet: open the Start here chat in the left "
                                                  "sidebar and index your Drive first (1 to 5 minutes). Then come back."}
    me = os.environ.get("PASEO_AGENT_ID")
    try:
        mine = next((a for a in _agents() if a["id"] == me), None)
        if mine and mine.get("name") != SPARE:
            ensure_spare()  # a chat the person made themselves: keep a waiting one ready for next time
    except Exception:
        pass
    card = {"questions": [{"header": "Idli", "multiSelect": False,
                           "question": "Hi, I'm Idli. Everything you show me stays on this computer. What would you like "
                                       "to do?",
                           "options": [{"label": "Clean up a file", "description": "Find mistakes in a spreadsheet and "
                                        "mark them in a copy in your Drive to fix"},
                                       {"label": "Analyse a file", "description": "Ask questions and get charts, answered "
                                        "from the file itself"}]}]}
    return {"indexed": True, "card": card,
            "then": "Call AskUserQuestion with exactly `card` (write nothing first). Then ask in one short line which "
                    "file (a few words from its name, or a link). When they answer, find it (drive_find, or file_get "
                    "straight away for a link) and call file_get with goal \"clean\" or \"analyse\" to match."}


# ---------------------------------------------------------------- a new chat that is already waiting
SPARE = "New chat"
_SPARE_STAMP = os.path.expanduser("~/idli-insights/config/spare-chat.json")


def _user_cli(*args, timeout=60):
    """The paseo CLI as the person (not as this agent, whose CLI calls are limited to its own workspace)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("PASEO_")}
    return subprocess.run([_paseo(), *args], capture_output=True, text=True, timeout=timeout, env=env)


def _agents():
    r = _user_cli("ls", "--global", "--json")
    return json.loads(r.stdout or "[]")


def ensure_spare():
    """Keep one Idli chat open on the start card ("Clean up a file / Analyse a file"), so a person never waits
    for the model to greet them. Runs in the background; at most one spare, at most one start per two minutes."""
    import threading

    def go():
        try:
            try:
                with open(_SPARE_STAMP) as f:
                    if time.time() - json.load(f).get("ts", 0) < 120:
                        return
            except (OSError, ValueError):
                pass
            me = os.environ.get("PASEO_AGENT_ID", "")
            here = os.path.realpath(sh.data_dir())
            for a in _agents():
                if a.get("name") == SPARE and a["id"] != me and a.get("status") != "closed" and \
                        os.path.realpath(os.path.expanduser(a.get("cwd") or "")) == here:
                    return
            ws = json.loads(_user_cli("workspace", "ls", "--json").stdout or "[]")
            wid = next((w["workspaceId"] for w in ws if os.path.realpath(os.path.expanduser(w["cwd"])) == here), None)
            if not wid:
                return
            os.makedirs(os.path.dirname(_SPARE_STAMP), exist_ok=True)
            with open(_SPARE_STAMP, "w") as f:
                json.dump({"ts": time.time()}, f)
            _user_cli("run", "--provider", os.environ.get("IDLI_PROVIDER", "t4gc-cowork"), "--workspace", wid,
                      "--mode", "bypassPermissions", "--thinking", "low", "--title", SPARE, "--no-wait", "hi",
                      timeout=90)
        except Exception:
            pass
    threading.Thread(target=go, daemon=True).start()


def claim_chat(name):
    """The person started using a waiting "New chat": give it a real name, and open the next spare."""
    me = os.environ.get("PASEO_AGENT_ID")
    try:
        mine = next((a for a in _agents() if a["id"] == me), None)
        if mine and (mine.get("name") == SPARE or str(mine.get("name", "")).startswith("Find: ")):
            _user_cli("agent", "update", me, "--name", name[:60])
    except Exception:
        pass
    ensure_spare()


# ---------------------------------------------------------------- what Idli has learned, in a chat
def t_skills_list():
    """What Idli has learned, as a table for the chat (the Mission control chat "What Idli has learned")."""
    rows = formserver.skills_list()
    if not rows:
        return {"table": "Nothing yet.", "say_to_user": "Write `table`. Then: files you clean or analyse in Idli are "
                                                         "learned with Claude and appear here."}
    lines = ["| File | Version | Tabs | Checks | Measures | Charts | Changed |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| **{r['title']}** | v{r['version']} | {', '.join(r['tabs'])} | {r['checks']} | {r['measures']} | "
                     f"{len(r['charts'])} | {r['changed']} |")
    lines += ["", "Say \"delete <file>\" to make Idli forget a file (you'd teach it again with Claude), or \"refresh\" "
              "to update this list."]
    return {"table": "\n".join(lines), "ids": {r["title"]: r["id"] for r in rows},
            "say_to_user": "Write `table` exactly as it is (it ends with a line about deleting); nothing else."}


def t_skill_delete(file_title, confirmed=False):
    rows = formserver.skills_list()
    hit = next((r for r in rows if r["title"].lower() == str(file_title).lower() or r["id"] == file_title), None) or \
        next((r for r in rows if str(file_title).lower() in r["title"].lower()), None)
    if not hit:
        return {"error": f"Nothing learned called '{file_title}'.", "then": "Call skills_list and show it."}
    if not confirmed:
        return {"card": {"questions": [{"header": "Forget", "multiSelect": False,
                                        "question": f"Forget {hit['title']}? Idli loses its checks, measures and "
                                                    f"{len(hit['charts'])} chart(s); you'd teach it again with Claude. "
                                                    "(A copy is kept in idli-insights/archive/skills.)",
                                        "options": [{"label": "Yes, forget it", "description": hit["title"]},
                                                    {"label": "Keep it", "description": "Nothing changes"}]}]},
                "then": f"Call AskUserQuestion with exactly `card` (write nothing first). On \"Yes, forget it\" call "
                        f"skill_delete with file_title '{hit['id']}' and confirmed=true, then skills_list."}
    out = formserver.skills_delete(hit["id"])
    return {"deleted": hit["title"], "say_to_user": f"Done: Idli has forgotten {hit['title']}."}


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
                                                            "a file id from drive_search"},
                  "goal": {"type": "string", "enum": ["clean", "analyse"],
                           "description": "What the user wants to do with it (default analyse)"}}, ["link"]),
    "file_open": (t_file_open, "Open a spreadsheet's form: says whether Idli has been taught this file, whether its "
                  "layout changed, the problems the checks found, and what the form can answer (measures, group_by, "
                  "filters, presets per tab). Opens the form in a browser tab. Always call this before answering "
                  "anything about a spreadsheet.", {**FILE, "show_form": {"type": "boolean",
                                                                          "description": "Open the form tab (default true)"},
                                                     "goal": {"type": "string", "enum": ["clean", "analyse"]}},
                  ["file"]),
    "show_dashboard": (t_show_dashboard, "Bring the file's dashboard (form) tab to the front. Only after the user "
                       "said yes on the card.", {"file": {"type": "string", "description": "The file from file_open"}}, []),
    "file_ask": (t_file_ask, "Answer a question about an opened file by filling its form. The numbers come from the "
                 "data, never from you; the form tab shows the same answer.",
                 {**FILE, "spec": SPEC, "tab": {"type": "string", "description": "Tab name from file_open (default: "
                                                                                  "the first)"},
                  "chart": {"type": "boolean", "description": "Also draw the answer as a bar chart in the chat (needs "
                                                              "group_by and a measure)"}}, ["file", "spec"]),
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
    "working_copy": (t_working_copy, "Only after the user said yes (the card, or they asked): put a copy of the file "
                     "next to the original in their Drive with the problems marked (red cells, one comment per kind of "
                     "problem, an 'Idli checks' tab) and open it in a tab. The original is never changed.",
                     {**FILE, "fresh": {"type": "boolean", "description": "Make a new copy even if one exists"}}, ["file"]),
    "working_copy_ready": (t_working_copy_ready, "When the user says they've fixed the working copy (ready, done): "
                           "download it, re-check it and open its form.", FILE, ["file"]),
    "chart_request": (t_chart_request, "For a chart or analysis the form's quick chart can't draw, or when the user "
                      "wants Claude to suggest analyses: prepares a copy with fake values for Claude to design the chart "
                      "on. Shows a card first; nothing is sent until they say yes.",
                      {**FILE, "question": {"type": "string", "description": "The chart they asked for, in their words; "
                                                                             "empty = suggest analyses"}}, ["file"]),
    "chart_show": (t_chart_show, "Draw the file's charts (Claude wrote them on fake data) from the real data and "
                   "return markdown to show them in the chat. Pass every chart id at once in `charts`.",
                   {**FILE, "charts": {"type": "array", "items": {"type": "string"},
                                       "description": "Chart ids (from file_open's charts, or Claude's message)"},
                    "chart": {"type": "string", "description": "One chart id"}}, ["file"]),
    "show_skills": (t_show_skills, "Open the page listing what Idli has learned (one skill per file), where the user "
                    "can delete one.", {}, []),
    "start": (t_start, "The first step of an Idli chat when the user says hi or hasn't said what they want: a card "
              "asking whether to clean up a file or analyse one.", {}, []),
    "skills_list": (t_skills_list, "What Idli has learned: one row per file taught with Claude (checks, measures, "
                    "charts).", {}, []),
    "skill_delete": (t_skill_delete, "Make Idli forget one file's skill (after a yes on its card).",
                     {"file_title": {"type": "string", "description": "The file's name from skills_list"},
                      "confirmed": {"type": "boolean", "description": "True only after the user said yes on the card"}},
                     ["file_title"]),
}


def whoami():
    return "local files"
