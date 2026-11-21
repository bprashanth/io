#!/usr/bin/env python3
"""Install Idli (alpha) on a computer that already has the Idli build of Paseo installed and opened once.

  python3 install-idli.py                       install or update
  python3 install-idli.py --token muse.json     also connect the private model (silo Access token file from the owner)
  python3 install-idli.py --dry-run             say what it would do

Linux and macOS. Windows is not supported in the alpha (Idli's launchers are shell scripts): see
docs/idli-alpha-release.md.

It:
  1. checks what Idli needs: Python 3.10+, Claude Code (`claude`), Node and npm, and Paseo's daemon
     (open the app once so ~/.paseo/config.json exists);
  2. copies this kit's cowork/ to ~/idli-insights/app/cowork (a stable place: Paseo's providers point at it).
     An update replaces the code and keeps .venv;
  3. writes the private model's Claude settings (~/idli-insights/config/claude-t4gc/settings.json) from the template
     if missing, and with --token points them at silo (desktop/muse-connect.py; the secret is never printed);
  4. runs desktop/setup-laptop.py (providers, .venv, the dashboard-links plugin) and desktop/idli-bootstrap.py
     (Start here, Drivey, Builder) from the installed copy.
It never writes credentials of its own. Google sign-in needs Idli's OAuth client file from the owner, out of band.
"""
import os
import shutil
import subprocess
import sys

DRY = "--dry-run" in sys.argv
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the cowork/ folder this script sits in
HOME = os.path.expanduser("~")
IDLI = os.environ.get("IDLI_HOME", os.path.join(HOME, "idli-insights"))
DEST = os.path.join(IDLI, "app", "cowork")
CONFIG = os.path.join(IDLI, "config")
T4GC = os.path.join(CONFIG, "claude-t4gc", "settings.json")
SKIP = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", "tests", "teach", "HOME_SHOTS", ".idli",
                              "node_modules", "*.pyc", "cowork.mcp.json")


def say(msg):
    print(("[dry-run] " if DRY else "") + msg, flush=True)


def fail(msg):
    sys.exit("Idli can't install yet: " + msg)


def paseo_cli():
    """Paseo's command-line tool: on PATH, or inside the installed app."""
    found = shutil.which("paseo")
    if found:
        return found
    for p in ("/Applications/Paseo.app/Contents/Resources/bin/paseo",
              os.path.join(HOME, "Applications/Paseo.app/Contents/Resources/bin/paseo"),
              "/opt/Paseo/resources/bin/paseo",
              os.path.join(HOME, "Applications/Paseo/resources/bin/paseo")):
        if os.path.exists(p):
            return p
    return None


def template():
    for p in (os.path.join(KIT, "desktop", "claude-t4gc-settings.json"),
              os.path.join(os.path.dirname(KIT), "laptop", "claude-t4gc-settings.json")):
        if os.path.exists(p):
            return p
    return None


def check():
    if sys.platform.startswith("win"):
        fail("Windows is not supported in the alpha. Use Linux or macOS (docs/idli-alpha-release.md).")
    if sys.version_info < (3, 10):
        fail(f"Python 3.10 or newer is needed (this is {sys.version.split()[0]}).")
    missing = [n for n in ("claude", "node", "npm") if not shutil.which(n)]
    if missing:
        fail("install " + ", ".join(missing) + " first. Claude Code: https://claude.com/claude-code ; "
             "Node 20+: https://nodejs.org")
    cli = paseo_cli()
    if not cli:
        fail("Paseo's command-line tool wasn't found. Install the Idli build of Paseo and open it once.")
    if not os.path.exists(os.path.join(HOME, ".paseo", "config.json")):
        fail("open the Paseo app once (it creates ~/.paseo/config.json), then run this again.")
    return cli


def copy_kit():
    if os.path.realpath(KIT) == os.path.realpath(DEST):
        say(f"running from {DEST}: nothing to copy")
        return
    say(f"copy {KIT} -> {DEST}")
    if DRY:
        return
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    venv = os.path.join(DEST, ".venv")
    kept = None
    if os.path.isdir(venv):  # keep the Python environment across updates
        kept = DEST + ".venv-keep"
        shutil.rmtree(kept, ignore_errors=True)
        os.replace(venv, kept)
    shutil.rmtree(DEST, ignore_errors=True)
    shutil.copytree(KIT, DEST, ignore=SKIP)
    if kept:
        os.replace(kept, venv)
    tpl = template()
    if tpl and not os.path.exists(os.path.join(DEST, "desktop", "claude-t4gc-settings.json")):
        shutil.copy(tpl, os.path.join(DEST, "desktop", "claude-t4gc-settings.json"))


def model_settings(token):
    if not os.path.exists(T4GC):
        tpl = template()
        if not tpl:
            fail("the private model's settings template is missing from this kit.")
        say(f"write {T4GC} from the template")
        if not DRY:
            os.makedirs(os.path.dirname(T4GC), exist_ok=True)
            os.chmod(CONFIG, 0o700)
            shutil.copy(tpl, T4GC)
            os.chmod(T4GC, 0o600)
    else:
        say(f"{T4GC} exists: kept")
    if token:
        run([sys.executable, os.path.join(DEST, "desktop", "muse-connect.py"), token])


def run(cmd, env=None):
    say("$ " + " ".join(cmd))
    if not DRY:
        subprocess.run(cmd, cwd=DEST, check=True, env=env)


def main():
    cli = check()
    token = None
    if "--token" in sys.argv:
        i = sys.argv.index("--token")
        if i + 1 >= len(sys.argv):
            fail("--token needs the token file the owner gave you.")
        token = os.path.abspath(os.path.expanduser(sys.argv[i + 1]))
    copy_kit()
    model_settings(token)
    env = dict(os.environ, PATH=os.path.dirname(cli) + os.pathsep + os.environ.get("PATH", ""))
    run([sys.executable, os.path.join(DEST, "desktop", "setup-laptop.py")] + (["--dry-run"] if DRY else []), env)
    run([sys.executable, os.path.join(DEST, "desktop", "idli-bootstrap.py")] + (["--dry-run"] if DRY else []), env)
    print("\nIdli is installed. Quit and reopen Paseo once. Then, in Start here:\n"
          "  - Logins: sign in to Google (Idli's OAuth client file comes from the owner);\n"
          "  - Drivey: @ a Drive file and ask a question.\n"
          + ("" if token else "The private model isn't connected yet: run this again with --token <file>.\n"))


if __name__ == "__main__":
    main()
