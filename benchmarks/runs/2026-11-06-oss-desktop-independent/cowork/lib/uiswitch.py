"""Bring a chat or a tab to the front in Paseo, after the person said yes on a card.

Two ways, by what is being shown:
- a chat (an agent), in any workspace: Paseo's own deep link, paseo://h/<server>/agent/<agent>, handed to the
  running app by launching it again (Electron passes it to the open window and quits). Works in a normal install.
- a browser tab (the drive-index progress page): Paseo has no link for those, so this clicks the tab through the
  app's DevTools port, which only our development launcher opens (idli-launch.sh, port 9333). Without the port it
  says so and the caller tells the person which tab to click. Shipping fix: Paseo patch P7.

  python -m lib.uiswitch agent <agent-id>          (also used by the Claude workspace at the end of teaching)
  python -m lib.uiswitch tab drive-index.localhost
"""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request

APP = os.environ.get("PASEO_APP") or next((p for p in ("/opt/Paseo/Paseo", shutil.which("Paseo") or "") if p and os.path.exists(p)), None)
CDP_PORT = int(os.environ.get("IDLI_CDP_PORT", "9333"))


def _env():
    # the CLI as the person, not as the calling agent (agent-scoped CLI calls are limited to their workspace)
    return {k: v for k, v in os.environ.items() if not k.startswith("PASEO_") or k == "PASEO_HOME"}


def _cli():
    return shutil.which("paseo") or os.path.expanduser("~/.local/bin/paseo")


def server_id():
    r = subprocess.run([_cli(), "status", "--json"], capture_output=True, text=True, timeout=30, env=_env())
    return json.loads(r.stdout)["serverId"]


def full_agent_id(agent):
    """Agent ids may come shortened (first 7-8 chars); the deep link needs the full one."""
    if len(agent) >= 32:
        return agent
    r = subprocess.run([_cli(), "ls", "--global", "--json"], capture_output=True, text=True, timeout=30, env=_env())
    return next((a["id"] for a in json.loads(r.stdout or "[]") if a["id"].startswith(agent)), agent)


def split_enabled():
    """Idli and Claude side by side in one window (Paseo patches P13/P14 installed): ~/idli-insights/config/ui.json
    {"split": true}, written when the patched app UI is installed. Off, everything works as before (two workspaces)."""
    try:
        with open(os.path.join(os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights"), "config",
                               "ui.json")) as f:
            return bool(json.load(f).get("split"))
    except (OSError, ValueError):
        return False


def show_agent(agent, side=None):
    """Switch Paseo to this chat, in whatever workspace it lives. side ("left"/"right", split mode only): put the
    chat in that pane of a side-by-side workspace and focus it (P13: the side rides on the agent id, "<id>~right")."""
    if not APP:
        return {"ok": False, "why": "Paseo app not found"}
    try:
        link = f"paseo://h/{server_id()}/agent/{full_agent_id(agent)}" + (
            f"~{side}" if side in ("left", "right") and split_enabled() else "")
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "why": f"could not read Paseo's server id: {type(e).__name__}"}
    # Navigate the running window through DevTools when it's on (the app is started with --remote-debugging-port).
    # Handing the link to a second launch of the app was unreliable (2026-11-14: the window didn't move, and a
    # second launch can be left running as a second window).
    try:
        page = next(t for t in _targets() if t.get("type") == "page" and str(t.get("url", "")).startswith("paseo://app"))
        route = link.replace("paseo://h/", "paseo://app/h/", 1)
        _ws_eval(page["webSocketDebuggerUrl"], f"location.href = {json.dumps(route)}; true")
        return {"ok": True, "via": "devtools"}
    except (OSError, ValueError, KeyError, StopIteration, ConnectionError, TimeoutError):
        pass
    p = subprocess.Popen([APP, link], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        p.wait(timeout=15)  # the second launch hands the link over and quits
    except subprocess.TimeoutExpired:
        pass
    return {"ok": True}


def show_terminal(workspace_id, terminal_id, side="right", focus=True):
    """Open a workspace terminal's tab and put it on one side with focus (Paseo UI patch P17, build idli8+): the
    person's Claude CLI goes on the right of Drivey. Needs DevTools (the app started with --remote-debugging-port)."""
    try:
        page = next(t for t in _targets() if t.get("type") == "page" and str(t.get("url", "")).startswith("paseo://app"))
        srv = server_id()
        ws = page["webSocketDebuggerUrl"]
        if _ws_eval(ws, "typeof window.__idliPlaceTab") != "function":  # older UI: open it by URL, then place
            route = f"paseo://app/h/{srv}/workspace/{workspace_id}?open=" + urllib.parse.quote(f"terminal:{terminal_id}")
            _ws_eval(ws, f"location.href = {json.dumps(route)}; true")
            time.sleep(4)
            page = next(t for t in _targets() if t.get("type") == "page" and str(t.get("url", "")).startswith("paseo://app"))
        # P17 opens the terminal's tab itself when it has none, so no reload is needed
        got = _ws_eval(page["webSocketDebuggerUrl"],
                       "typeof window.__idliPlaceTab === 'function' ? window.__idliPlaceTab(" + json.dumps(
                           {"serverId": srv, "workspaceId": workspace_id, "kind": "terminal", "id": terminal_id,
                            "side": side, "focus": focus}) + ") : 'no-p17'")
        return {"ok": got is True, "why": None if got is True else "this Paseo UI has no P17 (install idli8)"}
    except (OSError, ValueError, KeyError, StopIteration, ConnectionError, TimeoutError,
            subprocess.SubprocessError) as e:
        return {"ok": False, "why": type(e).__name__}


def show_alone(workspace_id, terminal_id, wait=4):
    """Go to a workspace and show one terminal there, in a single pane (a new team's Builder chat). Paseo opens a
    terminal made from the CLI with ?open=terminal:<id>; P17's __idliPlaceTab then focuses it without splitting."""
    try:
        page = next(t for t in _targets() if t.get("type") == "page" and str(t.get("url", "")).startswith("paseo://app"))
        srv = server_id()
        route = f"paseo://app/h/{srv}/workspace/{workspace_id}?open=" + urllib.parse.quote(f"terminal:{terminal_id}")
        _ws_eval(page["webSocketDebuggerUrl"], f"location.href = {json.dumps(route)}; true")
        time.sleep(wait)
        page = next(t for t in _targets() if t.get("type") == "page" and str(t.get("url", "")).startswith("paseo://app"))
        got = _ws_eval(page["webSocketDebuggerUrl"],
                       "typeof window.__idliPlaceTab === 'function' ? window.__idliPlaceTab(" + json.dumps(
                           {"serverId": srv, "workspaceId": workspace_id, "kind": "terminal", "id": terminal_id,
                            "side": "left", "focus": True}) + ") : 'no-p17'")
        return {"ok": got in (True, "no-p17"), "why": None if got is True else got}
    except (OSError, ValueError, KeyError, StopIteration, ConnectionError, TimeoutError,
            subprocess.SubprocessError) as e:
        return {"ok": False, "why": type(e).__name__}


def open_url(workspace_id, url, side='right', focus=True):
    """Open a browser tab in the specified workspace using the P21 UI bridge."""
    if side not in ('left', 'right') or not isinstance(workspace_id, str) or not workspace_id:
        return {'ok': False, 'why': 'Open this page from a Drivey workspace.'}
    if os.environ.get('IDLI_TEST_OPEN_LOG'):  # tests without Paseo: record the page; a headless browser opens it
        with open(os.environ['IDLI_TEST_OPEN_LOG'], 'a') as f:
            f.write(url + '\n')
        return {'ok': True, 'why': None}
    try:
        page = next(t for t in _targets() if t.get('type') == 'page' and str(t.get('url', '')).startswith('paseo://app'))
        args = {'serverId': server_id(), 'workspaceId': workspace_id, 'url': url, 'side': side, 'focus': bool(focus)}
        got = _ws_eval(page['webSocketDebuggerUrl'],
                       "(async () => { if (typeof window.__idliOpenTab !== 'function') return false; "
                       "return (await window.__idliOpenTab(" + json.dumps(args) + ")) !== false; })()")
        return {'ok': got is True, 'why': None if got is True else 'Choose the page link to open it. The Paseo UI needs P21.'}
    except (OSError, ValueError, KeyError, StopIteration, ConnectionError, TimeoutError, subprocess.SubprocessError):
        return {'ok': False, 'why': 'Choose the page link to open it. Paseo could not open a tab.'}


# ---- a minimal DevTools (CDP) client over a websocket, standard library only
class Cdp:
    def __init__(self, ws_url, timeout=10, sock=None):
        # sock: an already connected socket (lib/chromectl.py reaches a profile's DevTools through a unix socket)
        rest = ws_url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.timeout, self.n, self.buf, self.events = timeout, 0, b"", []
        self.s = sock or socket.create_connection((host, int(port)), timeout=timeout)
        self.s.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.s.recv(1024)
            if not chunk:
                raise ConnectionError("no handshake")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode(errors="replace"))
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _need(self, k):
        while len(self.buf) < k:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.buf += chunk
        out, self.buf = self.buf[:k], self.buf[k:]
        return out

    def send(self, method, params=None):
        """Send one CDP call without waiting; its id."""
        self.n += 1
        msg = json.dumps({"id": self.n, "method": method, "params": params or {}}).encode()
        mask, n = os.urandom(4), len(msg)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                               else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(hdr + mask + bytes(b ^ mask[k % 4] for k, b in enumerate(msg)))
        return self.n

    def call(self, method, params=None, on_event=None):
        """One CDP call; its result, or None if the browser answered with an error. on_event(cdp, event) sees events
        that arrive meanwhile (chromectl answers "Leave site?" boxes this way); it may raise to stop waiting."""
        want = self.send(method, params)
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            b1, b2 = self._need(2)
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._need(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._need(8))[0]
            data = self._need(ln)
            if b1 & 0x0F == 1:
                reply = json.loads(data)
                if reply.get("id") == want:
                    return reply.get("result") if "error" not in reply else None
                if "method" in reply:
                    if len(self.events) < 200:
                        self.events.append(reply)
                    if on_event:
                        on_event(self, reply)
        raise TimeoutError("no reply")

    def drain(self, seconds, on_event=None):
        """Read events for a moment (a box a click opens shows up just after the click)."""
        end, old = time.time() + seconds, self.s.gettimeout()
        try:
            while time.time() < end:
                self.s.settimeout(max(0.05, end - time.time()))
                try:
                    b1, b2 = self._need(2)
                except (TimeoutError, socket.timeout):
                    return
                ln = b2 & 0x7F
                if ln == 126:
                    ln = struct.unpack(">H", self._need(2))[0]
                elif ln == 127:
                    ln = struct.unpack(">Q", self._need(8))[0]
                data = self._need(ln)
                if b1 & 0x0F == 1:
                    msg = json.loads(data)
                    if "method" in msg and on_event:
                        on_event(self, msg)
        finally:
            self.s.settimeout(old)

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


def _ws_eval(ws_url, expression, timeout=10):
    c = Cdp(ws_url, timeout)
    try:
        return ((c.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True}) or {})
                .get("result", {}).get("value"))
    finally:
        c.close()


def _targets():
    with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=3) as r:
        return json.load(r)


class QuietDownloads:
    """Dev builds only: while open, Paseo's browser tabs save downloads into `folder` without a Save box. The
    setting lives on each tab's DevTools connection, so the connections stay open until close(), which puts the
    Save box back. Shipping fix: Paseo patch P1. `ok` says whether it took effect."""

    def __init__(self, folder):
        self.conns, self.ok = [], False
        try:
            tabs = [t for t in _targets() if t.get("type") == "webview"]
        except (OSError, ValueError):
            return
        for t in tabs:
            try:
                c = Cdp(t["webSocketDebuggerUrl"])
                if c.call("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": folder}) is not None:
                    self.conns.append(c)
                    self.ok = True
                else:
                    c.close()
            except (OSError, ValueError, KeyError, ConnectionError, TimeoutError):
                pass

    def close(self):
        for c in self.conns:
            try:
                c.call("Page.setDownloadBehavior", {"behavior": "default"})
            except (OSError, ConnectionError, TimeoutError):
                pass
            c.close()
        self.conns = []


def webview_ids():
    try:
        return {t["id"] for t in _targets() if t.get("type") == "webview"}
    except (OSError, ValueError):
        return set()


class Page:
    """One browser tab's page through DevTools (dev builds only): run JS in it, drop a file on it."""

    def __init__(self, target_id, timeout=20):
        t = next(t for t in _targets() if t["id"] == target_id)
        self.c = Cdp(t["webSocketDebuggerUrl"], timeout)

    def eval(self, js):
        return ((self.c.call("Runtime.evaluate", {"expression": js, "returnByValue": True, "awaitPromise": True}) or {})
                .get("result", {}).get("value"))

    def drop_file(self, path, x=None, y=None):
        """Drag a local file onto the page, as a person dropping it from the file manager (Drive uploads it)."""
        if x is None:
            x, y = (self.eval("[innerWidth / 2, innerHeight / 2]") or [600, 400])
        data = {"items": [], "files": [path], "dragOperationsMask": 1}
        for typ in ("dragEnter", "dragOver", "drop"):
            if self.c.call("Input.dispatchDragEvent", {"type": typ, "x": x, "y": y, "data": data}) is None:
                return False
            time.sleep(0.3)
        return True

    def close(self):
        self.c.close()


def new_page(before, wait=20):
    """The DevTools id of a tab opened after `before` (a webview_ids() snapshot), once it exists."""
    end = time.time() + wait
    while time.time() < end:
        new = webview_ids() - before
        if new:
            return sorted(new)[0]
        time.sleep(0.5)
    return None


# Paseo keeps other workspaces' tab rows mounted but hidden: use the row that is on screen. The row also holds an
# off-screen copy of each label (for measuring): take the one actually on screen. A label matches if it equals, or
# starts with, one of the candidates (a tab shows its host until it loads, then the page title); the newest wins.
CLICK_TAB = """(labels => { const rows = [...document.querySelectorAll('[data-testid="workspace-tabs-row"]')]
    .filter(r => { const b = r.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
  if (!rows.length) return 'no-row';
  const onScreen = e => { const r = e.getBoundingClientRect(); if (!r.width) return false;
    const c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return c && (c === e || e.contains(c) || c.contains(e)); };
  const fits = t => labels.some(l => t === l || (l.endsWith('*') && t.startsWith(l.slice(0, -1))));
  for (const row of rows) {
    const hits = [...row.querySelectorAll('*')].filter(e => e.childElementCount === 0 && fits((e.innerText || '').trim())).filter(onScreen);
    if (hits.length) { const leaf = hits[hits.length - 1]; (leaf.parentElement || leaf).click(); return 'ok'; } }
  return 'no-tab'; })(%s)"""


def show_tab(label):
    """Click the tab with this label in the workspace that's showing (dev builds only, see above). label: a string or
    a list of candidates; a candidate ending in * matches labels starting with it."""
    labels = [label] if isinstance(label, str) else list(label)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=3) as r:
            pages = json.load(r)
    except OSError:
        return {"ok": False, "why": "no-devtools-port"}
    page = next((p for p in pages if p.get("type") == "page" and p.get("url", "").startswith("paseo://app")), None)
    if not page:
        return {"ok": False, "why": "app page not found"}
    try:
        got = _ws_eval(page["webSocketDebuggerUrl"], CLICK_TAB % json.dumps(labels))
    except (OSError, ValueError, ConnectionError, TimeoutError) as e:
        return {"ok": False, "why": f"{type(e).__name__}: {e}"[:120]}
    return {"ok": got == "ok", "why": None if got == "ok" else got}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("agent", "tab"):
        sys.exit(__doc__)
    print(json.dumps(show_agent(sys.argv[2]) if sys.argv[1] == "agent" else show_tab(sys.argv[2])))
