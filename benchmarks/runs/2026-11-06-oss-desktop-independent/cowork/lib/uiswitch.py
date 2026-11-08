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


# ---- a minimal DevTools (CDP) client: one Runtime.evaluate over a websocket, standard library only
def _ws_eval(ws_url, expression, timeout=10):
    rest = ws_url.split("://", 1)[1]
    hostport, path = rest.split("/", 1)
    host, port = hostport.split(":")
    s = socket.create_connection((host, int(port)), timeout=timeout)
    try:
        key = base64.b64encode(os.urandom(16)).decode()
        s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = s.recv(1024)
            if not chunk:
                raise ConnectionError("no handshake")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode(errors="replace"))
        buf = head.split(b"\r\n\r\n", 1)[1]
        msg = json.dumps({"id": 1, "method": "Runtime.evaluate",
                          "params": {"expression": expression, "returnByValue": True}}).encode()
        mask = os.urandom(4)
        n = len(msg)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536
                               else bytes([0x80 | 127]) + struct.pack(">Q", n))
        s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(msg)))

        def need(k):
            nonlocal buf
            while len(buf) < k:
                chunk = s.recv(65536)
                if not chunk:
                    raise ConnectionError("closed")
                buf += chunk
            out, buf = buf[:k], buf[k:]
            return out
        deadline = time.time() + timeout
        while time.time() < deadline:
            b1, b2 = need(2)
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", need(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", need(8))[0]
            data = need(ln)
            if b1 & 0x0F == 1:
                reply = json.loads(data)
                if reply.get("id") == 1:
                    return reply.get("result", {}).get("result", {}).get("value")
        raise TimeoutError("no reply")
    finally:
        s.close()


# Paseo keeps other workspaces' tab rows mounted but hidden: use the row that is on screen
CLICK_TAB = """(label => { const rows = [...document.querySelectorAll('[data-testid="workspace-tabs-row"]')]
    .filter(r => { const b = r.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
  if (!rows.length) return 'no-row';
  for (const row of rows) {
    const leaf = [...row.querySelectorAll('*')].find(e => e.childElementCount === 0 && (e.innerText || '').trim() === label);
    if (leaf) { (leaf.parentElement || leaf).click(); return 'ok'; } }
  return 'no-tab'; })(%s)"""


def show_tab(label):
    """Click the tab with this label in the workspace that's showing (dev builds only, see above)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=3) as r:
            pages = json.load(r)
    except OSError:
        return {"ok": False, "why": "no-devtools-port"}
    page = next((p for p in pages if p.get("type") == "page" and p.get("url", "").startswith("paseo://app")), None)
    if not page:
        return {"ok": False, "why": "app page not found"}
    try:
        got = _ws_eval(page["webSocketDebuggerUrl"], CLICK_TAB % json.dumps(label))
    except (OSError, ValueError, ConnectionError, TimeoutError) as e:
        return {"ok": False, "why": f"{type(e).__name__}: {e}"[:120]}
    return {"ok": got == "ok", "why": None if got == "ok" else got}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("agent", "tab"):
        sys.exit(__doc__)
    print(json.dumps(show_agent(sys.argv[2]) if sys.argv[1] == "agent" else show_tab(sys.argv[2])))
