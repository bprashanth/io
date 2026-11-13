"""Fetch a Google Drive file as the person, straight from the app's signed-in browser, with no download box.

A Mini is a dashboard for one Drive file, so it fetches that file every time it opens. This runs `fetch()` inside a
Google tab of Paseo's browser (DevTools, dev builds; shipping needs a small Paseo patch), so the request carries the
person's own sign-in: if they can't open the file in Drive, Idli can't either.

  fetch(file_id, sheet=True) -> bytes        raises NoAccess, NoGoogle
"""
import base64
import json
import os
import time

from lib import uiswitch

GOOGLE = ("https://docs.google.com/", "https://drive.google.com/")


class NoAccess(Exception):
    """The person's Google account can't open the file (or it is gone)."""


class NoGoogle(Exception):
    """No signed-in Google tab in the app's browser to fetch through."""


def export_url(file_id, sheet=True):
    from sites.google import tools as g
    if sheet:
        return g.sheets_url(file_id, "export?format=xlsx")
    return "https://drive.google.com/uc?export=download&id=" + file_id + g.au("&")


JS = r"""(async (url) => {
  const r = await fetch(url, {credentials: "include", redirect: "follow"});
  const ct = r.headers.get("content-type") || "";
  if (!r.ok || ct.includes("text/html")) return {status: r.status, html: ct.includes("text/html")};
  const b = new Uint8Array(await r.arrayBuffer());
  let s = "";
  for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
  return {status: r.status, b64: btoa(s), type: ct};
})"""


def tab_fetch(target, url, timeout=90):
    """Run the fetch in one DevTools target (a tab whose page is on a Google origin). Returns bytes."""
    c = uiswitch.Cdp(target["webSocketDebuggerUrl"], timeout)
    try:
        res = c.call("Runtime.evaluate", {"expression": f"{JS}({json.dumps(url)})", "awaitPromise": True,
                                          "returnByValue": True})
    finally:
        c.close()
    v = ((res or {}).get("result") or {}).get("value")
    if not isinstance(v, dict):
        raise NoGoogle("the Google tab didn't answer")
    if v.get("b64") is not None:
        return base64.b64decode(v["b64"])
    raise NoAccess(f"Drive answered {v.get('status')}" + (" with a sign-in or request-access page" if v.get("html") else ""))


def fetch(file_id, sheet=True):
    fake = os.environ.get("IDLI_DRIVE_FAKE")  # tests: a folder of <id>.xlsx; a missing id means no access
    if fake:
        p = os.path.join(fake, file_id + ".xlsx")
        if not os.path.exists(p):
            raise NoAccess("no such file in the fake Drive")
        time.sleep(float(os.environ.get("IDLI_DRIVE_FAKE_DELAY", "0")))
        with open(p, "rb") as f:
            return f.read()
    try:
        targets = [t for t in uiswitch._targets() if t.get("type") in ("webview", "page")
                   and t.get("url", "").startswith(GOOGLE)]
    except (OSError, ValueError):
        targets = []
    url = export_url(file_id, sheet)
    if targets:
        return tab_fetch(targets[0], url)
    return session_fetch(url)


def session_fetch(url, timeout=90):
    """No Google tab open: the same request from here, with the browser session's Google cookies (read through any
    of the app's tabs; they share one session). Follows Google's redirects by hand, sending each host its cookies."""
    import urllib.error
    import urllib.parse
    import urllib.request
    try:
        tab = next(t for t in uiswitch._targets() if t.get("type") in ("webview", "page"))
    except (OSError, ValueError, StopIteration):
        raise NoGoogle("the app's browser isn't reachable")
    c = uiswitch.Cdp(tab["webSocketDebuggerUrl"], 20)
    try:
        got = c.call("Network.getCookies", {"urls": ["https://docs.google.com/", "https://drive.google.com/",
                                                     "https://accounts.google.com/", "https://www.google.com/"]})
    finally:
        c.close()
    jar = (got or {}).get("cookies") or []
    if not any(k.get("name", "").endswith("SID") for k in jar):
        raise NoGoogle("not signed in to Google in the app's browser")

    class Keep(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(Keep)
    for _ in range(6):
        host = urllib.parse.urlsplit(url).hostname or ""
        cookie = "; ".join(f"{k['name']}={k['value']}" for k in jar
                           if host == k["domain"].lstrip(".") or host.endswith("." + k["domain"].lstrip(".")))
        req = urllib.request.Request(url, headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"} if cookie else
                                     {"User-Agent": "Mozilla/5.0"})
        try:
            with opener.open(req, timeout=timeout) as r:
                if "text/html" in (r.headers.get("Content-Type") or ""):
                    raise NoAccess("Drive answered with a sign-in or request-access page")
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            raise NoAccess(f"Drive answered {e.code}")
    raise NoAccess("too many redirects")
