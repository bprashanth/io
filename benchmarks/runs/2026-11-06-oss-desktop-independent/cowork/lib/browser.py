"""Drive the user's tabs in Paseo's workspace browser through the daemon's agent endpoint.

Every site plugin uses these helpers instead of talking to Paseo itself. Tabs belong to the
workspace of PASEO_AGENT_ID (Paseo sets it for each agent; the test runner takes --agent).
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

MCP_URL = os.environ.get("PASEO_MCP_URL", "http://127.0.0.1:6767/mcp/agents")
LOG = os.environ.get("COWORK_LOG")


def log(*a):
    if LOG:
        with open(LOG, "a") as f:
            print(time.strftime("%H:%M:%S"), *a, file=f)


def paseo(tool, **args):
    """Call one of Paseo's browser_* tools. Raises RuntimeError with Paseo's message on failure."""
    url = MCP_URL + "?" + urllib.parse.urlencode({"callerAgentId": os.environ.get("PASEO_AGENT_ID", "")})
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    req = urllib.request.Request(url, body, {"content-type": "application/json",
                                             "accept": "application/json, text/event-stream"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    msg = None
    for line in raw.splitlines():
        if line.startswith("data:"):
            msg = json.loads(line[5:])
    msg = msg or json.loads(raw)
    res = msg.get("result", {})
    text = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
    if res.get("isError") or "error" in msg:
        raise RuntimeError(text or json.dumps(msg.get("error")))
    log(tool, json.dumps(args)[:200], "->", len(text), "chars")
    return text


def tabs():
    out = []
    for m in re.finditer(r'browserId=(\S+)( active)? title="(.*)" url=(\S+)', paseo("browser_list_tabs")):
        out.append({"id": m.group(1), "active": bool(m.group(2)), "title": m.group(3), "url": m.group(4)})
    return out


def tab_for(*hosts, open_url=None):
    """Reuse the user's tab for this site (prefer the active one), else open one."""
    every = tabs()
    ts = [t for t in every if any(h in t["url"] for h in hosts)]
    ts.sort(key=lambda t: not t["active"])
    if ts:
        return ts[0]["id"]
    url = open_url or "https://" + hosts[0]
    out = ""
    for attempt in range(3):
        # The first tab in a workspace the app hasn't shown yet often times out, but is created anyway.
        try:
            out = paseo("browser_new_tab", url=url)
        except RuntimeError as e:
            out = str(e)
        m = re.search(r"browserId=(\S+)", out) or re.search(r'"browserId"\s*:\s*"([^"]+)"', out)
        if m:
            return m.group(1)
        time.sleep(3 + 3 * attempt)
        every = tabs()
        ts = [t for t in every if any(h in t["url"] for h in hosts)]
        if ts:
            return ts[0]["id"]
    # browser_new_tab sometimes times out; reuse a tab on the same domain (e.g. drive -> mail.google.com).
    def domain(u):
        return ".".join(urllib.parse.urlparse(u).hostname.split(".")[-2:]) if "//" in u else ""
    same = [t for t in every if domain(t["url"]) and domain(t["url"]) == domain(url)]
    if same:
        paseo("browser_navigate", browserId=same[0]["id"], url=url)
        return same[0]["id"]
    raise RuntimeError(f"Could not open a browser tab for {hosts[0]} ({out.strip()[:120]}). "
                       "Open the browser pane in this workspace and try again.")


def snapshot(tab, ready=None, tries=8):
    """Snapshot until `ready(snap)` is true (pages keep rendering after navigation)."""
    snap = ""
    for _ in range(tries):
        snap = paseo("browser_snapshot", browserId=tab)
        if ready is None or ready(snap):
            return snap
        time.sleep(1)
    return snap


def evaluate(tab, js):
    """Run a JS function in the page and return its JSON result (not allowed on Gmail/Docs)."""
    raw = paseo("browser_evaluate", browserId=tab, function=js)
    payload = raw.split("returned:", 1)[-1].strip()
    try:
        val = json.loads(payload)
        return json.loads(val) if isinstance(val, str) else val
    except ValueError:
        return None


def page_url(snap):
    m = re.search(r"^URL: (\S+)", snap, re.M)
    return m.group(1) if m else ""


def q(s):  # unescape a quoted snapshot label
    return s.replace('\\"', '"')


class NotSignedIn(RuntimeError):
    """The site shows a sign-in page instead of the account's content."""
