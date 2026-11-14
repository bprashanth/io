#!/usr/bin/env python3
"""Idli first-run bootstrap: make a Paseo install look the way Idli should on first open.
Safe to rerun: it only adds what's missing.

  Start here       its own folder (~/idli-insights/setup), first in the sidebar
     Logins           the setup chat (sign-in checks; also answers "what has Idli learned")
     Minis            a tab: the page listing the files Idli has learned (grows as Claude teaches it)
     Drive            a tab for signing in to Google
  Drivey       the private folder (~/idli-insights/cowork-real): Drive files, where the work happens; a "New chat"
     Drivey    is always waiting there on its first card (clean up a file / analyse a file). Its chats get the split
               panel (the private model on the left, Claude beside it).
  WhatsAppy    ~/idli-insights/whatsappy: chats open straight to Claude (the person's own subscription), no split.
  Canvay       ~/idli-insights/canvay: the same. Both are open spaces to try out Minis beyond Drive
               (narrative/IDLI_DESKTOP.md).
  Claude      this cowork/ folder: Claude teaches Idli a file, from fake data only
     Claude

Runs on the machine with Paseo, after the daemon is up (desktop/idli-launch.sh does that). The heading order
needs Paseo patch P2 (todos/idli-insights/p1/paseo_patches.md); until then the person drags them once.
Providers (Idli 30B, Claude) come from desktop/setup-laptop.py.

  python3 desktop/idli-bootstrap.py            do it
  python3 desktop/idli-bootstrap.py --dry-run  say what it would do
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse

COWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDLI = os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights")
DRY = "--dry-run" in sys.argv
LAYOUT = [  # (workspace name, folder, instructions copied to <folder>/CLAUDE.md)
    ("Start here", os.path.join(IDLI, "setup"), os.path.join(COWORK, "idli", "START-HERE.md")),
    ("Drivey", os.path.join(IDLI, "cowork-real"), os.path.join(COWORK, "idli", "CLAUDE.md")),
    ("Claude", COWORK, None),
]
CLAUDE_SPACES = [  # (workspace name, folder): chats run plain Claude Code; no Idli tools, no split (the split follows
    ("WhatsAppy", os.path.join(IDLI, "whatsappy")),  # the private model's provider, Paseo patch P15)
    ("Canvay", os.path.join(IDLI, "canvay")),
]
CLAUDE_PROVIDER = os.environ.get("IDLI_CLAUDE_PROVIDER", "claude")
LAYOUT += [(n, f, None) for n, f in CLAUDE_SPACES]
FOLDER = {n: f for n, f, _ in LAYOUT}
HEADING = {}  # the sidebar heading (project) when it differs from the workspace
OLD_NAMES = {"Idli": "Drivey"}  # workspace renamed 2026-11-13
OLD_MISSION_CONTROL = "What Idli has learned"  # its own workspace until 2026-11-12; now a tab in Start here
SITES = "google\nfiles\n"  # no free SQL (sheets): answers go through the form
# Each chat sees only the tools its job needs (a `cowork.tools` allow-list per folder; a small model chooses better
# from fewer). No Drive index or file search for now: Idli works from a link the person pastes.
TOOLSETS = {
    "Start here": ["setup_check", "show_skills", "skills_list", "skill_delete", "skill_share", "skill_import"],
    "Drivey": ["drive_fetch", "mini_open", "mini_ask", "start", "file_get", "gsheet_read", "file_open", "show_dashboard", "file_ask", "file_privacy", "claude_open", "teach_file", "teach_send",
             "working_copy", "working_copy_ready", "chart_request", "chart_show", "form_explain", "skill_import"],
}
START_PROVIDER = os.environ.get("IDLI_START_PROVIDER", "t4gc-cowork")
CHAT = "Logins"  # the setup chat in Start here (the workspace keeps the name Start here)
TABS = []  # the Drive tab opens only when the Logins check finds Google signed out (and closes once signed in)


def say(msg):
    print(("[dry-run] " if DRY else "") + msg, flush=True)


def paseo_bin():
    for p in (shutil.which("paseo"), os.path.expanduser("~/.local/bin/paseo"), "/usr/local/bin/paseo", "/usr/bin/paseo"):
        if p and os.path.exists(p):
            return p
    sys.exit("The paseo command was not found.")


ENV = {k: v for k, v in os.environ.items() if not k.startswith("PASEO_")}  # act as the user, not as an agent


def paseo(*args, parse=True, change=False):
    if change and DRY:
        say("would run: paseo " + " ".join(args))
        return None
    r = subprocess.run([paseo_bin(), *args] + (["--json"] if parse else []), capture_output=True, text=True,
                       timeout=120, env=ENV)
    if r.returncode:
        raise RuntimeError(f"paseo {' '.join(args)}: {(r.stderr or r.stdout).strip()[-300:]}")
    return json.loads(r.stdout) if parse and r.stdout.strip() else r.stdout


def same(a, b):
    """Same folder; the CLI sometimes prints paths with ~."""
    return bool(a) and os.path.realpath(os.path.expanduser(a)) == os.path.realpath(os.path.expanduser(b))


def folders():
    for name, path, instructions in LAYOUT:
        if name in dict(CLAUDE_SPACES):  # a plain folder: no Idli instructions, tools or sites
            if not os.path.isdir(path):
                say(f"create folder {path}")
                if not DRY:
                    os.makedirs(path, exist_ok=True)
            continue
        if path == COWORK or not instructions and os.path.isdir(path):
            continue
        if not os.path.isdir(path):
            say(f"create folder {path}")
            if not DRY:
                os.makedirs(path, exist_ok=True)
        dest = os.path.join(path, "CLAUDE.md")
        if instructions and (not os.path.exists(dest) or open(dest).read() != open(instructions).read()):
            say(f"write {dest}")
            if not DRY:
                shutil.copyfile(instructions, dest)
        tools = os.path.join(path, "cowork.tools")
        want = "\n".join(TOOLSETS.get(name, [])) + "\n"
        if name in TOOLSETS and (not os.path.exists(tools) or open(tools).read() != want):
            say(f"write {tools}")
            if not DRY:
                with open(tools, "w") as f:
                    f.write(want)
        sites = os.path.join(path, "cowork.sites")
        if not os.path.exists(sites) or open(sites).read() != SITES:
            say(f"write {sites}")
            if not DRY:
                with open(sites, "w") as f:
                    f.write(SITES)


def projects_and_workspaces():
    ids = {}
    for name, path, _ in LAYOUT:
        if name == "Claude" and split_mode():  # beside each Idli chat instead (retire_claude_workspace)
            continue
        proj = next((p for p in paseo("project", "ls") if same(p["path"], path)), None)
        if not proj:
            say(f"register project {path}")
            paseo("project", "create", path, parse=False, change=True)
            proj = next((p for p in (paseo("project", "ls") or []) if same(p["path"], path)), None) if not DRY else None
        heading = HEADING.get(name, name)
        if proj and proj["name"] != heading:
            say(f"name project '{proj['name']}' -> '{heading}'")
            paseo("project", "rename", proj["projectId"], heading, parse=False, change=True)
        wss = [w for w in paseo("workspace", "ls") if same(w["cwd"], path)]
        names = {n for n, _, _ in LAYOUT}
        ws = next((w for w in wss if w["name"] == name), None) or \
            next((w for w in wss if OLD_NAMES.get(w["name"]) == name), None) or \
            next((w for w in wss if w["name"] not in names), None)
        if not ws and proj:
            say(f"create workspace '{name}'")
            paseo("workspace", "create", "--isolation", "local", "--project", proj["projectId"], "--path", path,
                  "--title", name, parse=False, change=True)
            ws = next((w for w in (paseo("workspace", "ls") or []) if same(w["cwd"], path) and w["name"] == name),
                      None) if not DRY else None
        elif ws and ws["name"] != name:
            say(f"name workspace '{ws['name']}' -> '{name}'")
            paseo("workspace", "rename", ws["workspaceId"], name, parse=False, change=True)
        ids[name] = ws["workspaceId"] if ws else None
    return ids


def start_chat(ws_id):
    folder = FOLDER["Start here"]
    mine = [a for a in paseo("ls", "--global") if same(a.get("cwd") or "", folder)]
    agent = next((a for a in mine if a["name"] == CHAT), None)
    old = next((a for a in mine if a["name"] == "Start here"), None)  # its name until 2026-11-12
    if not agent and old:
        say(f"rename the Start here chat to '{CHAT}'")
        paseo("agent", "update", old["id"], "--name", CHAT, parse=False, change=True)
        agent = old
    if agent:
        say(f"{CHAT} chat exists")
        if (agent.get("labels") or {}).get("idli.role") != "setup":  # Start here never splits (Paseo patch P15)
            paseo("agent", "update", agent["id"], "--label", "idli.role=setup", parse=False, change=True)
        return agent["id"]
    say(f"create the {CHAT} chat (Idli greets the person)")
    if DRY or not ws_id:
        return None
    out = paseo("run", "--provider", START_PROVIDER, "--workspace", ws_id, "--mode", "bypassPermissions",
                "--thinking", "low",  # measured: low acts on "yes" in ~5 s vs ~10 s on high, same choices
                "--title", CHAT, "--label", "idli.role=setup", "--no-wait", "hello")
    return (out or {}).get("agentId")


def chat(ws_id, folder, title, prompt, provider=START_PROVIDER):
    """A chat that should always be there (made once; found again by its title). Returns its id."""
    old = next((a for a in paseo("ls", "--global") if a["name"] == title and same(a.get("cwd") or "", folder)), None)
    if old:
        say(f"'{title}' chat exists")
        return old["id"]
    say(f"create the '{title}' chat")
    if DRY or not ws_id:
        return None
    extra = ["--thinking", "low"] if provider == START_PROVIDER else []
    out = paseo("run", "--provider", provider, "--workspace", ws_id, "--mode", "bypassPermissions", *extra,
                "--title", title, "--no-wait", prompt)
    return (out or {}).get("agentId")


OPENED = os.path.join(IDLI, "config", "bootstrap-tabs.json")  # tabs opened once: Paseo lists only the tabs of the
#                                                              workspace on screen, so we can't look for them later


def opened(key, value=None):
    try:
        with open(OPENED) as f:
            seen = json.load(f)
    except (OSError, ValueError):
        seen = {}
    if value is None:
        return seen.get(key)
    seen[key] = value
    os.makedirs(os.path.dirname(OPENED), exist_ok=True)
    with open(OPENED, "w") as f:
        json.dump(seen, f)


def browser_as(agent_id):
    """Paseo's browser tools acting in agent_id's workspace, once the app's browser host is up (else None)."""
    sys.path.insert(0, COWORK)
    os.environ["PASEO_AGENT_ID"] = agent_id
    from lib import browser
    for attempt in range(20):  # the desktop app's browser host may still be starting
        try:
            browser.tabs()
            return browser
        except Exception:
            time.sleep(3)
    return None


def learned_tab(agent_id):
    """The Minis tab (the page of what Idli has learned) in Start here, at the form server's current address (the server is
    started here so the page is live as soon as the app opens)."""
    if not agent_id or DRY:
        say("would open the Minis tab")
        return
    py = os.path.join(COWORK, ".venv", "bin", "python")
    r = subprocess.run([py if os.path.exists(py) else sys.executable, "-c",
                        "import sys,json; sys.path.insert(0, sys.argv[1]); from lib import formserver as f; "
                        "print(json.dumps(f.ensure(sys.argv[2])))", COWORK, FOLDER["Start here"]],
                       capture_output=True, text=True, timeout=60, env=ENV)
    if r.returncode:
        say("the page server didn't start: " + r.stderr.strip()[-200:])
        return
    port, token = json.loads(r.stdout)
    url = f"http://dashboard.localhost:{port}/skills?t={token}"
    browser = browser_as(agent_id)
    if not browser:
        say("the app's browser isn't available; open Paseo and rerun to add the Minis tab")
        return
    if opened("learned@" + FOLDER["Start here"]) == url:
        say("Minis tab is open")
        return
    old = next((t for t in browser.tabs() if "/skills" in t["url"]), None)  # only if that workspace is on screen
    if old:
        say("point the Minis tab at the current server")
        browser.paseo("browser_navigate", browserId=old["id"], url=url)
    else:
        say("open the Minis tab")
        browser.paseo("browser_new_tab", url=url)
    opened("learned@" + FOLDER["Start here"], url)


def start_tabs(agent_id):
    """Drive and Gmail tabs in Start here, opened as the Start here chat (so they land in its workspace)."""
    if not agent_id or DRY:
        say("would open Drive and Gmail tabs in Start here")
        return
    browser = browser_as(agent_id)
    if not browser:
        say("the app's browser isn't available; open Paseo and rerun to add the Drive and Gmail tabs")
        return
    tabs = browser.tabs()
    for host in {urllib.parse.urlparse(u).hostname for u in TABS} | {"drive.google.com"}:
        keep = 1 if any(urllib.parse.urlparse(u).hostname == host for u in TABS) else 0
        dup = [t for t in tabs if urllib.parse.urlparse(t["url"]).hostname == host][keep:]
        for t in dup:
            say(f"close a {host} tab")
            browser.paseo("browser_close_tab", browserId=t["id"])
    have = {urllib.parse.urlparse(t["url"]).hostname for t in browser.tabs()}
    for url in TABS:
        key = url + "@" + FOLDER["Start here"]  # Start here moved folders (2026-11-10): open its tabs again there
        if urllib.parse.urlparse(url).hostname not in have and not opened(key):
            say(f"open tab {urllib.parse.urlparse(url).hostname}")
            browser.paseo("browser_new_tab", url=url)
        opened(key, True)


def retire_old_mission_control():
    """Until 2026-11-12 Mission control was its own heading and workspace ("What Idli has learned"); it is a tab in
    Start here now. Archive the old workspace (its chat goes with it)."""
    for w in paseo("workspace", "ls") or []:
        if w["name"] == OLD_MISSION_CONTROL:
            say(f"archive the old Mission control workspace ({w['cwd']})")
            paseo("workspace", "archive", w["workspaceId"], parse=False, change=True)
    for p in paseo("project", "ls") or []:  # and its heading in the sidebar
        if same(p["path"], os.path.join(IDLI, "start-here")):
            say("remove the old Mission control heading")
            paseo("project", "delete", p["projectId"], parse=False, change=True)


def split_mode():
    try:
        with open(os.path.join(IDLI, "config", "ui.json")) as f:
            return bool(json.load(f).get("split"))
    except (OSError, ValueError):
        return False


def one_idli_workspace():
    """Split mode: Idli's folder has one workspace, "Drivey". A second one on the same folder (Paseo's "New workspace")
    leaves teach_send unable to tell which one the chat is in (Paseo doesn't say), so Claude opened in the wrong one and
    its pairing hid it. Others are archived; their chats stay in History."""
    if not split_mode():
        return
    for w in paseo("workspace", "ls") or []:
        if same(w["cwd"], FOLDER["Drivey"]) and w["name"] != "Drivey":
            say(f"archive the extra workspace '{w['name']}' on Idli's folder (its chats stay in History)")
            paseo("workspace", "archive", w["workspaceId"], parse=False, change=True)


def retire_claude_workspace():
    """Split mode: every Idli chat has its own Claude chat beside it (Paseo patches P13-P15), so the separate Claude
    heading goes (website teaching, which needs it, is parked). Its chats stay in Paseo's history."""
    if not split_mode():
        return
    for p in paseo("project", "ls") or []:
        if same(p["path"], COWORK):
            say("remove the Claude heading (Claude now opens beside each Idli chat)")
            paseo("project", "delete", p["projectId"], parse=False, change=True)


def retire_old_start_here():
    """Until 2026-11-10 Start here shared Mission control's folder (and indexed the Drive). It has its own folder
    and heading now and only checks sign-ins: archive the old workspace (and its chat)."""
    for w in paseo("workspace", "ls") or []:
        if w["name"] == "Start here" and not same(w["cwd"], FOLDER["Start here"]):
            say(f"archive the old Start here workspace in {w['cwd']}")
            paseo("workspace", "archive", w["workspaceId"], parse=False, change=True)


def main():
    folders()
    ids = projects_and_workspaces()
    retire_old_start_here()
    retire_old_mission_control()
    retire_claude_workspace()
    one_idli_workspace()
    agent = start_chat(ids.get("Start here"))
    learned_tab(agent)  # Minis: a tab in Start here, next to the chat
    start_tabs(agent)
    chat(ids.get("Drivey"), FOLDER["Drivey"], "New chat", "hi")  # Drivey keeps one waiting from then on
    for name, folder in CLAUDE_SPACES:  # one Claude chat waiting in each
        chat(ids.get(name), folder, "New chat", "hi", provider=CLAUDE_PROVIDER)
    say("done. Heading order: Start here, Drivey, WhatsAppy, Canvay (drag once until Paseo patch P2).")


if __name__ == "__main__":
    main()
