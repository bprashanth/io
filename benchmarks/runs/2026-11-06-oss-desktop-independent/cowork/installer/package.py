#!/usr/bin/env python3
"""Wrap a payload (installer/build_payload.py) into the file a person downloads and opens.

  python3 installer/package.py linux PAYLOAD VERSION OUTDIR   -> idli_<V>_amd64.deb   (dpkg-deb)
  python3 installer/package.py mac   PAYLOAD VERSION OUTDIR   -> Idli-<V>-arm64.dmg   (hdiutil; unsigned, ad-hoc)
  python3 installer/package.py win   PAYLOAD VERSION OUTDIR   -> Idli-Setup-<V>.exe   (Inno Setup's iscc)

Each one installs per platform convention and adds two launchers: "Idli" (open Idli) and "Idli setup" (change the
Muse code, connect Claude). Nothing is signed: this is for a handful of testers (see installer/TESTERS.md).
"""
import os
import plistlib
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, **kw):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def linux(payload, v, out):
    root = os.path.join(out, "_deb")
    shutil.rmtree(root, ignore_errors=True)
    opt = os.path.join(root, "opt", "idli")
    shutil.copytree(payload, opt, symlinks=True)
    bindir = os.path.join(root, "usr", "bin")
    os.makedirs(bindir)
    for name, extra in (("idli", ""), ("idli-setup", " --setup")):
        p = os.path.join(bindir, name)
        with open(p, "w") as f:
            f.write(f'#!/bin/sh\nexec /opt/idli/python/bin/python3 /opt/idli/cowork/installer/idli_app.py{extra} "$@"\n')
        os.chmod(p, 0o755)
    apps = os.path.join(root, "usr", "share", "applications")
    os.makedirs(apps)
    for name, label, cmd in (("idli", "Idli", "idli"), ("idli-setup", "Idli setup", "idli-setup")):
        with open(os.path.join(apps, name + ".desktop"), "w") as f:
            f.write(f"[Desktop Entry]\nType=Application\nName={label}\nComment=Your Drive assistant\n"
                    f"Exec={cmd}\nIcon=idli\nTerminal=false\nCategories=Office;\n")
    icons = os.path.join(root, "usr", "share", "icons", "hicolor", "512x512", "apps")
    os.makedirs(icons)
    shutil.copy2(os.path.join(payload, "idli.png"), os.path.join(icons, "idli.png"))
    deb = os.path.join(root, "DEBIAN")
    os.makedirs(deb)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(opt) for f in fs
               if not os.path.islink(os.path.join(d, f))) // 1024
    with open(os.path.join(deb, "control"), "w") as f:
        f.write(f"Package: idli\nVersion: {v}\nArchitecture: amd64\nMaintainer: Idli <noreply@idli.cc>\n"
                f"Installed-Size: {size}\nSection: utils\nPriority: optional\n"
                "Depends: libnss3, libgbm1, libasound2 | libasound2t64, libgtk-3-0 | libgtk-3-0t64, curl\n"
                "Description: Idli, a Drive assistant on a private model\n"
                " Bundles Paseo, a standalone Python and Idli's tools.\n")
    with open(os.path.join(deb, "postinst"), "w") as f:  # Electron's sandbox helper must be setuid root,
        f.write("#!/bin/sh\nset -e\n"                     # as Paseo's own .deb does
                "if [ -f /opt/idli/paseo/chrome-sandbox ]; then\n"
                "  chown root:root /opt/idli/paseo/chrome-sandbox\n  chmod 4755 /opt/idli/paseo/chrome-sandbox\nfi\n"
                "command -v update-desktop-database >/dev/null && update-desktop-database -q || true\n")
    os.chmod(os.path.join(deb, "postinst"), 0o755)
    target = os.path.join(out, f"idli_{v}_amd64.deb")
    run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", root, target])
    shutil.rmtree(root)
    return target


def mac(payload, v, out, arch="arm64"):
    app = os.path.join(out, "_dmg", "Idli.app")
    shutil.rmtree(os.path.dirname(app), ignore_errors=True)
    res = os.path.join(app, "Contents", "Resources")
    shutil.copytree(payload, res, symlinks=True)
    macos = os.path.join(app, "Contents", "MacOS")
    os.makedirs(macos)
    with open(os.path.join(macos, "Idli"), "w") as f:  # a double-click with Option held opens setup again
        f.write('#!/bin/sh\nR="$(cd "$(dirname "$0")/../Resources" && pwd)"\n'
                'exec "$R/python/bin/python3" "$R/cowork/installer/idli_app.py" "$@"\n')
    os.chmod(os.path.join(macos, "Idli"), 0o755)
    run(["sips", "-s", "format", "icns", os.path.join(payload, "idli.png"), "--out", os.path.join(res, "idli.icns")])
    with open(os.path.join(app, "Contents", "Info.plist"), "wb") as f:
        plistlib.dump({"CFBundleName": "Idli", "CFBundleDisplayName": "Idli", "CFBundleIdentifier": "cc.idli.app",
                       "CFBundleExecutable": "Idli", "CFBundleIconFile": "idli.icns", "CFBundlePackageType": "APPL",
                       "CFBundleShortVersionString": v, "CFBundleVersion": v, "LSMinimumSystemVersion": "12.0",
                       "LSUIElement": True}, f)  # no Dock icon for the launcher itself: Paseo is the window
    run(["codesign", "--force", "--deep", "--sign", "-", app])  # ad-hoc: Apple silicon refuses unsigned code
    setup = os.path.join(os.path.dirname(app), "Idli setup.command")
    with open(setup, "w") as f:
        f.write('#!/bin/sh\nexec "/Applications/Idli.app/Contents/MacOS/Idli" --setup\n')
    os.chmod(setup, 0o755)
    os.symlink("/Applications", os.path.join(os.path.dirname(app), "Applications"))
    target = os.path.join(out, f"Idli-{v}-{arch}.dmg")
    run(["hdiutil", "create", "-volname", "Idli", "-srcfolder", os.path.dirname(app), "-ov", "-format", "UDZO",
         target])
    shutil.rmtree(os.path.dirname(app))
    return target


def win(payload, v, out):
    iss = os.path.join(out, "idli.iss")
    payload = os.path.abspath(payload)
    app_py = '"""{app}\\cowork\\installer\\idli_app.py"""'      # Inno: "" inside a quoted value is one "
    setup_py = '"""{app}\\cowork\\installer\\idli_app.py"" --setup"'
    pyw = '"{app}\\python\\pythonw.exe"'
    lines = [
        "[Setup]",
        "AppId={{6C2B6D1E-1D2A-4F0B-9B7E-1D11CC000001}",
        "AppName=Idli",
        f"AppVersion={v}",
        "AppPublisher=Idli",
        "DefaultDirName={localappdata}\\Programs\\Idli",
        "PrivilegesRequired=lowest",
        "DisableProgramGroupPage=yes",
        "DisableDirPage=yes",
        f"OutputDir={os.path.abspath(out)}",
        f"OutputBaseFilename=Idli-Setup-{v}",
        "Compression=lzma2/fast",
        "UninstallDisplayIcon={app}\\python\\python.exe",
        "WizardStyle=modern",
        "",
        "[Files]",
        f'Source: "{payload}\\*"; DestDir: "{{app}}"; Flags: recursesubdirs createallsubdirs ignoreversion',
        "",
        "[Icons]",
        f'Name: "{{userprograms}}\\Idli"; Filename: {pyw}; Parameters: {app_py}; WorkingDir: "{{app}}"',
        f'Name: "{{userprograms}}\\Idli setup"; Filename: {pyw}; Parameters: {setup_py}; WorkingDir: "{{app}}"',
        f'Name: "{{userdesktop}}\\Idli"; Filename: {pyw}; Parameters: {app_py}; WorkingDir: "{{app}}"',
        "",
        "[Run]",
        f'Filename: {pyw}; Parameters: {app_py}; Description: "Open Idli"; Flags: nowait postinstall skipifsilent',
        "",
    ]
    with open(iss, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    run([iscc, iss])
    return os.path.join(out, f"Idli-Setup-{v}.exe")


if __name__ == "__main__":
    kind, payload, v, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    print({"linux": linux, "mac": mac, "win": win}[kind](payload, v, out))
