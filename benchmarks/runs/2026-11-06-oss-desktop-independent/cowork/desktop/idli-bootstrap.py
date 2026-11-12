#!/usr/bin/env python3
"""Idli first-run bootstrap: make a Paseo install look the way Idli should on first open.
Safe to rerun: it only adds what's missing.

  Start here       its own folder (~/idli-insights/setup), first in the sidebar
     Start here       the setup chat (sign-in checks; also answers "what has Idli learned")
     Mission control  a tab: the page listing the files Idli has learned (grows as Claude teaches it)
     Drive            a tab for signing in to Google
  Idli         the private folder (~/idli-insights/cowork-real): where the work happens; a "New chat" is always
     Idli      waiting there on its first card (clean up a file / analyse a file)
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
    ("Idli", os.path.join(IDLI, "cowork-real"), os.path.join(COWORK, "idli", "CLAUDE.md")),
    ("Claude", COWORK, None),
]
FOLDER = {n: f for n, f, _ in LAYOUT}
HEADING = {}  # the sidebar heading (project) when it differs from the workspace
OLD_MISSION_CONTROL = "What Idli has learned"  # its own workspace until 2026-11-12; now a tab in Start here
SITES = "google\nfiles\n"  # no free SQL (sheets): answers go through the form
# Each chat sees only the tools its job needs (a `cowork.tools` allow-list per folder; a small model chooses better
# from fewer). No Drive index or file search for now: Idli works from a link the person pastes.
TOOLSETS = {
    "Start here": ["setup_check", "show_skills", "skills_list", "skill_delete"],
    "Idli": ["start", "file_get", "gsheet_read", "file_open", "show_dashboard", "file_ask", "teach_file", "teach_send",
             "working_copy", "working_copy_ready", "chart_request", "chart_show", "form_explain"],
}
START_PROVIDER = os.environ.get("IDLI_START_PROVIDER", "t4gc-cowork")
TABS = ["https://drive.google.com/drive/my-drive"]  # Gmail later; Drive is all the first run needs


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
        ws = next((w for w in wss if w["name"] == name), None) or next((w for w in wss if w["name"] not in names), None)
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
    agent = next((a for a in paseo("ls", "--global") if a["name"] == "Start here" and same(a.get("cwd") or "", folder)), None)
    if agent:
        say("Start here chat exists")
        return agent["id"]
    say("create the Start here chat (Idli greets the person)")
    if DRY or not ws_id:
        return None
    out = paseo("run", "--provider", START_PROVIDER, "--workspace", ws_id, "--mode", "bypassPermissions",
                "--thinking", "low",  # measured: low acts on "yes" in ~5 s vs ~10 s on high, same choices
                "--title", "Start here", "--no-wait", "hello")
    return (out or {}).get("agentId")


def chat(ws_id, folder, title, prompt):
    """A chat that should always be there (made once; found again by its title). Returns its id."""
    old = next((a for a in paseo("ls", "--global") if a["name"] == title and same(a.get("cwd") or "", folder)), None)
    if old:
        say(f"'{title}' chat exists")
        return old["id"]
    say(f"create the '{title}' chat")
    if DRY or not ws_id:
        return None
    out = paseo("run", "--provider", START_PROVIDER, "--workspace", ws_id, "--mode", "bypassPermissions",
                "--thinking", "low", "--title", title, "--no-wait", prompt)
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
    """The Mission control tab (the page of what Idli has learned) in Start here, at the form server's current address (the server is
    started here so the page is live as soon as the app opens)."""
    if not agent_id or DRY:
        say("would open the Mission control tab")
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
        say("the app's browser isn't available; open Paseo and rerun to add the Mission control tab")
        return
    if opened("learned@" + FOLDER["Start here"]) == url:
        say("Mission control tab is open")
        return
    old = next((t for t in browser.tabs() if "/skills" in t["url"]), None)  # only if that workspace is on screen
    if old:
        say("point the Mission control tab at the current server")
        browser.paseo("browser_navigate", browserId=old["id"], url=url)
    else:
        say("open the Mission control tab")
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
    for host in {urllib.parse.urlparse(u).hostname for u in TABS}:  # reruns opened duplicates: keep one per site
        dup = [t for t in tabs if urllib.parse.urlparse(t["url"]).hostname == host][1:]
        for t in dup:
            say(f"close a duplicate {host} tab")
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
    agent = start_chat(ids.get("Start here"))
    learned_tab(agent)  # Mission control: a tab in Start here, next to the chat
    start_tabs(agent)
    chat(ids.get("Idli"), FOLDER["Idli"], "New chat", "hi")  # Idli keeps one waiting from then on
    say("done. Heading order: Start here, Idli, Claude (drag once until Paseo patch P2).")


if __name__ == "__main__":
    main()
