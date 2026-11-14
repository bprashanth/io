"""Local consent and reveal ledger. Only the authenticated page can decide a request."""
import copy
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import uuid

from lib import privacy, journey

PERSONAL = 'PLACE codes can be revealed. Names, contacts, IDs and exact locations never are.'
BUDGET = 'This workspace has no reveals left. You can allow 3 more on the Reveals page.'


def _path(data_dir, name):
    return Path(data_dir) / '.idli' / name


def _budget(data_dir):
    path = _path(data_dir, 'reveal-budget.json')
    return json.loads(path.read_text()) if path.exists() else {}


def remaining(data_dir, workspace):
    b = _budget(data_dir).get(workspace, {})
    return b.get('limit', 3) - b.get('used', 0)


@privacy.locked
def allow_more(data_dir, workspace):
    if not isinstance(workspace, str) or not workspace:
        raise ValueError('Open Reveals from a Drivey workspace.')
    b = _budget(data_dir)
    entry = b.setdefault(workspace, {'limit': 3, 'used': 0})
    entry['limit'] += 3
    privacy._write(_path(data_dir, 'reveal-budget.json'), b)
    return {'remaining': remaining(data_dir, workspace)}


@privacy.locked
def hide(data_dir, code, workspace, at):
    rows = privacy.reveals(data_dir)
    privacy._write(_path(data_dir, 'reveals.json'), [r for r in rows if not
                   (r['code'] == code and r['workspace'] == workspace and r['at'] == at)])
    return {'hidden': True}


@privacy.locked
def create(data_dir, code, reason, workspace, kind='unmask', query=None):
    info = privacy.code_info(data_dir, code)
    if not info or info['class'] != 'contextual':
        return {'refused': PERSONAL}
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        return {'refused': 'Give a short reason for this request.'}
    if not isinstance(workspace, str) or not workspace.strip():
        return {'refused': 'Open this request from a Drivey workspace.'}
    if kind not in ('lookup', 'unmask'):
        raise ValueError('Unknown request.')
    if kind == 'lookup' and (not isinstance(query, str) or '{value}' not in query or len(query) > 1000):
        return {'refused': 'The search must include {value}.'}
    if kind == 'unmask' and remaining(data_dir, workspace) <= 0:
        return {'refused': BUDGET}
    if query is not None:
        query = privacy._redact(query, privacy.session_vault(data_dir), lambda _: [])[0]
    ident = uuid.uuid4().hex
    record = {**info, 'code': code, 'value': privacy.session_vault(data_dir).display[code],
              'workspace': workspace, 'reason': reason.strip(), 'kind': kind, 'query': query,
              'expires': time.time() + 120, 'decision': 'pending'}
    privacy._write(_path(data_dir, f'consents/{ident}.json'), record)
    return {'id': ident}


@privacy.locked
def consent_data(data_dir, ident):
    path = journey.record_path(data_dir, 'consents', ident)
    record = json.loads(path.read_text())
    if record['decision'] == 'pending' and time.time() >= record['expires']:
        record['decision'] = 'timeout'
        privacy._write(path, record)
    return record


@privacy.locked
def decide(data_dir, ident, approve):
    if type(approve) is not bool:
        raise ValueError('Choose Reveal or Keep hidden.')
    record = consent_data(data_dir, ident)
    if record['decision'] != 'pending':
        return {'decision': record['decision']}
    decision = 'denied'
    if approve:
        info = privacy.code_info(data_dir, record['code'])
        value = privacy.session_vault(data_dir).display.get(record['code'])
        if not info or info['class'] != 'contextual' or value != record['value']:
            decision = 'changed'
        elif record['kind'] == 'unmask' and remaining(data_dir, record['workspace']) <= 0:
            decision = 'budget'
        else:
            rows = privacy.reveals(data_dir)
            rows.append({k: record[k] for k in ('code', 'value', 'column', 'file', 'workspace', 'reason', 'kind')}
                        | {'at': dt.datetime.now(dt.timezone.utc).isoformat()})
            if record['kind'] == 'unmask':
                b = _budget(data_dir)
                entry = b.setdefault(record['workspace'], {'limit': 3, 'used': 0})
                entry['used'] += 1
                # Spend before publishing the reveal. A failed write must not grant a free reveal.
                privacy._write(_path(data_dir, 'reveal-budget.json'), b)
            privacy._write(_path(data_dir, 'reveals.json'), rows)
            decision = 'approved'
    record['decision'] = decision
    privacy._write(journey.record_path(data_dir, 'consents', ident), record)
    return {'decision': decision}


def ask(data_dir, code, reason, workspace, kind='unmask', query=None):
    from lib import uiswitch
    result = create(data_dir, code, reason, workspace, kind, query)
    if 'refused' in result:
        return result
    ident = result['id']
    url = journey.page_url(data_dir, 'consent', id=ident, ws=workspace)
    try:
        opened = uiswitch.open_url(workspace, url, side='right', focus=True)
    except Exception:
        opened = {'ok': False}
    if not opened.get('ok'):
        decide(data_dir, ident, False)
        return {'refused': 'The consent page could not open. Keep this value hidden.'}
    while True:
        record = consent_data(data_dir, ident)
        if record['decision'] != 'pending':
            break
        time.sleep(.2)
    if record['decision'] != 'approved':
        return {'refused': BUDGET if record['decision'] == 'budget' else
                'The value stays hidden. The request was declined or expired.'}
    return record


class SearchResults(HTMLParser):
    """Read DuckDuckGo's HTML result links and snippets without executing page content."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.capture = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '').split()
        if 'result__a' in cls:
            url = urllib.parse.urljoin('https://duckduckgo.com', a.get('href', ''))
            url = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('uddg', [url])[0]
            if urllib.parse.urlsplit(url).scheme not in ('http', 'https'):
                return
            self.rows.append({'title': '', 'url': url, 'snippet': ''})
            self.capture, self.depth = 'title', 1
        elif 'result__snippet' in cls and self.rows:
            self.capture, self.depth = 'snippet', 1
        elif self.capture and tag not in ('br', 'img', 'meta', 'input', 'hr'):
            self.depth += 1

    def handle_endtag(self, tag):
        if self.capture:
            self.depth -= 1
            if self.depth <= 0:
                self.capture = None

    def handle_data(self, data):
        if self.capture and self.rows:
            self.rows[-1][self.capture] += data


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': 'Idli/1.0 (local research helper)'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(2_000_000).decode('utf-8', errors='replace')


def _strip_tags(text):
    import html
    import re
    return html.unescape(re.sub(r'<[^>]+>', '', text or '')).strip()


def search_news(query, limit=4):
    """Google News RSS: recent local news. Parsed as XML; no page content is executed."""
    import xml.etree.ElementTree as ET
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode(
        {'q': query, 'hl': 'en-IN', 'gl': 'IN', 'ceid': 'IN:en'})
    rows = []
    for item in ET.fromstring(_get(url)).iter('item'):
        link = (item.findtext('link') or '').strip()
        if urllib.parse.urlsplit(link).scheme not in ('http', 'https'):
            continue
        source = item.findtext('source') or ''
        date = (item.findtext('pubDate') or '')[:16]
        rows.append({'title': _strip_tags(item.findtext('title')), 'url': link,
                     'snippet': ' - '.join(x for x in (source.strip(), date.strip()) if x)})
        if len(rows) >= limit:
            break
    return rows


def search_wikipedia(query, limit=3):
    """Wikipedia search: background on places and programmes."""
    url = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'query', 'list': 'search', 'srsearch': query, 'format': 'json', 'srlimit': limit})
    rows = []
    for hit in json.loads(_get(url)).get('query', {}).get('search', [])[:limit]:
        title = str(hit.get('title', ''))
        rows.append({'title': title, 'url': 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_')),
                     'snippet': _strip_tags(hit.get('snippet', ''))})
    return rows


def search(query, fallback=None):
    """News first, then encyclopedia background; at most 6. (DuckDuckGo's HTML endpoint answers scripts with a bot
    challenge, tried 2026-11-15, so it is not used.) A source that fails is skipped."""
    rows = []
    for source in (search_news, search_wikipedia):
        try:
            rows += source(query)
        except (OSError, ValueError, Exception):  # noqa: BLE001 - one failing source must not hide the other
            continue
    if not rows and fallback and fallback != query:
        return search(fallback)
    return rows[:6]


def lookup_results(data_dir, code, query, value):
    with privacy.session_lock(data_dir):
        vault = privacy.session_vault(data_dir)
        index = privacy.code_index(data_dir, vault)
        if index.get(code, {}).get('class') != 'contextual' or vault.display.get(code) != value:
            raise ValueError(PERSONAL)
        query = privacy._redact(query, vault, lambda _: [])[0].replace('{value}', value)
        personal = copy.deepcopy(vault)
        personal.display = {c: v for c, v in vault.display.items() if index.get(c, {}).get('class', 'personal') == 'personal'}
        if privacy.known_leaks(query, personal):
            raise ValueError(PERSONAL)
    rows = search(query, value)
    with privacy.session_lock(data_dir):
        vault = privacy.session_vault(data_dir)
        def mask(text):
            # URLs can percent-encode names. Decode before masking. Include revealed values too.
            text = urllib.parse.unquote(str(text))
            return privacy._redact(text, vault, lambda _: [])[0]
        results = [{k: mask(row.get(k, '')) for k in ('title', 'url', 'snippet')} for row in rows[:6]]
        privacy._save(vault)
        return {'code': code, 'results': results}
