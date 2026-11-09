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


def show_agent(agent):
    """Switch Paseo to this chat, in whatever workspace it lives."""
    if not APP:
        return {"ok": False, "why": "Paseo app not found"}
    try:
        link = f"paseo://h/{server_id()}/agent/{full_agent_id(agent)}"
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "why": f"could not read Paseo's server id: {type(e).__name__}"}
    p = subprocess.Popen([APP, link], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        p.wait(timeout=15)  # the second launch hands the link over and quits
    except subprocess.TimeoutExpired:
        pass
    return {"ok": True}


# ---- a minimal DevTools (CDP) client over a websocket, standard library only
class Cdp:
    def __init__(self, ws_url, timeout=10):
        rest = ws_url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.timeout, self.n, self.buf = timeout, 0, b""
        self.s = socket.create_connection((host, int(port)), timeout=timeout)
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

    def call(self, method, params=None):
        """One CDP call; its result, or None if the browser answered with an error."""
        self.n += 1
        msg = json.dumps({"id": self.n, "method": method, "params": params or {}}).encode()
        mask, n = os.urandom(4), len(msg)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                               else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(hdr + mask + bytes(b ^ mask[k % 4] for k, b in enumerate(msg)))
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
                if reply.get("id") == self.n:
                    return reply.get("result") if "error" not in reply else None
        raise TimeoutError("no reply")

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


def _ws_eval(ws_url, expression, timeout=10):
    c = Cdp(ws_url, timeout)
    try:
        return ((c.call("Runtime.evaluate", {"expression": expression, "returnByValue": True}) or {})
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
        return ((self.c.call("Runtime.evaluate", {"expression": js, "returnByValue": True}) or {})
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
