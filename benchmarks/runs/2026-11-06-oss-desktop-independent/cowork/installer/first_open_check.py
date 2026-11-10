"""CI: open the installed Idli the way a person does, after setup, and check what the first run built.

  <bundled python> first_open_check.py OUT.json

Run after `idli_app.py --smoke` (which saved a Muse code pointing at a stand-in Muse). Marks setup done, runs
idli_app.py (no arguments: starts Paseo's window, waits for its daemon, runs the bootstrap), then asks Paseo for
the workspaces and chats. The chats can't answer in CI (no real Muse); what's checked is that they exist.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import idli_app as a  # noqa: E402

out = sys.argv[1]
a.write_private(a.STATE, {"done": True, "skip_claude": True, "at": time.time()})
t = time.time()
r = subprocess.run([sys.executable, os.path.join(HERE, "idli_app.py")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
rep = {"open_s": round(time.time() - t, 1), "exit": r.returncode, "tail": (r.stdout + r.stderr)[-3000:]}
_, cli = a.paseo_app_paths()
ws = json.loads(a.paseo(cli, "workspace", "ls", "--json").stdout or "[]")
ag = json.loads(a.paseo(cli, "ls", "--global", "--json").stdout or "[]")
rep["workspaces"] = sorted({(w.get("project"), w.get("name")) for w in ws})
rep["chats"] = sorted(x.get("name") for x in ag)
need_ws = {("Mission control", "Start here"), ("Mission control", "What Idli has learned"), ("Idli", "Idli"),
           ("Claude", "Claude")}
need_chats = {"Start here", "What Idli has learned", "New chat"}
rep["missing_workspaces"] = sorted(map(list, need_ws - set(rep["workspaces"])))
rep["missing_chats"] = sorted(need_chats - set(rep["chats"]))
rep["ok"] = r.returncode == 0 and not rep["missing_workspaces"] and not rep["missing_chats"]
rep["workspaces"] = [list(x) for x in rep["workspaces"]]
rep["browser_tabs"] = "isn't available" not in rep["tail"]  # the app's browser answered the bootstrap
time.sleep(20)  # let Paseo's window draw, then keep a picture of the screen
shot = os.path.join(os.path.dirname(os.path.abspath(out)), "first-open.png")
try:
    if a.WIN:
        ps = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
              "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
              "$i=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
              "[System.Drawing.Graphics]::FromImage($i).CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
              f"$i.Save('{shot}')")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=60)
    elif a.MAC:
        subprocess.run(["screencapture", "-x", shot], timeout=60)
    else:
        subprocess.run(["import", "-window", "root", shot], timeout=60)
except (OSError, subprocess.SubprocessError) as e:
    rep["screenshot_error"] = str(e)
rep["screenshot"] = os.path.exists(shot)
with open(out, "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=2)
print(json.dumps({k: v for k, v in rep.items() if k != "tail"}, indent=1))
a.paseo(cli, "daemon", "stop", timeout=120)
sys.exit(0 if rep["ok"] else 1)
