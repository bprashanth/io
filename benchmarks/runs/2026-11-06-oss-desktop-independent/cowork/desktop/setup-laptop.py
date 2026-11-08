#!/usr/bin/env python3
"""Recreate the co-work POC on a laptop that already has Paseo 0.15.2, Claude Code and the T4GC
Claude config in ~/idli-insights/config/claude-t4gc (docs/driving-desktop.md, "~/idli-insights").
Idempotent; prints what it did.

  python3 desktop/setup-laptop.py            # run from the cowork/ folder
  python3 desktop/setup-laptop.py --dry-run

It:
  1. writes cowork.mcp.json with this checkout's absolute paths;
  2. creates .venv (duckdb, pandas, openpyxl) with uv or python3 -m venv;
  3. merges into ~/.paseo/config.json (backup first): daemon.browserTools.enabled, pluginsEnabled,
     providers t4gc-cowork + diy-claude;
  4. creates ~/idli-insights/cowork-real (stand-in "real" workbook + cowork.sites) for the co-work workspace.
     ~/idli-insights (override with IDLI_HOME) holds every co-work workspace folder: the private-data side;
  5. builds and installs the dashboard-links Paseo plugin (npm install, typecheck, paseo plugin install);
  6. reloads Paseo. Plugin install needs a daemon restart; the script tells you.
It never writes credentials. ~/idli-insights/config/accounts.json (test account + fixtures) is yours to create.
"""
import json
import os
import shutil
import subprocess
import sys
import time

DRY = "--dry-run" in sys.argv
COWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
CONFIG = os.path.join(HOME, ".paseo", "config.json")
IDLI = os.environ.get("IDLI_HOME", os.path.join(HOME, "idli-insights"))
T4GC_CLAUDE = os.path.join(IDLI, "config", "claude-t4gc")
CLAUDE = shutil.which("claude") or os.path.join(HOME, ".local", "bin", "claude")

COWORK_PROVIDER = {
    "extends": "claude",
    "label": "Co-work · T4GC (private data, no shell)",
    "command": [CLAUDE, "--mcp-config", os.path.join(COWORK, "cowork.mcp.json")],
    "env": {"CLAUDE_CONFIG_DIR": T4GC_CLAUDE, "ENABLE_TOOL_SEARCH": "false"},
    "models": [{"id": "muse-glimmer-30b", "label": "T4GC model (Idli)", "isDefault": True}],
    "disallowedTools": ["Bash", "BashOutput", "KillShell", "Read", "Write", "Edit", "MultiEdit", "NotebookEdit",
                        "Glob", "Grep", "WebSearch", "WebFetch", "Task", "Agent", "TodoWrite", "Skill", "mcp__paseo",
                        # unused built-ins: ~60k chars of tool schema = ~11k prompt tokens on Muse
                        "Workflow", "SendMessage", "ScheduleWakeup", "CronCreate", "CronDelete", "CronList",
                        "EnterPlanMode", "ExitPlanMode", "EnterWorktree", "ExitWorktree", "ReportFindings", "ListAgents",
                        # co-work is read-only: find, suggest, download. Drafting mail is a write.
                        "mcp__cowork__gmail_draft_reply", "mcp__cowork__sheet_query", "mcp__cowork__sheet_profile"],
}
DIY_PROVIDER = {"extends": "claude", "label": "DIY · Claude (builds co-work tools, test accounts only)"}


def step(msg):
    print(("[dry-run] " if DRY else "") + msg)


def run(cmd, cwd=None):
    step("$ " + " ".join(cmd))
    if not DRY:
        subprocess.run(cmd, cwd=cwd, check=True)


def main():
    if not os.path.exists(os.path.join(T4GC_CLAUDE, "settings.json")):
        sys.exit(f"{T4GC_CLAUDE}/settings.json missing: create it first (docs/driving-desktop.md, '~/idli-insights').")
    py = os.path.join(COWORK, ".venv", "bin", "python")

    mcp = {"mcpServers": {"cowork": {"type": "stdio", "command": py,
                                     "args": ["-I", os.path.join(COWORK, "cowork_mcp.py")],
                                     "env": {"COWORK_LOG": "/tmp/cowork.log"}}}}
    step("write cowork.mcp.json")
    if not DRY:
        with open(os.path.join(COWORK, "cowork.mcp.json"), "w") as f:
            json.dump(mcp, f, indent=1)
            f.write("\n")

    if not os.path.exists(py):
        if shutil.which("uv"):
            run(["uv", "venv", "-q", ".venv", "--python", "3.12"], cwd=COWORK)
            run(["uv", "pip", "install", "-q", "--python", py, "duckdb", "pandas", "openpyxl"], cwd=COWORK)
        else:
            run([sys.executable, "-m", "venv", ".venv"], cwd=COWORK)
            run([py, "-m", "pip", "install", "-q", "duckdb", "pandas", "openpyxl"], cwd=COWORK)
    else:
        step(".venv exists")

    with open(CONFIG) as f:
        cfg = json.load(f)
    cfg.setdefault("daemon", {}).setdefault("browserTools", {})["enabled"] = True
    cfg["pluginsEnabled"] = True
    providers = cfg.setdefault("agents", {}).setdefault("providers", {})
    providers["t4gc-cowork"] = COWORK_PROVIDER
    providers["diy-claude"] = DIY_PROVIDER
    step(f"merge providers t4gc-cowork, diy-claude, browserTools, pluginsEnabled into {CONFIG}")
    if not DRY:
        shutil.copy(CONFIG, f"{CONFIG}.bak-{int(time.time())}")
        with open(CONFIG, "w") as f:
            json.dump(cfg, f, indent=2)

    real = os.path.join(IDLI, "cowork-real")
    if not os.path.exists(os.path.join(real, "field_visits_q3.xlsx")):
        step(f"create {real}")
        if not DRY:
            os.makedirs(real, exist_ok=True)
        run([py, "make_sample_sheets.py", "real", os.path.join(real, "field_visits_q3.xlsx")], cwd=COWORK)
    if not DRY:
        with open(os.path.join(real, "cowork.sites"), "w") as f:
            f.write("google\nsheets\nfiles\n")
        shutil.copy(os.path.join(COWORK, "idli", "CLAUDE.md"), os.path.join(real, "CLAUDE.md"))
    if not os.path.exists(os.path.join(COWORK, "sites", "sheets", "testdata", "field_visits_mock.xlsx")):
        run([py, "make_sample_sheets.py", "test", "sites/sheets/testdata/field_visits_mock.xlsx"], cwd=COWORK)

    plugin = os.path.join(COWORK, "dashboard-links")
    run(["npm", "install", "--silent"], cwd=plugin)
    run(["npx", "tsc", "--noEmit"], cwd=plugin)
    installed = subprocess.run(["paseo", "plugin", "ls"], capture_output=True, text=True).stdout
    if "dashboard-links" not in installed:
        run(["paseo", "plugin", "install", plugin])
    else:
        step("dashboard-links plugin already installed")
    run(["paseo", "reload", "--json"])
    print("\nDone. If the plugin is new, restart the Paseo app once (Quit, then start it with "
          "--remote-debugging-port=9333). Then: create ~/idli-insights/config/accounts.json, open a workspace on "
          f"{real} and one on {COWORK}, and run desktop/laptop-up.sh.")


if __name__ == "__main__":
    main()
