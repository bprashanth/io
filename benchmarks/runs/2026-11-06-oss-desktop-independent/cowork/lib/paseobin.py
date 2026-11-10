"""Find the paseo command on this computer (Linux, macOS, Windows).

The Idli installer records where it put Paseo in ~/idli-insights/config/paseo-bin (one line: the CLI's path), because
a fresh install has no `paseo` on PATH: the CLI ships inside the app (resources/bin/paseo, paseo.cmd on Windows).
Order: $IDLI_PASEO_BIN, that file, PATH, then the usual install places.
"""
import os
import shutil
import sys

IDLI = os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights")
RECORD = os.path.join(IDLI, "config", "paseo-bin")


def candidates():
    home = os.path.expanduser("~")
    out = [os.environ.get("IDLI_PASEO_BIN")]
    try:
        with open(RECORD, encoding="utf-8") as f:
            out.append(f.read().strip())
    except OSError:
        pass
    out.append(shutil.which("paseo"))
    if sys.platform == "win32":
        la = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        out += [os.path.join(la, "Programs", "Paseo", "resources", "bin", "paseo.cmd"),
                os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Paseo", "resources", "bin",
                             "paseo.cmd")]
    elif sys.platform == "darwin":
        out += [os.path.join(home, "Applications", "Paseo.app", "Contents", "Resources", "bin", "paseo"),
                "/Applications/Paseo.app/Contents/Resources/bin/paseo"]
    else:
        out += [os.path.join(IDLI, "app", "paseo", "resources", "bin", "paseo"), "/opt/Paseo/resources/bin/paseo"]
    out += [os.path.join(home, ".local", "bin", "paseo"), "/usr/local/bin/paseo", "/usr/bin/paseo"]
    return [p for p in out if p]


def find():
    """The paseo CLI's path, or None."""
    return next((p for p in candidates() if os.path.isfile(p)), None)


def record(path):
    os.makedirs(os.path.dirname(RECORD), exist_ok=True)
    with open(RECORD, "w", encoding="utf-8") as f:
        f.write(path)
