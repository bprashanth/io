"""Fetch a Google Drive file as the person, straight from the app's signed-in browser, with no download box.

A Mini is a dashboard for one Drive file, so it fetches that file every time it opens. The request carries the
person's own Google sign-in from Paseo's browser (read through DevTools, on in dev builds; shipping needs a small
Paseo patch): if they can't open the file in Drive, Idli can't either. About 1-1.5 s for a 7-130 KB sheet.

  fetch(file_id, sheet=True) -> bytes        raises NoAccess, NoGoogle
"""
import os
import time

from lib import uiswitch

class NoAccess(Exception):
    """The person's Google account can't open the file (or it is gone)."""


class NoGoogle(Exception):
    """No signed-in Google tab in the app's browser to fetch through."""


def export_url(file_id, sheet=True):
    from sites.google import tools as g
    if sheet:
        return g.sheets_url(file_id, "export?format=xlsx")
    return "https://drive.google.com/uc?export=download&id=" + file_id + g.au("&")


EXPORTS = {'Google Docs': ('document', 'docx'), 'Google Slides': ('presentation', 'pptx'),
           'Google Drawings': ('drawings', 'svg')}


def fetch(file_id, sheet=True, kind=None):
    fake = os.environ.get("IDLI_DRIVE_FAKE")  # tests: a folder of <id>.xlsx; a missing id means no access
    if fake:
        p = os.path.join(fake, file_id + ".xlsx")
        if not os.path.exists(p):
            raise NoAccess("no such file in the fake Drive")
        time.sleep(float(os.environ.get("IDLI_DRIVE_FAKE_DELAY", "0")))
        with open(p, "rb") as f:
            return f.read()
    if kind in EXPORTS:
        family, extension = EXPORTS[kind]
        suffix = f'export?format={extension}' if family == 'document' else f'export/{extension}'
        url = f'https://docs.google.com/{family}/d/{file_id}/{suffix}'
        return session_fetch(url)
    return session_fetch(export_url(file_id, sheet))


def session_fetch(url, timeout=90):
    """The request from here, with the app browser's Google cookies (read through any of the app's tabs; they share
    one session; they never leave this computer except to Google). Follows Google's redirects by hand, sending each
    host its cookies. (A fetch() inside a Google tab doesn't work: the export redirects to googleusercontent.com,
    and the browser won't let the page read that cross-origin answer. Tried on the laptop 2026-11-13.)"""
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
