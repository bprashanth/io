"""Idli: what the installed app runs when the person opens it (Linux, macOS, Windows).

The installer puts a self-contained Python, Idli's tools (this cowork/ tree) and Paseo next to each other:

    <APP>/python/            standalone Python with duckdb, pandas, openpyxl, matplotlib
    <APP>/cowork/            Idli's tools; this file is <APP>/cowork/installer/idli_app.py
    <APP>/paseo/             Paseo: an unpacked app (Linux), Paseo.zip (macOS) or Paseo-Setup.exe (Windows)

Opening Idli:
  1. copies the tools to ~/idli-insights/app/cowork (Claude teaches Idli there, so it must be writable; taught
     files in file-skills/ and teach/ are kept across updates);
  2. finds or installs Paseo, and the Claude Code CLI (Idli's private model runs through it too; signing in to
     Anthropic is optional and only needed for teaching);
  3. writes Paseo's providers and Idli's settings;
  4. the first time (or with --setup): a setup page in the browser: paste the Muse code, connect Claude
     (optional); Google sign-in happens in Idli's Drive tab;
  5. starts Paseo (no remote-debugging port) and runs the first-run bootstrap (desktop/idli-bootstrap.py).

  idli_app.py                 open Idli
  idli_app.py --setup         show the setup page again (change the Muse code, connect Claude)
  idli_app.py --smoke OUT     installer self-test for CI: no network secrets, writes a JSON report to OUT
"""
import base64
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # <APP>/cowork (read-only in an install)
APP = os.path.dirname(SRC)
IDLI = os.environ.get("IDLI_HOME") or os.path.join(os.path.expanduser("~"), "idli-insights")
COWORK = os.path.join(IDLI, "app", "cowork")                              # the writable copy everything uses
CONFIG = os.path.join(IDLI, "config")
LOG = os.path.join(CONFIG, "idli-app.log")
STATE = os.path.join(CONFIG, "setup.json")
WIN, MAC = sys.platform == "win32", sys.platform == "darwin"
HOME = os.path.expanduser("~")
PASEO_CONFIG = os.path.join(os.environ.get("PASEO_HOME") or os.path.join(HOME, ".paseo"), "config.json")
T4GC_CLAUDE = os.path.join(CONFIG, "claude-t4gc")
KEEP = {"file-skills", "teach", "charts", "cowork.mcp.json", ".venv", "__pycache__"}  # never overwritten by an update
CODE_PREFIX = "idli1."
NO_WINDOW = 0x08000000 if WIN else 0  # CREATE_NO_WINDOW: no console flashes on Windows


def log(*a):
    os.makedirs(CONFIG, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if sys.stdout and not (sys.executable or "").lower().endswith("pythonw.exe"):
        try:
            print(line, flush=True)
        except (OSError, ValueError):
            pass


def write_private(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(path + ".tmp", path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def version():
    try:
        with open(os.path.join(APP, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "dev"


# ---------------------------------------------------------------- 1. the tools, in a writable place
def sync_cowork():
    """Copy <APP>/cowork to ~/idli-insights/app/cowork when the installed version changed. Keeps what Idli learned."""
    stamp = os.path.join(COWORK, ".idli-version")
    have = open(stamp).read().strip() if os.path.exists(stamp) else None
    if have == version() and os.path.exists(os.path.join(COWORK, "cowork_mcp.py")) and version() != "dev":
        return False
    log(f"copy Idli's tools {have} -> {version()} into {COWORK}")
    os.makedirs(COWORK, exist_ok=True)
    for name in os.listdir(SRC):
        if name in KEEP:
            continue
        s, d = os.path.join(SRC, name), os.path.join(COWORK, name)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(s, d)
    for d in ("file-skills", os.path.join("teach", "inbox")):
        os.makedirs(os.path.join(COWORK, d), exist_ok=True)
    with open(stamp, "w") as f:
        f.write(version())
    return True


# ---------------------------------------------------------------- 2. Paseo
def paseo_app_paths():
    """(GUI executable, CLI) of an installed Paseo, or (None, None)."""
    la = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
    if WIN:
        roots = [os.path.join(la, "Programs", "Paseo"), os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                                                                     "Paseo")]
        for r in roots:
            if os.path.exists(os.path.join(r, "Paseo.exe")):
                return os.path.join(r, "Paseo.exe"), os.path.join(r, "resources", "bin", "paseo.cmd")
    elif MAC:
        for r in (os.path.join(HOME, "Applications", "Paseo.app"), "/Applications/Paseo.app"):
            if os.path.exists(r):
                return r, os.path.join(r, "Contents", "Resources", "bin", "paseo")
    else:
        for r in (os.path.join(APP, "paseo"), os.path.join(IDLI, "app", "paseo"), "/opt/Paseo"):
            if os.path.exists(os.path.join(r, "paseo")) or os.path.exists(os.path.join(r, "Paseo")):
                return os.path.join(r, "paseo" if os.path.exists(os.path.join(r, "paseo")) else "Paseo"), \
                    os.path.join(r, "resources", "bin", "paseo")
    return None, None


def install_paseo():
    """Install the Paseo the installer carries (per user, no admin)."""
    bundle = os.path.join(APP, "paseo")
    if WIN:
        setup = next((os.path.join(bundle, f) for f in os.listdir(bundle) if f.lower().endswith(".exe")), None)
        if not setup:
            raise RuntimeError("Paseo's installer is missing from this Idli install.")
        log("install Paseo (silent, for this user)")
        subprocess.run([setup, "/S"], check=True, timeout=600, creationflags=NO_WINDOW)
        for _ in range(120):  # the NSIS installer may return before its files land
            if paseo_app_paths()[0]:
                break
            time.sleep(1)
    elif MAC:
        z = next((os.path.join(bundle, f) for f in os.listdir(bundle) if f.endswith(".zip")), None)
        if not z:
            raise RuntimeError("Paseo is missing from this Idli install.")
        dest = os.path.join(HOME, "Applications")
        os.makedirs(dest, exist_ok=True)
        log(f"install Paseo into {dest}")
        subprocess.run(["ditto", "-x", "-k", z, dest], check=True, timeout=600)
    exe, cli = paseo_app_paths()
    if not exe:
        raise RuntimeError("Paseo did not install.")
    return exe, cli


def ensure_paseo():
    exe, cli = paseo_app_paths()
    if not exe:
        exe, cli = install_paseo()
    sys.path.insert(0, COWORK)
    from lib import paseobin
    paseobin.record(cli)
    os.environ["IDLI_PASEO_BIN"] = cli
    return exe, cli


def paseo(cli, *args, timeout=60):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PASEO_") or k == "PASEO_HOME"}
    return subprocess.run([cli, *args], capture_output=True, text=True, timeout=timeout, env=env,
                          creationflags=NO_WINDOW)


def daemon_up(cli):
    try:
        return paseo(cli, "status", "--json", timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def start_paseo(exe, cli):
    if daemon_up(cli):
        log("Paseo is running")
    else:
        log(f"start Paseo: {exe}")
        if MAC:
            subprocess.Popen(["open", exe])
        else:
            subprocess.Popen([exe], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=not WIN, creationflags=0x00000008 if WIN else 0)  # DETACHED_PROCESS
    for _ in range(90):
        if daemon_up(cli):
            return True
        time.sleep(1)
    log("Paseo's daemon did not answer in 90 s")
    return False


# ---------------------------------------------------------------- 2b. Claude Code
def claude_path():
    for p in (shutil.which("claude"), os.path.join(HOME, ".local", "bin", "claude.exe" if WIN else "claude"),
              os.path.join(HOME, ".claude", "local", "claude")):
        if p and os.path.isfile(p):
            return p
    return None


def install_claude():
    """Anthropic's official installer (per user, into ~/.local/bin). Idli never ships Claude Code itself."""
    log("install Claude Code with Anthropic's installer")
    if WIN:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
               "irm https://claude.ai/install.ps1 | iex"]
    else:
        cmd = ["/bin/bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, creationflags=NO_WINDOW)
    log("claude installer exit", r.returncode, (r.stdout + r.stderr)[-400:].replace("\n", " | "))
    return claude_path()


def claude_signed_in(claude):
    if not claude:
        return False
    try:
        r = subprocess.run([claude, "auth", "status"], capture_output=True, text=True, timeout=30,
                           creationflags=NO_WINDOW)
        return r.returncode == 0 and json.loads(r.stdout or "{}").get("loggedIn") is True
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------- 3. settings
def muse_access():
    a = read_json(os.path.join(CONFIG, "muse-access.json"))
    return a if a and a.get("url") and a.get("client_id") and a.get("client_secret") else None


def write_settings(claude):
    py = sys.executable
    if py.lower().endswith("pythonw.exe"):  # the MCP server talks over stdio: needs the console python
        py = py[:-len("pythonw.exe")] + "python.exe"
    mcp = {"mcpServers": {"cowork": {"type": "stdio", "command": py,
                                     "args": ["-I", os.path.join(COWORK, "cowork_mcp.py")],
                                     "env": {"COWORK_LOG": os.path.join(CONFIG, "cowork.log")}}}}
    with open(os.path.join(COWORK, "cowork.mcp.json"), "w", encoding="utf-8") as f:
        json.dump(mcp, f, indent=1)
    # Idli 30B: the Claude Code CLI pointed at Muse, with Idli's tools only (desktop/setup-laptop.py)
    template = read_json(os.path.join(SRC, "installer", "claude-t4gc-settings.json"), {"env": {}})
    settings = read_json(os.path.join(T4GC_CLAUDE, "settings.json")) or template
    settings.setdefault("env", {}).update({k: v for k, v in template.get("env", {}).items()
                                           if k not in ("ANTHROPIC_BASE_URL",)})
    a = muse_access()
    if a:
        settings["env"]["ANTHROPIC_BASE_URL"] = a["url"].rstrip("/")
        settings["env"]["ANTHROPIC_CUSTOM_HEADERS"] = (f"CF-Access-Client-Id: {a['client_id']}\n"
                                                       f"CF-Access-Client-Secret: {a['client_secret']}")
    write_private(os.path.join(T4GC_CLAUDE, "settings.json"), settings)
    sys.path.insert(0, COWORK)
    import importlib.util
    spec = importlib.util.spec_from_file_location("setup_laptop", os.path.join(COWORK, "desktop", "setup-laptop.py"))
    sl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sl)
    cowork = dict(sl.COWORK_PROVIDER)
    cowork["command"] = [claude or "claude", "--mcp-config", os.path.join(COWORK, "cowork.mcp.json")]
    cowork["env"] = {"CLAUDE_CONFIG_DIR": T4GC_CLAUDE, "ENABLE_TOOL_SEARCH": "false"}
    cfg = read_json(PASEO_CONFIG, {}) or {}
    cfg.setdefault("daemon", {}).setdefault("browserTools", {})["enabled"] = True
    providers = cfg.setdefault("agents", {}).setdefault("providers", {})
    providers["t4gc-cowork"] = cowork
    providers["diy-claude"] = dict(sl.DIY_PROVIDER)
    os.makedirs(os.path.dirname(PASEO_CONFIG), exist_ok=True)
    if os.path.exists(PASEO_CONFIG):
        shutil.copy(PASEO_CONFIG, PASEO_CONFIG + ".bak-idli")
    with open(PASEO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    log("settings written (providers t4gc-cowork, diy-claude)")


# ---------------------------------------------------------------- 4. the Muse code
def decode_code(code):
    """'idli1.<base64url JSON {u, i, s}>' -> {url, client_id, client_secret}. Raises ValueError with a plain reason."""
    code = "".join((code or "").split())
    if not code.startswith(CODE_PREFIX):
        raise ValueError("That isn't an Idli code: it should start with 'idli1.'")
    body = code[len(CODE_PREFIX):]
    try:
        d = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("That code is incomplete: copy the whole line, from 'idli1.' to the end.")
    a = {"url": str(d.get("u") or "").rstrip("/"), "client_id": str(d.get("i") or ""),
         "client_secret": str(d.get("s") or "")}
    if not a["url"].startswith(("https://", "http://127.0.0.1", "http://localhost")) or not a["client_id"] \
            or not a["client_secret"]:
        raise ValueError("That code is incomplete: copy the whole line, from 'idli1.' to the end.")
    return a


def encode_code(url, client_id, client_secret):
    raw = json.dumps({"u": url, "i": client_id, "s": client_secret}, separators=(",", ":")).encode()
    return CODE_PREFIX + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def check_muse(a, timeout=20):
    """Ask Muse for its models with these credentials. Returns the model ids; raises ValueError with a plain reason."""
    req = urllib.request.Request(a["url"] + "/v1/models", headers={
        "CF-Access-Client-Id": a["client_id"], "CF-Access-Client-Secret": a["client_secret"], "User-Agent": "idli"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ids = [m.get("id") for m in json.load(r).get("data", []) if m.get("id")]
    except urllib.error.HTTPError as e:
        raise ValueError(f"Idli's model said no to this code (HTTP {e.code}). Ask for a new code.")
    except (OSError, ValueError) as e:
        raise ValueError(f"Can't reach Idli's model at {a['url']} ({type(e).__name__}). Check the internet "
                         "connection and try again.")
    if not ids:
        raise ValueError("Idli's model answered but listed no models. Ask whoever runs it.")
    return ids


def save_code(code):
    a = decode_code(code)
    ids = check_muse(a)
    write_private(os.path.join(CONFIG, "muse-access.json"), a)
    return a, ids


# ---------------------------------------------------------------- 5. the setup page
class Setup:
    """State behind setup.html; one instance per launch."""

    def __init__(self):
        self.token = secrets.token_urlsafe(16)
        self.done = threading.Event()
        self.claude = claude_path()
        self.signed_in = claude_signed_in(self.claude)
        self.busy = None          # "installing" | "signing in"
        self.error = None
        self.login = None         # the `claude auth login` process
        self.login_url = None
        self.skip_claude = False

    def state(self):
        a = muse_access()
        return {"muse": {"ok": bool(a), "url": a["url"] if a else None},
                "claude": {"installed": bool(self.claude), "signed_in": self.signed_in, "busy": self.busy,
                           "login_url": self.login_url, "error": self.error, "skipped": self.skip_claude},
                "version": version()}

    def install(self):
        def run():
            self.busy, self.error = "installing", None
            try:
                self.claude = install_claude()
                if not self.claude:
                    self.error = "Claude Code didn't install. Check the internet connection and try again."
            except Exception as e:  # noqa: BLE001 - shown to the person
                self.error = f"Claude Code didn't install: {e}"
            self.busy = None
        threading.Thread(target=run, daemon=True).start()

    def sign_in(self):
        if not self.claude:
            self.error = "Install Claude Code first."
            return
        self.busy, self.error, self.login_url = "signing in", None, None
        self.login = subprocess.Popen([self.claude, "auth", "login"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, creationflags=NO_WINDOW)

        def read():
            for line in self.login.stdout:
                log("claude login:", line.strip()[:120])
                if "https://" in line and not self.login_url:
                    self.login_url = line[line.index("https://"):].split()[0]
            self.login.wait()
            self.signed_in = claude_signed_in(self.claude)
            self.busy = None
            if not self.signed_in:
                self.error = "Not signed in yet. Try again, or skip: Idli works without Claude."

        threading.Thread(target=read, daemon=True).start()

    def paste_login_code(self, code):
        if self.login and self.login.poll() is None:
            self.login.stdin.write(code.strip() + "\n")
            self.login.stdin.flush()


def make_handler(setup):
    page = os.path.join(SRC, "installer", "setup.html")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _ok(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return secrets.compare_digest((q.get("t") or [""])[0], setup.token)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if not self._ok():
                return self._send(403, {"error": "open the setup page from the Idli app"})
            if u.path == "/":
                with open(page, encoding="utf-8") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/state":
                return self._send(200, setup.state())
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if not self._ok():
                return self._send(403, {"error": "forbidden"})
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if u.path == "/api/muse":
                try:
                    a, ids = save_code(body.get("code", ""))
                    return self._send(200, {"ok": True, "url": a["url"], "models": ids})
                except ValueError as e:
                    return self._send(400, {"ok": False, "error": str(e)})
            if u.path == "/api/claude/install":
                setup.install()
                return self._send(200, {"ok": True})
            if u.path == "/api/claude/login":
                setup.sign_in()
                return self._send(200, {"ok": True})
            if u.path == "/api/claude/code":
                setup.paste_login_code(body.get("code", ""))
                return self._send(200, {"ok": True})
            if u.path == "/api/finish":
                setup.skip_claude = bool(body.get("skip_claude"))
                write_private(STATE, {"done": True, "skip_claude": setup.skip_claude, "at": time.time()})
                setup.done.set()
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})

    return H


def serve_setup(setup, port=0):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(setup))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/?t={setup.token}"


def run_setup():
    setup = Setup()
    httpd, url = serve_setup(setup)
    log("setup page:", url.split("?")[0])
    webbrowser.open(url)
    setup.done.wait()
    time.sleep(1)  # let the page show "opening Idli"
    httpd.shutdown()
    return setup


# ---------------------------------------------------------------- open Idli
def bootstrap():
    r = subprocess.run([sys.executable if not sys.executable.lower().endswith("pythonw.exe")
                        else sys.executable[:-len("pythonw.exe")] + "python.exe",
                        os.path.join(COWORK, "desktop", "idli-bootstrap.py")],
                       capture_output=True, text=True, timeout=900, creationflags=NO_WINDOW)
    log("bootstrap:", (r.stdout + r.stderr)[-1500:].replace("\n", " | "))
    return r.returncode == 0


def main():
    if MAC:  # the person approved Idli.app once; don't make them approve every file inside it
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", os.path.dirname(os.path.dirname(APP))],
                       capture_output=True)
    sync_cowork()
    exe, cli = ensure_paseo()
    claude = claude_path() or install_claude()
    write_settings(claude)
    if "--setup" in sys.argv or not (read_json(STATE) or {}).get("done") or not muse_access():
        run_setup()
        write_settings(claude_path())
    if not muse_access():
        log("no Muse code: opening Paseo without Idli's chats")
        start_paseo(exe, cli)
        return
    if start_paseo(exe, cli):
        bootstrap()


# ---------------------------------------------------------------- CI self-test
def smoke(out):
    """Everything that can be proven without a person or a secret. Writes {check: {ok, detail}} to out."""
    rep = {}

    def check(name, fn):
        t = time.time()
        try:
            detail = fn()
            rep[name] = {"ok": True, "detail": detail, "s": round(time.time() - t, 1)}
        except Exception as e:  # noqa: BLE001
            rep[name] = {"ok": False, "detail": f"{type(e).__name__}: {e}"[:800], "s": round(time.time() - t, 1)}
        log("smoke", name, "OK" if rep[name]["ok"] else "FAIL", str(rep[name]["detail"])[:300])

    def imports():
        import duckdb, matplotlib, numpy, openpyxl, pandas  # noqa: E401,F401
        con = duckdb.connect()
        assert con.execute("select 41 + 1").fetchone()[0] == 42
        return {"python": sys.version.split()[0], "pandas": pandas.__version__, "duckdb": duckdb.__version__,
                "matplotlib": matplotlib.__version__, "openpyxl": openpyxl.__version__}

    def tools_copy():
        sync_cowork()
        assert os.path.exists(os.path.join(COWORK, "cowork_mcp.py"))
        return COWORK

    def mcp():
        p = subprocess.Popen([sys.executable, "-I", os.path.join(COWORK, "cowork_mcp.py")], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=IDLI,
                             env={**os.environ, "COWORK_SITES": "google,files"}, creationflags=NO_WINDOW)
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
        out_, err = p.communicate("\n".join(json.dumps(m) for m in msgs) + "\n", timeout=120)
        resp = [json.loads(l) for l in out_.splitlines() if l.strip().startswith("{")]
        tools = next((r["result"]["tools"] for r in resp if r.get("id") == 2), None)
        if not tools:
            raise RuntimeError(f"no tools/list answer; stderr: {err[-600:]}")
        names = sorted(t["name"] for t in tools)
        for need in ("start", "file_get", "file_ask", "drive_find"):
            assert need in names, f"{need} missing from {names}"
        return {"tools": len(names)}

    def muse_code():
        bad = []
        for c in ("hello", "idli1.%%%", "idli1." + base64.urlsafe_b64encode(b'{"u":"ftp://x"}').decode()):
            try:
                decode_code(c)
                bad.append(c)
            except ValueError:
                pass
        assert not bad, f"accepted bad codes: {bad}"
        try:  # well formed, nobody listening
            check_muse(decode_code(encode_code("http://127.0.0.1:9", "id.access", "s")), timeout=5)
            raise AssertionError("an unreachable Muse was accepted")
        except ValueError as e:
            unreachable = str(e)

        class Fake(BaseHTTPRequestHandler):  # a stand-in Muse that checks the two Access headers
            def log_message(self, *a):
                pass

            def do_GET(self):
                good = self.headers.get("CF-Access-Client-Id") == "ci.access" and \
                    self.headers.get("CF-Access-Client-Secret") == "ci-secret"
                body = json.dumps({"data": [{"id": "muse-test"}]} if good else {"error": "no"}).encode()
                self.send_response(200 if good else 403)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        u = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            check_muse(decode_code(encode_code(u, "ci.access", "wrong")))
            raise AssertionError("a wrong secret was accepted")
        except ValueError as e:
            refused = str(e)
        a, ids = save_code(encode_code(u, "ci.access", "ci-secret"))
        saved = read_json(os.path.join(CONFIG, "muse-access.json"))
        assert saved["client_id"] == "ci.access" and ids == ["muse-test"]
        srv.shutdown()
        return {"unreachable": unreachable[:80], "wrong_secret": refused[:80], "good": ids}

    def setup_page():
        s = Setup()
        httpd, url = serve_setup(s)
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                html = r.read().decode()
            assert "Idli" in html and "idli1." in html
            st_url = url.replace("/?t=", "/api/state?t=")
            with urllib.request.urlopen(st_url, timeout=10) as r:
                st = json.load(r)
            try:
                urllib.request.urlopen(url.split("?")[0] + "api/state?t=wrong", timeout=10)
                raise AssertionError("served without the token")
            except urllib.error.HTTPError as e:
                assert e.code == 403
            req = urllib.request.Request(url.replace("/?t=", "/api/muse?t="), json.dumps({"code": "nope"}).encode(),
                                         {"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=10)
                raise AssertionError("bad code accepted by the page")
            except urllib.error.HTTPError as e:
                assert e.code == 400
            return {"state": st}
        finally:
            httpd.shutdown()

    def paseo_install():
        exe, cli = ensure_paseo()
        v = paseo(cli, "--version", timeout=120)
        assert v.returncode == 0, v.stderr[-400:]
        return {"exe": exe, "cli": cli, "version": v.stdout.strip()[-60:]}

    def claude_cli():
        c = claude_path() or install_claude()
        assert c, "Claude Code didn't install"
        return {"claude": c, "signed_in": claude_signed_in(c)}

    def settings():
        write_settings(claude_path())
        cfg = read_json(PASEO_CONFIG)
        assert "t4gc-cowork" in cfg["agents"]["providers"]
        s = read_json(os.path.join(T4GC_CLAUDE, "settings.json"))
        assert s["env"]["ANTHROPIC_BASE_URL"].startswith("http://127.0.0.1:")  # the fake Muse from muse_code
        assert "CF-Access-Client-Id: ci.access" in s["env"]["ANTHROPIC_CUSTOM_HEADERS"]
        return {"providers": sorted(cfg["agents"]["providers"])}

    def daemon():
        _, cli = paseo_app_paths()
        r = paseo(cli, "daemon", "start", timeout=180)
        for _ in range(90):
            if daemon_up(cli):
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"daemon not up: {(r.stdout + r.stderr)[-600:]}")
        pl = paseo(cli, "provider", "ls", "--json", timeout=60)
        assert "t4gc-cowork" in pl.stdout, f"provider ls: {(pl.stdout + pl.stderr)[-600:]}"
        return {"providers_seen": "t4gc-cowork"}

    def bootstrap_dry():
        r = subprocess.run([sys.executable, os.path.join(COWORK, "desktop", "idli-bootstrap.py"), "--dry-run"],
                           capture_output=True, text=True, timeout=300, creationflags=NO_WINDOW,
                           env={**os.environ, "IDLI_PASEO_BIN": paseo_app_paths()[1]})
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
        return (r.stdout + r.stderr)[-800:]

    def daemon_stop():
        _, cli = paseo_app_paths()
        r = paseo(cli, "daemon", "stop", timeout=120)
        return (r.stdout + r.stderr).strip()[-200:]

    for name, fn in (("python_and_libraries", imports), ("tools_copied", tools_copy), ("mcp_tools", mcp),
                     ("muse_code", muse_code), ("setup_page", setup_page), ("paseo_installed", paseo_install),
                     ("claude_cli", claude_cli), ("settings", settings), ("paseo_daemon", daemon),
                     ("bootstrap_dry_run", bootstrap_dry), ("daemon_stop", daemon_stop)):
        check(name, fn)
    rep["_summary"] = {"ok": all(v["ok"] for v in rep.values()), "platform": sys.platform, "version": version()}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    return rep["_summary"]["ok"]


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        sys.exit(0 if smoke(sys.argv[sys.argv.index("--smoke") + 1]) else 1)
    try:
        main()
    except Exception as e:  # noqa: BLE001 - the person sees the log path
        log("FAILED:", f"{type(e).__name__}: {e}")
        raise
