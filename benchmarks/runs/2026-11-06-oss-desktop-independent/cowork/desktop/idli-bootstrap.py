#!/usr/bin/env python3
"""Idli first-run bootstrap: make a Paseo install look the way Idli insights should on first open.
Safe to rerun: it only adds what's missing.

  Start here            its own folder (~/idli-insights/start-here): the setup chat (tab 0) with Idli's
     Start here         greeting, plus a Drive tab and a Gmail tab for signing in
  Idli insights         the private folder (~/idli-insights/cowork-real): where the work happens
     Idli insights
  Teacher - Claude      this cowork/ folder: Claude teaches Idli a file, from fake data only
     Teacher - Claude

Runs on the machine with Paseo, after the daemon is up (desktop/idli-launch.sh does that). The heading order
needs Paseo patch P2 (todos/idli-insights/paseo_patches.md); until then the person drags them once.
Providers (Idli 30B, Idli 9B, Teacher) come from desktop/setup-laptop.py.

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
LAYOUT = [  # (heading and workspace name, folder, instructions copied to <folder>/CLAUDE.md)
    ("Start here", os.path.join(IDLI, "start-here"), os.path.join(COWORK, "idli", "START-HERE.md")),
    ("Idli insights", os.path.join(IDLI, "cowork-real"), os.path.join(COWORK, "idli", "CLAUDE.md")),
    ("Teacher - Claude", COWORK, None),
]
SITES = "google\nsheets\nfiles\n"
START_PROVIDER = os.environ.get("IDLI_START_PROVIDER", "t4gc-cowork")
TABS = ["https://drive.google.com/drive/my-drive", "https://mail.google.com/mail/u/0/#inbox"]


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
        if path == COWORK:
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
        sites = os.path.join(path, "cowork.sites")
        if not os.path.exists(sites):
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
        if proj and proj["name"] != name:
            say(f"name project '{proj['name']}' -> '{name}'")
            paseo("project", "rename", proj["projectId"], name, parse=False, change=True)
        wss = [w for w in paseo("workspace", "ls") if same(w["cwd"], path)]
        ws = next((w for w in wss if w["name"] == name), wss[0] if wss else None)
        if not ws and proj:
            say(f"create workspace '{name}'")
            paseo("workspace", "create", "--isolation", "local", "--project", proj["projectId"], "--path", path,
                  "--title", name, parse=False, change=True)
            ws = next((w for w in (paseo("workspace", "ls") or []) if same(w["cwd"], path)), None) if not DRY else None
        elif ws and ws["name"] != name:
            say(f"name workspace '{ws['name']}' -> '{name}'")
            paseo("workspace", "rename", ws["workspaceId"], name, parse=False, change=True)
        ids[name] = ws["workspaceId"] if ws else None
    return ids


def start_chat(ws_id):
    folder = LAYOUT[0][1]
    agent = next((a for a in paseo("ls", "--global") if a["name"] == "Start here" and same(a.get("cwd") or "", folder)), None)
    if agent:
        say("Start here chat exists")
        return agent["id"]
    say("create the Start here chat (Idli greets the person)")
    if DRY or not ws_id:
        return None
    out = paseo("run", "--provider", START_PROVIDER, "--workspace", ws_id, "--mode", "bypassPermissions",
                "--title", "Start here", "--no-wait", "start")
    return (out or {}).get("agentId")


def start_tabs(agent_id):
    """Drive and Gmail tabs in Start here, opened as the Start here chat (so they land in its workspace)."""
    if not agent_id or DRY:
        say("would open Drive and Gmail tabs in Start here")
        return
    sys.path.insert(0, COWORK)
    os.environ["PASEO_AGENT_ID"] = agent_id
    from lib import browser
    for attempt in range(20):  # the desktop app's browser host may still be starting
        try:
            have = {urllib.parse.urlparse(t["url"]).hostname for t in browser.tabs()}
            break
        except Exception:
            time.sleep(3)
    else:
        say("the app's browser isn't available; open Paseo and rerun to add the Drive and Gmail tabs")
        return
    for url in TABS:
        if urllib.parse.urlparse(url).hostname not in have:
            say(f"open tab {urllib.parse.urlparse(url).hostname}")
            browser.paseo("browser_new_tab", url=url)


def main():
    folders()
    ids = projects_and_workspaces()
    agent = start_chat(ids.get("Start here"))
    start_tabs(agent)
    say("done. Heading order: Start here, Idli insights, Teacher - Claude (drag once until Paseo patch P2).")


if __name__ == "__main__":
    main()
