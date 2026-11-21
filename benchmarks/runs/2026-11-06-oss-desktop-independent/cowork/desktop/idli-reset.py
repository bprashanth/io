#!/usr/bin/env python3
"""Put Idli back to a new user's first open, keeping the Google sign-in (for trying the first run again).

Stops an index build, deletes the Drive index, closes Idli's own tabs (drive-index progress, file peeks), archives
every chat, then runs the bootstrap, which makes a fresh Start here chat with the greeting. The Drive tab and the
browser's Google sign-in stay. Runs on the machine with Paseo.

  python3 desktop/idli-reset.py
"""
import json
import os
import signal
import subprocess
import sys

COWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, COWORK)
IDLI = os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights")
CONFIG = os.path.join(IDLI, "config")
OURS = ("drive-index.localhost", "/preview", "drive.google.com/file/d/")  # tabs Idli opened, not the person's


def cli(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PASEO_")}
    r = subprocess.run(["paseo", *args], capture_output=True, text=True, timeout=90, env=env)
    return r.stdout


def stop_builds():
    for pid in os.listdir("/proc"):  # not pkill -f: it can match this script's own shell
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if "driveindex.py build" in cmd:
            os.kill(int(pid), signal.SIGTERM)
            print("stopped index build", pid)


def main():
    stop_builds()
    agents = json.loads(cli("ls", "--global", "--json") or "[]")
    from lib import browser
    for a in agents:
        os.environ["PASEO_AGENT_ID"] = a["id"]  # browser tools act in this chat's workspace
        try:
            for t in browser.tabs():
                if any(s in t["url"] for s in OURS):
                    browser.paseo("browser_close_tab", browserId=t["id"])
                    print("closed tab", t["url"][:60])
        except Exception as e:
            print("tabs:", type(e).__name__, e)
        cli("stop", a["id"])
        cli("archive", a["id"])
        print("archived", a.get("name"))
    os.environ.pop("PASEO_AGENT_ID", None)
    for f in ("drive-index.duckdb", "drive-index.duckdb.wal", "drive-index.json", "drive-index.dryrun",
              "drive-index.duckdb.hold", "drive-index.json.hold", "peek-tabs.json"):
        p = os.path.join(CONFIG, f)
        if os.path.exists(p):
            os.remove(p)
            print("deleted", f)
    subprocess.run([sys.executable, os.path.join(COWORK, "desktop", "idli-bootstrap.py")], check=False)


if __name__ == "__main__":
    main()
