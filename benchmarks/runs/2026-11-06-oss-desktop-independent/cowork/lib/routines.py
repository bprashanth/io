"""Routines: a team's workflow, run by Idli the same way every time (narrative/BUILDER_JOURNEY.md, "Routines").

The Builder writes <team>/extensions/routines/<name>.json and tests it on the team's TEST accounts. Idli runs it, never
Claude: Claude doesn't see the mail, the sheet or the calendar of a real run.

Steps run in order and fill a context:
- sheet:  a Google Sheet's rows                  {"type": "sheet", "role": "me", "sheet": "{config.leads_sheet}", "as": "leads"}
- mail:   unread inbox mail, opened              {"type": "mail", "role": "me", "as": "mail", "from_in": "leads.email"}
- free:   open times from the secret iCal feed   {"type": "free", "ical": "{config.ical}", "as": "slots", "days": 5,
                                                   "hours": "10:00-17:00", "minutes": 30, "count": 3}
- judge:  the private 9B, per item, with a JSON schema   {"type": "judge", "each": "mail", "prompt": "...{new_text}...",
          "schema": {...}, "as": "verdict"}. A verdict with "unclear": true goes to the person.
- script: the team's own Python (routines/<file>.py), JSON in and out  {"type": "script", "file": "lead_replies.py"}.
          It gets {"context", "memory", "mode"} on stdin and prints {"context": {...}, "memory": {...},
          "actions": [...]}.
Actions, keyed so each is done once:
- {"type": "draft_email", "key", "role", "to", "subject", "body"}  a Gmail draft; the person presses Send
- {"type": "book_event", "key", "role", "title", "start" (ISO), "minutes", "guest", "details"}  after the person's yes
- {"type": "ask_person", "key", "text"}  shown on the Runs page
State (<team>/.idli/routines/<name>/): state.json (done keys, pending approvals, the 9B's verdicts by message, the
script's memory), config.json ({"test": {...}, "real": {...}}: sheet ids, the secret iCal address), runs/<time>.json.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,40}')
STEP_TYPES = {'sheet', 'mail', 'free', 'judge', 'script'}
ACTION_TYPES = {'draft_email', 'book_event', 'ask_person'}
NEEDS_YES = {'book_event'}


def ext_dir(data_dir):
    return Path(data_dir).resolve() / 'extensions'


def routine_file(data_dir, name):
    if not NAME.fullmatch(str(name)):
        raise ValueError('A routine name is short, lowercase, with dashes.')
    return ext_dir(data_dir) / 'routines' / f'{name}.json'


def state_dir(data_dir, name):
    d = Path(data_dir).resolve() / '.idli' / 'routines' / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _write(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent)
    with os.fdopen(fd, 'w') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=str)
    os.replace(tmp, p)


def names(data_dir):
    d = ext_dir(data_dir) / 'routines'
    return sorted(p.stem for p in d.glob('*.json')) if d.is_dir() else []


def load(data_dir, name):
    p = routine_file(data_dir, name)
    if not p.is_file():
        raise ValueError(f'There is no routine {name} (routines/{name}.json).')
    try:
        return json.loads(p.read_text())
    except ValueError as exc:
        raise ValueError(f'routines/{name}.json is not valid JSON: {exc}') from None


def check(data_dir, name):
    """Problems with the routine file, in plain words (empty when fine)."""
    try:
        r = load(data_dir, name)
    except ValueError as exc:
        return [str(exc)]
    out = []
    steps = r.get('steps')
    if not isinstance(steps, list) or not steps:
        return ['It needs "steps", a list.']
    have = set()
    for i, s in enumerate(steps):
        t = s.get('type') if isinstance(s, dict) else None
        where = f'Step {i + 1}'
        if t not in STEP_TYPES:
            out.append(f'{where}: type must be one of {", ".join(sorted(STEP_TYPES))}.')
            continue
        if t in ('sheet', 'mail') and not s.get('role'):
            out.append(f'{where}: say which account ("role": "me").')
        if t == 'sheet' and not s.get('sheet'):
            out.append(f'{where}: "sheet" (a sheet id, or {{config.<key>}}).')
        if t == 'free' and s.get('via') == 'web' and not s.get('ical'):
            out.append(f'{where}: "ical" (usually {{config.ical}}), when it reads the calendar through the web.')
        if t == 'judge':
            if s.get('each') not in have:
                out.append(f'{where}: "each" must name an earlier step\'s "as".')
            if not s.get('prompt') or not isinstance(s.get('schema'), dict):
                out.append(f'{where}: a judge needs "prompt" and "schema" (JSON schema of the answer).')
            elif 'unclear' not in (s['schema'].get('properties') or {}):
                out.append(f'{where}: the schema needs an "unclear" true/false, so doubtful answers go to the person.')
        if t == 'script':
            f = ext_dir(data_dir) / 'routines' / str(s.get('file', ''))
            if not re.fullmatch(r'[a-z0-9_]+\.py', str(s.get('file', ''))) or not f.is_file():
                out.append(f'{where}: "file" must be a .py file in routines/.')
        if t != 'script' and not s.get('as'):
            out.append(f'{where}: "as" (the name its result goes under).')
        have.add(s.get('as'))
    return out


# ---- profiles and settings per mode ----

def _profile(data_dir, role, mode):
    from lib import chromeprofiles
    if mode == 'test':
        return chromeprofiles.profile_for_role(str(data_dir), role)
    return chromeprofiles.real_profile_for_role(str(data_dir), role)


def _email(data_dir, role, mode):
    """The Google account for a role: a confirmed test account in a rehearsal, the person's mapped account in real
    runs. Its Google sign-in (lib/google_api.py) must exist."""
    from lib import chromeprofiles
    if mode == 'test':
        chromeprofiles.profile_for_role(str(data_dir), role)  # checks the profile's accounts are all test accounts
        row = next(r for r in chromeprofiles.test_accounts(str(data_dir)) if r['role'] == role)
        return row['email']
    raw = _read(Path(data_dir).resolve() / '.idli' / 'real-accounts.json', {})
    row = next((r for r in raw.get('accounts') or [] if r.get('role') == role), None)
    if not row or not row.get('email'):
        raise ValueError('This routine runs on your real Google account, and that is not connected in Idli yet.')
    return row['email']


def config(data_dir, name, mode):
    return _read(state_dir(data_dir, name) / 'config.json', {}).get(mode, {})


def set_config(data_dir, name, mode, key, value):
    if mode not in ('test', 'real') or not re.fullmatch(r'[a-z0-9_]{1,40}', str(key)):
        raise ValueError('Use mode test or real, and a short lowercase key.')
    p = state_dir(data_dir, name) / 'config.json'
    c = _read(p, {})
    c.setdefault(mode, {})[key] = value
    _write(p, c)
    return sorted(c[mode])


def _fill(value, cfg):
    def one(m):
        if m.group(1) not in cfg:
            raise ValueError(f'The routine needs the setting {m.group(1)}, which is not set yet.')
        return str(cfg[m.group(1)])
    return re.sub(r'\{config\.([a-z0-9_]+)\}', one, value) if isinstance(value, str) else value


# ---- the private 9B ----

def judge(prompt, schema, timeout=120, max_tokens=400):
    """One answer from the private 9B, shaped by the JSON schema."""
    from lib import stackwall
    base, headers, model = stackwall.model_upstream()
    body = {'model': model, 'temperature': 0, 'stream': False, 'max_tokens': int(max_tokens),
            'messages': [{'role': 'system', 'content': 'Answer with JSON only, matching the schema. If you are not '
                          'sure, set "unclear" to true.'}, {'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'schema': schema}},
            'chat_template_kwargs': {'enable_thinking': False}}
    req = urllib.request.Request(base + '/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={**headers, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.load(r)['choices'][0]['message']['content']
    m = re.search(r'\{.*\}', text, re.S)
    try:
        out = json.loads(m.group(0) if m else text)
    except ValueError:
        return {'unclear': True, 'why': 'The private model did not answer in the expected shape.'}
    return out if isinstance(out, dict) else {'unclear': True}


def _format(prompt, item, context):
    flat = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
            for k, v in {**{k: v for k, v in context.items() if not isinstance(v, list)}, **item}.items()}
    return re.sub(r'\{([a-z_][a-z0-9_]*)\}', lambda m: str(flat.get(m.group(1), '')), prompt)


# ---- running ----

class Run:
    def __init__(self, data_dir, name, mode='test', dry_run=False, browsers=None, judge_fn=None):
        self.data_dir, self.name, self.mode, self.dry_run = Path(data_dir).resolve(), name, mode, dry_run
        self.routine = load(data_dir, name)
        self.cfg = config(data_dir, name, mode)
        self.state_path = state_dir(data_dir, name) / 'state.json'
        self.state = _read(self.state_path, {})
        for k in ('done', 'pending', 'judged', 'memory', 'asks'):
            self.state.setdefault(k, {})
        self.browsers = browsers if browsers is not None else {}  # role -> Browser (tests pass fakes)
        self.judge_fn = judge_fn or judge
        self.emails = {}
        self.log = {'routine': name, 'mode': mode, 'dry_run': dry_run, 'started': _now(), 'steps': [], 'actions': []}
        self.context = {}

    def browser(self, role):
        if role not in self.browsers:
            from lib import chromeprofiles, chromectl
            self.browsers[role] = chromectl.Browser(port=chromeprofiles.open_for_work(_profile(self.data_dir, role,
                                                                                              self.mode)))
        return self.browsers[role]

    def email(self, role):
        if role not in self.emails:
            self.emails[role] = _email(self.data_dir, role, self.mode)
        return self.emails[role]

    def step(self, s):
        from lib import google_api as api, google_web as g
        t, key = s['type'], s.get('as')
        web = s.get('via') == 'web'  # Google's web pages instead of its APIs: only when a step asks for it
        if t == 'sheet' and not web:
            rows = api.sheet_values(self.email(s['role']), _fill(s['sheet'], self.cfg), s.get('range', 'A:ZZ'))
            self.context[key] = [{(k or '').strip().lower(): (v or '').strip() for k, v in r.items()} for r in rows]
            return f'{len(rows)} rows'
        if t == 'mail' and not web:
            who = self.email(s['role'])
            allow = None
            if s.get('from_in'):
                src, col = s['from_in'].split('.', 1)
                allow = {str(r.get(col, '')).strip().lower() for r in self.context.get(src, [])} - {''}
            q = f'newer_than:{int(s.get("days", 7))}d -label:{api.HANDLED.replace("/", "-")} -in:sent -in:drafts'
            found = []
            senders = sorted(allow or [])
            for i in range(0, len(senders), 20) if allow is not None else [None]:
                part = q if i is None else f'from:({" OR ".join(senders[i:i + 20])}) ' + q
                found += [] if allow == set() else api.gmail_list(who, part, 100)
            seen = self.state.setdefault('seen', {})
            msgs, old, skipped = [], 0, 0
            for m in {m['id']: m for m in found}.values():
                if m['id'] in seen:
                    old += 1
                    continue
                msg = api.gmail_raw(who, m['id'])
                if allow is not None and msg['from'] not in allow:
                    skipped += 1
                    continue
                msgs.append(msg)
            msgs.sort(key=lambda m: m.get('date', ''))
            self._new_seen = [m['id'] for m in msgs]
            self._handled_by = who
            self.context[key] = msgs
            return f'{len(msgs)} new from the list, {old} seen before' + (f', {skipped} from others' if skipped else '')
        if t == 'free' and not web:
            now = dt.datetime.now().astimezone()
            busy = api.calendar_freebusy(self.email(s.get('role', 'me')), now, now + dt.timedelta(days=int(s.get('days', 5)) + 7))
            slots = g.free_slots(busy, days=s.get('days', 5), hours=s.get('hours', '10:00-17:00'),
                                 minutes=s.get('minutes', 30), count=s.get('count', 3))
            self.context[key] = [{'start': t.isoformat(), 'label': g.slot_label(t)} for t in slots]
            return f'{len(slots)} open times'
        if t == 'sheet':
            rows = g.sheet_rows(self.browser(s['role']), _fill(s['sheet'], self.cfg), s.get('gid'))
            self.context[key] = [{(k or '').strip().lower(): (v or '').strip() for k, v in r.items()} for r in rows]
            return f'{len(rows)} rows'
        if t == 'mail':
            b = self.browser(s['role'])
            allow = None
            if s.get('from_in'):
                src, col = s['from_in'].split('.', 1)
                allow = {str(r.get(col, '')).strip().lower() for r in self.context.get(src, [])} - {''}
            # with a list of senders: Gmail's search, read or unread; else the unread inbox
            found = g.mail_search(b, sorted(allow), s.get('days', 7)) if allow else ([] if allow is not None
                                                                                     else g.mail_feed(b))
            msgs, skipped, old = [], 0, 0
            seen = self.state.setdefault('seen', {})
            for m in found:
                if m['id'] in seen and not s.get('reread'):
                    old += 1
                    continue
                msg = g.mail_message(b, m['id'])
                if allow is not None and msg['from'] not in allow:
                    skipped += 1  # the thread's last message is someone else's (often your own reply)
                    continue
                msgs.append(msg)
            self._new_seen = [m['id'] for m in msgs]  # marked seen only when the whole run went through
            self.context[key] = msgs
            return f'{len(msgs)} new from the list, {old} seen before, {skipped} last answered by someone else'
        if t == 'free':
            busy = g.ical_busy(_fill(s['ical'], self.cfg))
            slots = g.free_slots(busy, days=s.get('days', 5), hours=s.get('hours', '10:00-17:00'),
                                 minutes=s.get('minutes', 30), count=s.get('count', 3))
            self.context[key] = [{'start': t.isoformat(), 'label': g.slot_label(t)} for t in slots]
            return f'{len(slots)} open times'
        if t == 'judge':
            n = unclear = 0
            for item in self.context.get(s['each'], []):
                cache = f'{item.get("id", "")}:{s.get("as")}'
                if cache in self.state['judged']:
                    item[key] = self.state['judged'][cache]
                else:
                    item[key] = self.judge_fn(_format(s['prompt'], item, self.context), s['schema'])
                    if not self.dry_run:
                        self.state['judged'][cache] = item[key]
                    n += 1
                if item[key].get('unclear'):
                    unclear += 1
                    self._ask(f'unclear:{item.get("id", "")}', f'Please read: "{item.get("subject", "")}" from '
                              f'{item.get("from", "")}. The private model was not sure what it says.')
            return f'{n} read by the private model, {unclear} unclear (sent to you)'
        if t == 'script':
            out = self._script(s['file'])
            self.context.update(out.get('context') or {})
            if isinstance(out.get('memory'), dict):
                self.state['memory'] = out['memory']
            acts = out.get('actions') or []
            for a in acts:
                self.action(a)
            return f'{len(acts)} actions'

    def _script(self, file):
        path = ext_dir(self.data_dir) / 'routines' / file
        payload = json.dumps({'context': self.context, 'memory': self.state['memory'], 'mode': self.mode,
                              'now': _now()}, default=str, ensure_ascii=False)
        env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(tempfile.gettempdir()), 'LANG': 'C.UTF-8',
               'PYTHONUTF8': '1', 'TZ': os.environ.get('TZ', '')}
        # TODO(wall): on Linux run this inside stackwall's run wall (no network), as readers are.
        res = subprocess.run([sys.executable, '-I', str(path)], input=payload, capture_output=True, text=True,
                             timeout=120, env=env, cwd=str(ext_dir(self.data_dir)))
        if res.returncode != 0:
            raise ValueError(f'routines/{file} failed: {res.stderr.strip()[-400:]}')
        try:
            out = json.loads(res.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise ValueError(f'routines/{file} must print one JSON object as its last line.') from None
        return out if isinstance(out, dict) else {}

    def _ask(self, key, text):
        if key not in self.state['done'] and key not in self.state['asks']:
            self.state['asks'][key] = {'text': text, 'at': _now()}

    def action(self, a):
        t, key = a.get('type'), str(a.get('key') or '')
        if t not in ACTION_TYPES or not key:
            self.log['actions'].append({'key': key, 'type': t, 'result': 'ignored: needs a known type and a key'})
            return
        if key in self.state['done'] or key in self.state['pending']:
            self.log['actions'].append({'key': key, 'type': t, 'result': 'already done'})
            return
        if t == 'ask_person':
            self._ask(key, a.get('text', ''))
            self.log['actions'].append({'key': key, 'type': t, 'result': 'shown to you'})
            return
        if t in NEEDS_YES and not self.approve_all:
            if not self.dry_run:
                self.state['pending'][key] = {**a, 'mode': self.mode, 'at': _now()}
            self.log['actions'].append({'key': key, 'type': t, 'result': 'waiting for your yes'})
            return
        self.log['actions'].append({'key': key, 'type': t, 'result': self.do(a)})

    approve_all = False

    def do(self, a):
        """Carry out one action (a draft, or a booking the person approved)."""
        from lib import google_web as g
        if self.dry_run:
            return 'would do (dry run)'
        key = a['key']
        from lib import google_api as api
        web = a.get('via') == 'web'
        if a['type'] == 'draft_email':
            if web:
                g.compose_draft(self.browser(a.get('role', 'me')), a['to'], a['subject'], a['body'])
            else:
                reply = self._reply_target(a)
                api.gmail_create_draft(self.email(a.get('role', 'me')), a['to'], a['subject'], a['body'],
                                       thread_id=reply.get('thread'), in_reply_to=reply.get('message_id'), key=key)
            result = 'draft saved (you press Send)'
        elif a['type'] == 'book_event':
            start = dt.datetime.fromisoformat(a['start'])
            if web:
                g.calendar_event(self.browser(a.get('role', 'me')), a['title'], start, int(a.get('minutes', 30)),
                                 a['guest'], a.get('details', ''))
            else:
                api.calendar_insert(self.email(a.get('role', 'me')), a['title'], start, int(a.get('minutes', 30)),
                                    [a['guest']], a.get('details', ''), key=key)
            result = 'booked, invitation sent'
        else:
            return 'nothing to do'
        self.state['done'][key] = {'type': a['type'], 'at': _now(), 'result': result,
                                   'summary': _summary(a)}
        self.state['pending'].pop(key, None)
        self.save()
        return result

    def _reply_target(self, a):
        """The message a draft answers: "reply_to" (a message id) if the script gave it, else the newest message in
        this run from that person with the same subject."""
        mail = [m for v in self.context.values() if isinstance(v, list) for m in v if isinstance(m, dict) and 'thread' in m]
        if a.get('reply_to'):
            return next((m for m in mail if m.get('id') == a['reply_to']), {})
        bare = lambda x: re.sub(r'(?i)^\s*((re|fwd?):\s*)+', '', str(x or '')).strip().lower()  # noqa: E731
        hits = [m for m in mail if m.get('from') == str(a.get('to', '')).lower() and bare(m.get('subject')) == bare(a.get('subject'))]
        return max(hits, key=lambda m: m.get('date', '')) if hits else {}

    def save(self):
        if not self.dry_run:
            _write(self.state_path, self.state)

    def go(self):
        try:
            for s in self.routine['steps']:
                t0 = time.time()
                try:
                    note = self.step(s)
                except Exception as exc:
                    self.log['steps'].append({'step': s.get('as') or s.get('file'), 'type': s['type'], 'ok': False,
                                              'note': str(exc)[:300], 'seconds': round(time.time() - t0, 1)})
                    self.log['ok'] = False
                    break
                self.log['steps'].append({'step': s.get('as') or s.get('file'), 'type': s['type'], 'ok': True,
                                          'note': note, 'seconds': round(time.time() - t0, 1)})
            else:
                self.log['ok'] = True
                if not self.dry_run:
                    for mid in getattr(self, '_new_seen', []):
                        self.state.setdefault('seen', {})[mid] = _now()
                    if getattr(self, '_handled_by', None) and self._new_seen:
                        from lib import google_api
                        google_api.gmail_mark_handled(self._handled_by, self._new_seen)
        finally:
            self.log['finished'] = _now()
            self.save()
            if not self.dry_run:
                _write(state_dir(self.data_dir, self.name) / 'runs' / (self.log['started'].replace(':', '') + '.json'),
                       self.log)
        return self.log


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def _summary(a):
    if a['type'] == 'draft_email':
        return f'Draft to {a.get("to", "")}: {a.get("subject", "")}'
    if a['type'] == 'book_event':
        try:
            when = dt.datetime.fromisoformat(a['start'])
            from lib import google_web as g
            when = g.slot_label(when)
        except (ValueError, KeyError):
            when = a.get('start', '')
        return f'{a.get("title", "Meeting")} with {a.get("guest", "")}, {when}'
    return a.get('text', '')


def run(data_dir, name, mode='test', dry_run=False, approve_all=False, **kw):
    problems = check(data_dir, name)
    if problems:
        raise ValueError('The routine has problems: ' + ' '.join(problems))
    if approve_all and mode != 'test':
        raise ValueError('Only a rehearsal on test accounts can skip the person\'s yes.')
    r = Run(data_dir, name, mode, dry_run, **kw)
    r.approve_all = approve_all
    return r.go()


def overview(data_dir):
    """For the Runs page: each routine with its last runs, what waits for a yes, and what to read."""
    out = []
    for name in names(data_dir):
        sd = state_dir(data_dir, name)
        st = _read(sd / 'state.json', {})
        runs = sorted((sd / 'runs').glob('*.json'), reverse=True)[:5] if (sd / 'runs').is_dir() else []
        r = _read(routine_file(data_dir, name), {})
        out.append({'name': name, 'title': r.get('title') or name, 'about': r.get('about', ''),
                    'pending': [{'key': k, 'summary': _summary(v), 'type': v.get('type')}
                                for k, v in (st.get('pending') or {}).items()],
                    'asks': [{'key': k, 'text': v.get('text', '')} for k, v in (st.get('asks') or {}).items()],
                    'done': sorted(({'key': k, **v} for k, v in (st.get('done') or {}).items()),
                                   key=lambda x: x.get('at', ''), reverse=True)[:10],
                    'runs': [_read(p, {}) for p in runs],
                    'real_ready': bool(config(data_dir, name, 'real'))})
    return out


def decide(data_dir, name, key, yes, mode='test', browsers=None):
    """The person's answer to a pending action (yes: do it now) or to a question (either answer clears it)."""
    st_path = state_dir(data_dir, name) / 'state.json'
    st = _read(st_path, {})
    if key in (st.get('asks') or {}):
        st['asks'].pop(key)
        st.setdefault('done', {})[key] = {'type': 'ask_person', 'at': _now(), 'result': 'read by you'}
        _write(st_path, st)
        return {'ok': True}
    a = (st.get('pending') or {}).get(key)
    if not a:
        raise ValueError('That is no longer waiting.')
    if not yes:
        st['pending'].pop(key)
        st.setdefault('done', {})[key] = {'type': a['type'], 'at': _now(), 'result': 'skipped by you',
                                         'summary': _summary(a)}
        _write(st_path, st)
        return {'ok': True, 'result': 'skipped'}
    r = Run(data_dir, name, a.get('mode') or mode, browsers=browsers)
    return {'ok': True, 'result': r.do(a)}
