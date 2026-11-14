"""Per-file privacy (engine and local review page).

What leaves: the configured HTTP scanner receives column sample windows and only
unmatched question text. Claude receives masked questions, form ids/labels,
masked filter choices and earlier masked question/spec pairs. No rows, answers,
SQL, workbook paths or vault are included in planner prompts. A final local
leak check refuses prompts containing known private values.
What never leaves: the vault and original workbook. Real samples on /privacy are
served only by the authenticated loopback formserver. Scanner failure is reported
as 'regex only'; names/places unknown to the vault may then be missed. Review=ask
is a setting for callers to enforce before invoking plan; plan itself sends.
"""
import builtins
import difflib
from contextlib import contextmanager
import functools
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import urllib.request

from . import filekit as fk
from .privacy_engine.columns import classify_columns
from .privacy_engine.detect import regex_engine
from .privacy_engine.pseudonymize import PseudonymMap, TOKEN_RE, normalise, pseudonymise_frame, redact_text

_LOCK = threading.RLock()
_HELD = threading.local()


@contextmanager
def session_lock(data_dir):
    """Serialize vault read/modify/write across the proxy and the form server."""
    import fcntl
    root = Path(data_dir).resolve()
    with _LOCK:
        held = getattr(_HELD, 'roots', frozenset())
        if root in held:
            yield
            return
        folder = root / '.idli'
        folder.mkdir(parents=True, exist_ok=True)
        fd = os.open(folder / 'privacy.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            _HELD.roots = held | {root}
            try:
                yield
            finally:
                _HELD.roots = held


def locked(fn):
    directory = next(iter(inspect.signature(fn).parameters), None) == 'data_dir'
    @functools.wraps(fn)
    def call(*args, **kwargs):
        guard = session_lock(args[0] if args else kwargs['data_dir']) if directory else _LOCK
        with guard:
            return fn(*args, **kwargs)
    return call


def _key(data_dir, file):
    root = Path(data_dir).resolve()
    path = (root / file).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('File must be inside the data directory')
    return path.relative_to(root).as_posix()


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@locked
def get(data_dir, file):
    key = _key(data_dir, file)
    path = Path(data_dir) / 'privacy.json'
    saved = json.loads(path.read_text()) if path.exists() else {}
    return {'mode': None, 'review': 'ask', 'columns': {}, **saved.get(key, {})}


@locked
def set(data_dir, file, **changes):
    if changes.keys() - {'mode', 'review', 'columns'}:
        raise ValueError('Unknown privacy setting')
    settings = {**get(data_dir, file), **changes}
    if settings['mode'] not in (None, 'fake', 'mask') or settings['review'] not in ('ask', 'auto'):
        raise ValueError('Invalid mode or review')
    if not isinstance(settings['columns'], dict) or any(
            not isinstance(k, str) or type(v) is not bool for k, v in settings['columns'].items()):
        raise ValueError('Columns must map names to booleans')
    path = Path(data_dir) / 'privacy.json'
    saved = json.loads(path.read_text()) if path.exists() else {}
    saved[_key(data_dir, file)] = settings
    _write(path, saved)
    return settings


def _vault(data_dir, file):
    _key(data_dir, file)  # retain the per-file path validation
    return _session_map(data_dir)


def _session_map(data_dir):
    """One code namespace for the directory, including existing per-file vaults.

    Conflicting legacy codes cannot be safely reinterpreted: refuse migration rather
    than silently restore a tool call to a different person's value.
    """
    path = Path(data_dir) / 'vault' / 'session.json'
    vault = PseudonymMap(path)
    if not path.exists():
        for old in sorted(path.parent.glob('*.json')):
            legacy = PseudonymMap(old)
            for code, real in legacy.display.items():
                key = normalise(real)
                if ((code in vault.display and normalise(vault.display[code]) != key)
                        or (key in vault.forward and vault.forward[key] != code)):
                    raise ValueError('Conflicting legacy vaults; use a new data directory')
                vault.display[code], vault.forward[key] = real, code
            for prefix, count in legacy.counters.items():
                vault.counters[prefix] = max(vault.counters.get(prefix, 0), count)
    return vault


@locked
def session_vault(data_dir):
    """Seed every selected cell in every mask-mode file into the shared vault."""
    vault = _session_map(data_dir)
    path = Path(data_dir) / 'privacy.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    for file, options in sorted(settings.items()):
        if options.get('mode') != 'mask':
            continue
        key = _key(data_dir, file)
        sheets, _ = fk.raw_sheets(str(Path(data_dir) / key))
        for frame in sheets.values():
            _code_frame(frame, options.get('columns', {}), vault)
    _save(vault)
    return vault


@locked
def active_vault(data_dir, vault=None):
    """Keep stable codes in storage, but stop masking cells explicitly switched off.

    Values still selected in another file/column stay private. Scanner-discovered values
    that are not cells also remain private.
    """
    import copy
    vault = copy.deepcopy(vault or session_vault(data_dir))
    path = Path(data_dir) / 'privacy.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    active, inactive = builtins.set(), builtins.set()
    for file, options in settings.items():
        if options.get('mode') != 'mask':
            continue
        sheets, _ = fk.raw_sheets(str(Path(data_dir) / _key(data_dir, file)))
        for frame in sheets.values():
            for column in frame.columns:
                dest = active if options.get('mode') == 'mask' and options.get('columns', {}).get(str(column)) else inactive
                dest.update(normalise(str(v)) for v in frame[column] if str(v).strip())
    excluded = inactive - active
    vault.display = {code: real for code, real in vault.display.items() if normalise(real) not in excluded}
    vault.forward = {normalise(real): code for code, real in vault.display.items()}
    vault.refresh()
    return vault


def _save(vault):
    _write(vault.path, {'forward': vault.forward, 'display': vault.display, 'counters': vault.counters})


class Scanner:
    def __init__(self):
        self.status = 'ok'

    def __call__(self, text):
        if self.status != 'ok':
            return []
        # Cloudflare (privacy.idli.cc) refuses Python's default User-Agent with a 403
        headers = {'Content-Type': 'application/json', 'User-Agent': 'idli-privacy/1'}
        token = os.environ.get('IO_PRIVACY_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(os.environ.get('IDLI_SCANNER', 'http://127.0.0.1:8899/scan'),
                                     json.dumps({'text': text}).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                spans = json.load(r)['spans']
            return [(int(a), int(b), str(c), float(d)) for a, b, c, d in spans
                    if 0 <= int(a) < int(b) <= len(text) and float(d) >= .7]
        except (OSError, ValueError, KeyError, TypeError):
            self.status = 'regex only'
            return []


def _class(column):
    c = str(column).casefold()
    for pattern, cls in [(r'name|beneficiary|employee', 'person_name'),
                         (r'ward|village|town|place|district', 'village'),
                         (r'address', 'address'), (r'phone|mobile', 'phone'), (r'email', 'email')]:
        if re.search(pattern, c):
            return cls
    return 'value'


def _frame(path, tab):
    sheets, _ = fk.raw_sheets(str(path))
    tab = tab or next(iter(sheets))
    if tab not in sheets:
        raise ValueError('Unknown workbook tab')
    return sheets[tab]


def _code_frame(frame, columns, vault):
    # Explicit choices always code the entire cell, including numbers, dates and GPS.
    classes = {c: _class(c) for c in frame.columns if columns.get(str(c), False)}
    return pseudonymise_frame(frame, classes, vault)


@locked
def suggest(path, tab):
    frame = _frame(path, tab)
    scanner = Scanner()
    classes = classify_columns(frame, scanner)
    vault = PseudonymMap()
    choices, reasons = {}, {}
    for c in frame.columns:
        info = classes[str(c)]
        mask = info['class'] not in ('none', 'age', 'record_id_non_pii')
        reason = info['rule']
        if info['rule'] in ('no-model', 'span-coverage', 'categorical') and _class(c) != 'value':
            mask, reason = True, 'identifier column heading'
        if re.search(r'income|amount|salary|revenue|expense|price|cost|balance', str(c), re.I):
            values = frame[c].replace('', None).dropna()
            import pandas as pd
            if len(values) and pd.to_numeric(values, errors='coerce').notna().mean() >= .95:
                mask, reason = False, 'numeric measure'
        choices[str(c)] = mask
        reasons[str(c)] = reason
    coded = _code_frame(frame, choices, vault)
    return [{'column': str(c), 'mask': choices[str(c)],
             'reason': reasons[str(c)] + ('; scanner unavailable — regex only' if scanner.status != 'ok' else ''),
             'samples': frame[c].head(3).astype(str).tolist(),
             'as_sent': coded[c].head(3).astype(str).tolist()} for c in frame.columns]


@locked
def masked_frame(data_dir, file, path, tab):
    vault = _vault(data_dir, file)
    frame = _code_frame(_frame(path, tab), get(data_dir, file)['columns'], vault)
    _save(vault)
    return frame


@locked
def _seed(data_dir, file, path):
    # All chosen cells, across tabs, before matching any question (not just samples).
    vault = _vault(data_dir, file)
    sheets, _ = fk.raw_sheets(str(path))
    for frame in sheets.values():
        _code_frame(frame, get(data_dir, file)['columns'], vault)
    _save(vault)
    return vault


def _value_pattern(value):
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value):
        return r'(?<![\w.])' + re.escape(value) + r'(?!\w|\.\d)'
    return r'(?<!\w)' + re.escape(value) + r'(?!\w)'


def _known(text, vault):
    # Include short and numeric values too; avoid matching numbers inside code suffixes.
    values = sorted(vault.display.values(), key=len, reverse=True)
    if not values:
        return text, []
    pattern = re.compile('|'.join(_value_pattern(v) for v in values), re.I)
    found = []
    def sub(m):
        code = vault.forward[normalise(m.group())]
        found.append({'real': m.group(), 'code': code, 'why': 'known value'})
        return code
    return pattern.sub(sub, text), found


GENERIC = {'ward', 'village', 'block', 'district', 'taluka', 'taluk', 'gram', 'nagar', 'colony', 'area', 'zone',
           'the', 'of'}


def _cores(vault):
    """Each known value, plus its distinctive part ('Yerawada Ward' -> 'Yerawada'), so a question that names a place
    the short way gets the same code as the file's value instead of a new one."""
    out = []
    for code, real in vault.display.items():
        out.append((code, real))
        core = ' '.join(w for w in re.findall(r'[^\W\d_]+', real) if w.casefold() not in GENERIC)
        if core and core.casefold() != real.casefold():
            out.append((code, core))
    return out


def _redact(text, vault, scanner):
    text, found = _known(text, vault)
    # Conservative edit-distance match against known words/phrases only; unique winner.
    words = list(re.finditer(r'\b[^\W\d_]+(?:[\s-]+[^\W\d_]+)*\b', text))
    spans = []
    for m in words:
        tokens = list(re.finditer(r'[^\W\d_]+', m.group()))
        for i in range(len(tokens)):
            for n in range(1, min(5, len(tokens) - i) + 1):
                a, b = m.start() + tokens[i].start(), m.start() + tokens[i+n-1].end()
                fragment = text[a:b]
                if len(fragment) < 5:
                    continue
                matches = []
                for code, real in _cores(vault):
                    if len(real) < 5 or abs(len(real) - len(fragment)) > 2:
                        continue
                    ratio = difflib.SequenceMatcher(None, fragment.casefold(), real.casefold()).ratio()
                    if ratio >= .85 and code not in [c for c, _ in matches]:
                        matches.append((code, real))
                if len(matches) == 1:
                    spans.append((a, b, *matches[0]))
    end = -1
    selected = []
    for a, b, code, real in sorted(spans, key=lambda x: (x[0], -(x[1]-x[0]))):
        if a >= end:
            selected.append((a, b, code))
            found.append({'real': text[a:b], 'code': code, 'why': 'close known value'})
            end = b
    for a, b, code in reversed(selected):
        text = text[:a] + code + text[b:]
    text, events = redact_text(text, vault, regex_engine)
    found += [{'real': e['text'], 'code': e['token'], 'why': 'regex validator'} for e in events]
    # The scanner gets only the remaining text: blank out existing codes first.
    remaining = TOKEN_RE.sub(lambda m: ' ' * len(m.group()), text)
    spans = scanner(remaining)
    text, events = redact_text(text, vault, lambda _: spans)
    found += [{'real': e['text'], 'code': e['token'], 'why': 'scanner'} for e in events]
    return text, found


@locked
def mask_text(data_dir, file, path, text, active=False):
    full = _seed(data_dir, file, path)
    vault = active_vault(data_dir, full) if active else full
    scanner = Scanner()
    masked, found = _redact(str(text), vault, scanner)
    if active:
        full.forward.update(vault.forward)
        full.display.update(vault.display)
        full.counters.update(vault.counters)
        _save(full)
    else:
        _save(vault)
    return {'masked': masked, 'found': found, 'scanner': scanner.status}


@locked
def unmask(data_dir, file, obj):
    vault = _vault(data_dir, file)
    def restore(v):
        if isinstance(v, str):
            return vault.rehydrate(v)
        if isinstance(v, list):
            return [restore(x) for x in v]
        if isinstance(v, dict):
            return {restore(k): restore(x) for k, x in v.items()}
        return v
    return restore(obj)


@locked
def leak_check(data_dir, file, outgoing):
    return known_leaks(outgoing, _vault(data_dir, file))


def known_leaks(outgoing, vault):
    # Decode JSON escapes as well, and remove codes so e.g. a masked '001' doesn't
    # match inside NAME_001. Fail closed for known values in labels or instructions.
    text = TOKEN_RE.sub('', outgoing)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), text)
    return [v for v in vault.display.values()
            if re.search(_value_pattern(v), text, re.I)]


def _shape(form, spec):
    if not isinstance(spec, dict):
        return 'Spec must be an object.'
    for key, available in [('measures', form['_measures']),
                           ('group_by', {g['id']: g for g in form['group_by']})]:
        vals = spec.get(key, [])
        if not isinstance(vals, list) or any(not isinstance(v, str) or v not in available for v in vals):
            return 'Invalid ' + key + ' ids or shape.'
    try:
        from . import formkit
        formkit.compile_spec(form, '_privacy_shape_check', spec)
    except Exception:
        return 'Invalid filter or preset shape.'
    return None


def _planner_env():
    """The person's own Claude, not Idli's: Idli's tools run with Idli's Claude config (CLAUDE_CONFIG_DIR, a base URL
    pointing at the private model), which would quietly send the 'Claude' plan to the private model instead."""
    return {k: v for k, v in os.environ.items()
            if k not in ('CLAUDE_CONFIG_DIR', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_MODEL',
                         'ANTHROPIC_DEFAULT_HAIKU_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL',
                         'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_SMALL_FAST_MODEL', 'CLAUDECODE')
            and not k.startswith('PASEO_')}


def _claude(prompt):
    with tempfile.TemporaryDirectory() as cwd:
        r = subprocess.run(['claude', '-p', prompt, '--model', os.environ.get('IDLI_PLANNER_MODEL', 'haiku'),
                            '--output-format', 'json', '--tools=', '--strict-mcp-config', '--mcp-config',
                            '{"mcpServers":{}}', '--setting-sources', ''],
                           cwd=cwd, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
                           env=_planner_env())
    if r.returncode:
        raise ValueError('Planner process failed')
    envelope = json.loads(r.stdout)
    if envelope.get('is_error'):
        raise ValueError('Planner returned an error')
    raw = envelope.get('result', '')
    match = re.search(r'\{.*\}', raw, re.S)
    return json.loads(match.group() if match else raw)


@locked
def plan(data_dir, file, path, tab, form, question, history, instructions=None):
    sent = ''
    attempts = []
    try:
        if get(data_dir, file)['mode'] != 'mask':
            raise ValueError('Choose mask mode before planning')
        vault = _seed(data_dir, file, path)
        scanner = Scanner()
        # Whitelist form metadata: no summary, SQL, numeric extrema, rows or answers.
        brief = {'measures': [{'id': k, 'label': v['label']} for k, v in form['_measures'].items()],
                 'group_by': [{k: g[k] for k in ('id', 'label')} for g in form['group_by']],
                 'filters': [{k: f[k] for k in ('column', 'label', 'kind', 'values') if k in f}
                             for f in form['filters']],
                 'columns': [{'id': k, 'label': (v.get('label') if isinstance(v, dict) else None) or k}
                             for k, v in (form.get('_kinds') or {}).items()],
                 'presets': [{k: p[k] for k in ('id', 'label') if k in p} for p in form.get('presets') or []]}
        thread = [{'question': h.get('question', h.get('q', '')), 'spec': h.get('spec', {})}
                  for h in (history or [])[-6:]]
        payload = {'form': brief, 'question': question, 'history': thread}
        # Preserve JSON types/structure; redact string leaves, including labels and ids.
        def clean(v):
            if isinstance(v, str):
                return _redact(v, vault, scanner)[0]
            if isinstance(v, list):
                return [clean(x) for x in v]
            if isinstance(v, dict):
                return {clean(k): clean(x) for k, x in v.items()}
            # Numeric literals in earlier specs may themselves be masked income values.
            if v is not None and normalise(str(v)) in vault.forward:
                return vault.forward[normalise(str(v))]
            return v
        payload = clean(payload)
        _save(vault)
        if instructions:
            prompt = instructions + '\n' + json.dumps(payload, ensure_ascii=False)
        else:
          prompt = ('Plan a local form query. Return JSON {"spec":{"measures":[ids],"group_by":[ids],'
                  '"filters":{column:[values]}}} or {"cannot":"reason"}. Use only supplied ids. '
                  'Keep codes exactly. Choice filters use lists or {"not":[values]}; number/date filters '
                  'use {"min":value,"max":value}; contains filters use strings. Never invent SQL.\n'
                  + json.dumps(payload, ensure_ascii=False))
        for attempt in range(2):
            if leak_check(data_dir, file, prompt):
                return {'spec': None, 'sent': sent, 'error': 'Refused: private values remain in the prompt'}
            sent = prompt  # on retry this is the exact final prompt; sent_attempts records both
            attempts.append(sent)
            got = _claude(sent)
            if got.get('cannot'):
                return {'spec': None, 'sent': sent, 'sent_attempts': attempts, 'error': 'Planner cannot express this question',
                        'why': unmask(data_dir, file, str(got['cannot']))[:300]}
            spec = unmask(data_dir, file, got.get('spec'))
            error = _shape(form, spec)
            if not error:
                return {'spec': spec, 'sent': sent, 'sent_attempts': attempts, 'error': None, 'scanner': scanner.status,
                        'note': str(got['note'])[:300] if got.get('note') else None}
            # One backtrack with a fixed shape-only message; never return local errors/data.
            prompt += ('\nPrevious spec: ' + json.dumps(got.get('spec'), ensure_ascii=False)
                       + '\nThe previous plan had an invalid shape: ' + error + ' Return a repaired JSON plan.')
        return {'spec': None, 'sent': sent, 'sent_attempts': attempts, 'error': error}
    except Exception as exc:
        return {'spec': None, 'sent': sent, 'error': 'Planner failed: ' + type(exc).__name__}


@locked
def review(data_dir, file, path, tab=None, columns=None):
    """Local-only preview, using the same stable vault and full-cell coding as export."""
    sheets, _ = fk.raw_sheets(str(path))
    tab = tab or next(iter(sheets))
    rows = suggest(path, tab)
    settings = get(data_dir, file)
    choices = {r['column']: settings['columns'].get(r['column'], r['mask']) for r in rows}
    if columns is not None:
        if not isinstance(columns, dict) or any(type(v) is not bool for v in columns.values()):
            raise ValueError('Columns must map names to booleans')
        choices.update(columns)
    vault = _vault(data_dir, file)
    coded = None
    for name, frame in sheets.items():
        preview = _code_frame(frame, choices, vault)
        if name == tab:
            coded = preview
    for row in rows:
        row['mask'] = choices[row['column']]
        row['as_sent'] = coded[row['column']].head(3).astype(str).tolist()
    return {**settings, 'columns': choices, 'tabs': list(sheets), 'tab': tab, 'suggestions': rows, 'warning': review_warning(data_dir)}


@locked
def review_warning(data_dir, files=None):
    """Count the mask-mode files in this question (or the proxy's active file set)."""
    path = Path(data_dir) / 'privacy.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    state = Path(data_dir) / '.idli/home.json'
    if files is None and state.exists():
        selected = json.loads(state.read_text()).get('files')
        if selected:
            files = [item['local'] for item in selected]
    chosen = builtins.set(files) if files is not None else builtins.set(settings)
    masked = [v for k, v in settings.items() if k in chosen and v.get('mode') == 'mask']
    if len(masked) > 10 and any(v.get('review', 'ask') == 'ask' for v in masked):
        return f'{len(masked)} files are masked for this question. Reviewing each one may take time. Consider switching review to Auto.'
    return ''
