"""Drive one Chrome profile over DevTools (CDP), standard library only (narrative/BUILDER_JOURNEY.md).

Two users:
- Idli's MCP server, for the Builder's browser tools on a confirmed TEST profile: Browser(port=...).
- A team's own site plugin (extensions/sites/<app>/...), run by Idli inside its wall through team_run (the real
  account, later) or the Builder's rehearse (the test accounts). The wall has no network; Idli gives it one door per
  profile, a unix socket that reaches that profile's DevTools and nothing else:

      import chromectl
      b = chromectl.Browser('me')          # the role the tool declares in manifest.json ("profile": "me")
      b.open('https://mail.google.com/mail/u/0/#search/from%3Aboss')
      page = b.read()                      # {'url', 'title', 'text', 'links': [...], 'controls': [...]}
      b.click(text='Compose'); b.type(ref, 'Hello', enter=False)

- A plugin's test runs with no browser at all: Replay(snapshots) answers read() with pages saved earlier by the
  Builder's browser_read(save_as=...), and records clicks and typing.

Refs ("e12") are stable while the element stays on the page: Idli marks each element it lists with data-idli-ref.
"""
import base64
import json
import os
import re
import socket
import threading
import time
import urllib.parse

try:
    from lib.uiswitch import Cdp
except ImportError:  # inside the wall, lib/ itself is on the path
    from uiswitch import Cdp

REF = re.compile(r'e\d{1,6}')

READ_JS = r"""(([maxT, maxI]) => {
  let n = Number(document.documentElement.getAttribute('data-idli-n') || 0);
  const ref = el => { let r = el.getAttribute('data-idli-ref');
    if (!r) { r = 'e' + (++n); el.setAttribute('data-idli-ref', r); } return r; };
  const vis = el => { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el); return s.visibility !== 'hidden' && s.display !== 'none'; };
  const clean = t => String(t || '').replace(/\s+/g, ' ').trim().slice(0, 80);
  const field = el => ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
  const label = el => clean(el.getAttribute('aria-label') || (field(el)
      ? ((el.labels && el.labels[0] && el.labels[0].innerText) || el.getAttribute('placeholder') ||
         el.getAttribute('title') || el.getAttribute('name') || (el.type === 'submit' ? el.value : ''))
      : (el.innerText || el.getAttribute('title') || '')));
  const links = [], controls = [];
  for (const a of document.querySelectorAll('a[href]')) {
    if (links.length >= maxI) break;
    if (!vis(a)) continue;
    const t = label(a); if (!t) continue;
    links.push({ref: ref(a), text: t, href: String(a.href).slice(0, 200)});
  }
  const sel = 'button,input,textarea,select,[role=button],[role=textbox],[role=checkbox],[role=tab],' +
    '[role=menuitem],[role=option],[role=combobox],[role=link]:not(a),[contenteditable=true],[contenteditable=""]';
  for (const el of document.querySelectorAll(sel)) {
    if (controls.length >= maxI) break;
    if (!vis(el) || el.type === 'hidden') continue;
    const kind = el.getAttribute('role') || (el.tagName === 'INPUT' ? 'input:' + (el.type || 'text')
      : el.isContentEditable ? 'editor' : el.tagName.toLowerCase());
    const c = {ref: ref(el), kind, label: label(el)};
    if ((el.tagName === 'INPUT' && el.type !== 'password') || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT')
      c.value = String(el.value || '').slice(0, 200);
    if (el.type === 'checkbox' || el.getAttribute('role') === 'checkbox')
      c.checked = el.checked === true || el.getAttribute('aria-checked') === 'true';
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') c.disabled = true;
    controls.push(c);
  }
  document.documentElement.setAttribute('data-idli-n', String(n));
  const text = (document.body ? document.body.innerText : '').replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n');
  return {url: location.href, title: document.title, text: text.slice(0, maxT), text_cut: text.length > maxT,
          links, controls};
})(%s)"""

FIND_JS = r"""((want) => {
  const clean = t => String(t || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const els = [...document.querySelectorAll('[data-idli-ref]')];
  const name = el => clean(el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('title'));
  const hit = els.find(el => name(el) === want) || els.find(el => name(el).includes(want));
  return hit ? hit.getAttribute('data-idli-ref') : null;
})(%s)"""

SPOT_JS = r"""((ref) => {
  const el = document.querySelector('[data-idli-ref="' + ref + '"]');
  if (!el) return null;
  el.scrollIntoView({block: 'center', inline: 'center'});
  const r = el.getBoundingClientRect();
  const name = String(el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('title') || '')
    .replace(/\s+/g, ' ').trim().slice(0, 80);
  return {x: r.left + r.width / 2, y: r.top + r.height / 2, label: name, host: location.host};
})(%s)"""

CLEAR_JS = r"""((ref) => {
  const el = document.querySelector('[data-idli-ref="' + ref + '"]');
  if (!el) return false;
  el.focus();
  if (typeof el.select === 'function') el.select(); else document.execCommand('selectAll');
  return true;
})(%s)"""


def _never_send(host, what):
    """WhatsApp: never send, by anyone (owner rule). The rest of the rules live in the Builder's instructions."""
    if str(host).endswith('whatsapp.com') and re.search(r'(?i)\bsend\b|enter', str(what)):
        raise ValueError('Idli never sends WhatsApp messages. Draft the text and let the person send it.')


class Browser:
    """One profile's Chrome. port: DevTools on 127.0.0.1 (Idli's own side). sock: a unix socket door (in the wall).
    With neither, the role's door from the environment (IDLI_BROWSER_<ROLE>), as team tools get it."""

    def __init__(self, profile=None, port=None, sock=None, timeout=20):
        if port is None and sock is None:
            role = re.sub(r'[^A-Z0-9]', '_', str(profile or 'me').upper())
            sock = os.environ.get('IDLI_BROWSER_' + role)
            if not sock:
                raise ValueError(f'No browser for {profile or "me"}: declare "profile" in manifest.json and run the '
                                 'tool through Idli.')
        self.port, self.sock, self.timeout = port, sock, timeout

    # ---- plumbing
    def _socket(self):
        if self.sock:
            s = socket.socket(socket.AF_UNIX)
            s.settimeout(self.timeout)
            s.connect(self.sock)
            return s
        return socket.create_connection(('127.0.0.1', int(self.port)), timeout=self.timeout)

    def _http(self, path, method='GET'):
        s = self._socket()
        try:
            s.sendall(f'{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n'.encode())
            data = b''
            while b'\r\n\r\n' not in data:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
            head, _, body = data.partition(b'\r\n\r\n')
            m = re.search(rb'(?im)^content-length:\s*(\d+)', head)
            while m and len(body) < int(m.group(1)):  # Chrome keeps the connection open: read what it said
                chunk = s.recv(65536)
                if not chunk:
                    break
                body += chunk
        finally:
            s.close()
        if b' 200 ' not in head.split(b'\r\n', 1)[0]:
            raise ValueError('The browser did not answer.')
        try:
            return json.loads(body or b'null')
        except ValueError:  # /json/activate answers in plain words
            return body.decode(errors='replace')

    def _pages(self):
        return [t for t in self._http('/json/list') if t.get('type') == 'page'
                and not str(t.get('url', '')).startswith(('devtools://', 'chrome-extension://'))]

    def _page(self):
        pages = self._pages()
        if pages:
            return pages[0]  # Chrome lists the most recently used tab first
        return self._http('/json/new?about:blank', 'PUT')

    def _cdp(self, target=None):
        t = target or self._page()
        ws = t['webSocketDebuggerUrl']
        path = '/' + ws.split('://', 1)[1].split('/', 1)[1]
        return Cdp('ws://127.0.0.1:0' + path, self.timeout, sock=self._socket())

    def _call(self, method, params=None, target=None):
        c = self._cdp(target)
        try:
            return c.call(method, params or {})
        finally:
            c.close()

    def evaluate(self, js, target=None):
        """Run JavaScript in the current tab and return its value (JSON-able)."""
        res = self._call('Runtime.evaluate', {'expression': js, 'returnByValue': True, 'awaitPromise': True},
                         target) or {}
        if res.get('exceptionDetails'):
            raise ValueError('The page did not run that.')
        return (res.get('result') or {}).get('value')

    def wait(self, timeout=15):
        """Until the page has loaded (and a moment for pages that keep drawing)."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.evaluate('document.readyState') == 'complete':
                    break
            except (OSError, ValueError, ConnectionError, TimeoutError):
                pass
            time.sleep(0.3)
        time.sleep(0.6)

    # ---- the calls
    def tabs(self):
        return [{'tab': i, 'title': str(t.get('title', ''))[:80], 'url': str(t.get('url', ''))[:200]}
                for i, t in enumerate(self._pages())]

    def use_tab(self, tab):
        pages = self._pages()
        if not 0 <= int(tab) < len(pages):
            raise ValueError('There is no such tab. Call browser_tabs for the list.')
        self._http('/json/activate/' + pages[int(tab)]['id'])
        time.sleep(0.3)
        return self.tabs()

    def open(self, url, new_tab=False):
        url = str(url or '').strip()
        if not re.match(r'https?://', url):
            raise ValueError('Open a web address (https://...).')
        if new_tab:
            t = self._http('/json/new?' + urllib.parse.quote(url, safe=':/?#[]@!$&\'()*+,;=%'), 'PUT')
            self._http('/json/activate/' + t['id'])
        else:
            res = self._call('Page.navigate', {'url': url}) or {}
            if res.get('errorText'):
                raise ValueError('The page did not open: ' + str(res['errorText'])[:80])
        self.wait()
        return {'url': self.evaluate('location.href'), 'title': self.evaluate('document.title')}

    def read(self, max_text=6000, max_items=60):
        return self.evaluate(READ_JS % json.dumps([int(max_text), int(max_items)]))

    def find(self, text):
        """The ref of the listed element whose name is (or contains) this text. Call read() first."""
        return self.evaluate(FIND_JS % json.dumps(' '.join(str(text).split()).lower()))

    def _spot(self, ref):
        if not REF.fullmatch(str(ref or '')):
            raise ValueError('Use a ref from browser_read, such as e12.')
        spot = self.evaluate(SPOT_JS % json.dumps(ref))
        if not spot:
            raise ValueError(f'{ref} is not on the page any more. Read the page again.')
        return spot

    def _mouse(self, x, y):
        c = self._cdp()
        try:
            for typ in ('mouseMoved', 'mousePressed', 'mouseReleased'):
                c.call('Input.dispatchMouseEvent', {'type': typ, 'x': x, 'y': y, 'button': 'left',
                                                    'clickCount': 0 if typ == 'mouseMoved' else 1})
        finally:
            c.close()

    def click(self, ref=None, text=None):
        if not ref and text:
            if not self.find(text):
                self.read()
            ref = self.find(text)
            if not ref:
                raise ValueError(f'Nothing called "{str(text)[:60]}" is on the page. Read the page again.')
        spot = self._spot(ref)
        _never_send(spot.get('host'), spot.get('label'))
        self._mouse(spot['x'], spot['y'])
        time.sleep(0.5)
        self.wait(10)
        return {'clicked': spot.get('label', ''), 'url': self.evaluate('location.href'),
                'title': self.evaluate('document.title')}

    def type(self, ref, text, enter=False, clear=False):
        spot = self._spot(ref)
        if enter:
            _never_send(spot.get('host'), 'enter')
        self._mouse(spot['x'], spot['y'])
        if clear:
            self.evaluate(CLEAR_JS % json.dumps(ref))
        c = self._cdp()
        try:
            c.call('Input.insertText', {'text': str(text)})
            if enter:
                for typ in ('keyDown', 'keyUp'):
                    c.call('Input.dispatchKeyEvent', {'type': typ, 'key': 'Enter', 'code': 'Enter',
                                                      'windowsVirtualKeyCode': 13, 'nativeVirtualKeyCode': 13,
                                                      **({'text': '\r'} if typ == 'keyDown' else {})})
        finally:
            c.close()
        if enter:
            self.wait(10)
        return {'typed': len(str(text)), 'into': spot.get('label', ''), 'url': self.evaluate('location.href')}

    def shot(self, path):
        res = self._call('Page.captureScreenshot', {'format': 'png'}) or {}
        if not res.get('data'):
            raise ValueError('The browser did not take the picture.')
        with open(path, 'wb') as f:
            f.write(base64.b64decode(res['data']))
        return str(path)


class Replay:
    """A browser for plugin tests, with no browser: read() answers with saved snapshots (browser_read save_as=...),
    keyed by URL (the current one, or the longest saved URL it starts with), or in order when given a list.
    open/click/type are recorded in .actions."""

    def __init__(self, snapshots):
        self.snaps, self.actions, self.url, self.i = snapshots, [], None, 0

    def open(self, url, new_tab=False):
        self.actions.append(('open', url))
        self.url = url
        return {'url': url, 'title': ''}

    def read(self, max_text=6000, max_items=60):
        if isinstance(self.snaps, list):
            snap = self.snaps[min(self.i, len(self.snaps) - 1)]
            self.i += 1
            return snap
        keys = sorted((k for k in self.snaps if self.url and str(self.url).startswith(k)), key=len, reverse=True)
        if self.url in self.snaps:
            return self.snaps[self.url]
        if keys:
            return self.snaps[keys[0]]
        raise ValueError(f'No saved page for {self.url}')

    def find(self, text):
        want = ' '.join(str(text).split()).lower()
        snap = self.read()
        items = [(c['ref'], c.get('label', '')) for c in snap.get('controls', [])] + \
                [(a['ref'], a.get('text', '')) for a in snap.get('links', [])]
        hit = next((r for r, n in items if n.lower() == want), None) or \
            next((r for r, n in items if want in n.lower()), None)
        return hit

    def click(self, ref=None, text=None):
        self.actions.append(('click', ref or self.find(text)))
        return {'clicked': text or ref}

    def type(self, ref, text, enter=False, clear=False):
        self.actions.append(('type', ref, text, bool(enter)))
        return {'typed': len(str(text))}

    def tabs(self):
        return [{'tab': 0, 'title': '', 'url': self.url or ''}]

    def wait(self, timeout=15):
        pass


class Door:
    """Idli's side of a team tool's door: a unix socket that reaches one profile's DevTools port and nothing else."""

    def __init__(self, path, port):
        self.path, self.port = str(path), int(port)
        self.srv = socket.socket(socket.AF_UNIX)
        self.srv.bind(self.path)
        os.chmod(self.path, 0o600)
        self.srv.listen(32)
        self.stopped = False
        threading.Thread(target=self._serve, daemon=True).start()

    @staticmethod
    def _pipe(a, b):
        try:
            while True:
                data = a.recv(65536)
                if not data:
                    break
                b.sendall(data)
        except OSError:
            pass
        finally:
            for s in (a, b):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def _serve(self):
        while not self.stopped:
            try:
                c, _ = self.srv.accept()
            except OSError:
                break
            try:
                u = socket.create_connection(('127.0.0.1', self.port), timeout=10)
                u.settimeout(None)
            except OSError:
                c.close()
                continue
            threading.Thread(target=self._pipe, args=(c, u), daemon=True).start()
            threading.Thread(target=self._pipe, args=(u, c), daemon=True).start()

    def stop(self):
        self.stopped = True
        try:
            self.srv.close()
        except OSError:
            pass
        try:
            os.unlink(self.path)
        except OSError:
            pass
