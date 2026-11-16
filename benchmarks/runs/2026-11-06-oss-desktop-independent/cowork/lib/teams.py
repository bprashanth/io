"""Start here > Teams: make a team by answering a few questions. Idli asks (code, with the local 9B only reading
free-text answers); nothing here goes to Claude. The PoC makes one kind of team: a Drivey clone with its own name,
folder and Minis (narrative/DRIVEY_JOURNEY.md, part D).

Two halves:
  route(events, check)  the conversation, run by the chat router (lib/modes.py) on each turn. It rebuilds the state
                        from the chat's own history, so it never trusts anything but what was said and clicked.
  create(spec)          the setup, run by the team_create tool on the person's computer: folder, instructions, tools,
                        the sidebar heading. Its "New chat" row opens the two halves (Paseo patch P20).
"""
import functools
import json
import os
import re
import shutil
import subprocess
import urllib.request

TEAMS_CHAT = 'Teams'  # the Teams chat's first message (desktop/idli-bootstrap.py)
MAKE = 'Make a team'  # what the Make a team button sends (lib/teams.html)
EXAMPLE_GOAL = 'Lower household debt in 12 villages'
# Drivey's tools (desktop/idli-bootstrap.py TOOLSETS["Drivey"]): a team is a Drivey clone
TEAM_TOOLS = ['drive_fetch', 'privacy_review_open', 'claude_handoff', 'mini_open', 'mini_ask', 'binder_item']
SITES = 'google\nfiles\n'
RESERVED = {'start here', 'drivey', 'whatsappy', 'canvay', 'claude', 'claude code', 'logins', 'privacy', 'teams'}

DATA = [('Google Drive', 'Sheets and Excel files in Drive.'),
        ('On this computer', 'Excel or CSV files.'),
        ('Somewhere else', 'For example KoBo, Zoho or paper.')]
PEOPLE = [('Just me', 'Others can join later.'),
          ('A few of us', 'Two to five people.'),
          ('The whole team', 'More than five people.')]
PRIVATE = [('Yes', 'Idli turns them into codes before Claude sees them.'),
           ('No', 'Idli still checks each file.'),
           ('Not sure', 'Idli checks each file for you.')]
OUTSIDE = [('Yes, ask me each time', 'It gets the question and column names. Never rows.'),
           ('No', 'Questions stay on this computer.')]
CHANGE = [('Name', ''), ('Goal', ''), ('Outside service', ''), ('Who uses it', '')]
SETUP = [('Set it up', ''), ('Change something', 'Go back to a question.')]

TRYING = re.compile(r"(?i)\b(test(ing)?|trying|try(ing)? (it )?out|just (looking|checking|exploring)|demo|"
                    r"not (yet|now)|from (the )?it\b|it team|it department|next (week|month)|pilot)\b")
STOP = re.compile(r"(?i)^\s*(cancel|stop|quit|exit|never ?mind|forget it|no thanks)\b[\s.!]*$")
RESTART = re.compile(r"(?i)\b(start (again|over)|restart|from the (start|beginning))\b")
NAME_OK = re.compile(r"^[\w][\w &'.-]{0,29}$")
NOT_NAMES = {'hello', 'hi', 'hey', 'hii', 'ok', 'okay', 'yes', 'no', 'yeah', 'sure', 'thanks', 'thank you',
             'namaste', 'test', 'testing', 'asdf', 'idk', 'team', 'name', 'none', 'nothing', 'skip', 'good morning',
             'good afternoon', 'good evening', 'start', 'go', 'next', 'help'}
HELP = [
    (re.compile(r"(?i)\bwhat('?s| is) (a|this) team\b|\bwhat are teams\b"),
     'A team is a heading in your sidebar for one kind of work. It has its own chats and Minis.'),
    (re.compile(r"(?i)\bwhat('?s| is) (a )?mini\b"),
     'A Mini is a small saved analysis. Your team can ask it questions on this computer.'),
    (re.compile(r"(?i)\bhow long\b"), 'About a minute.'),
    (re.compile(r"(?i)\b(outside|query) service\b|\bwhat service\b|\bdeepseek\b"),
     'A service online that writes a query for a new question. It gets the question and column names, never rows. '
     'The query runs on this computer.'),
    (re.compile(r"(?i)\bwhat (do you|does it|does that|do) mean\b|\bwhy (do you|does it) (need|ask)\b"),
     'It decides how Idli sets up the team. You can change it before it is set up.'),
    (re.compile(r"(?i)\b(change|rename) (it|this|that)? ?later\b|\bcan i change\b"),
     'Yes. You can change it before it is set up.'),
    (re.compile(r"(?i)\b(does|will) (this|it|anything) (go|get sent) (to|online)|\bwho (sees|can see)\b|"
                r"\bsent to claude\b"),
     'Nothing you type here leaves this computer. Claude is not part of this.'),
]

ASK_NAME = "What's your team called?"


def ask_goal(name):
    return f'What does {name} work towards? One line is enough.'


# ---------------------------------------------------------------- reading free text (the local 9B, then rules)
def _nine(system, text, schema):
    """The local 9B's JSON for one short answer, or None (it is down, slow or unsure: the rules decide)."""
    url = (os.environ.get('IDLI_9B_URL') or 'http://127.0.0.1:8291').rstrip('/')
    payload = {'model': 'qwen3.5-9b', 'temperature': 0, 'max_tokens': 200,
               'chat_template_kwargs': {'enable_thinking': False},
               'messages': [{'role': 'system', 'content': system + ' Return JSON only.'},
                            {'role': 'user', 'content': str(text)[:1000]}],
               'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'schema': schema}}}
    try:
        req = urllib.request.Request(url + '/v1/chat/completions', json.dumps(payload).encode(),
                                     {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=float(os.environ.get('IDLI_TEAMS_9B_TIMEOUT', '25'))) as r:
            out = json.loads(json.load(r)['choices'][0]['message']['content'])
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _clean_name(s):
    s = ' '.join(str(s or '').replace('"', ' ').replace('`', ' ').split()).strip(" .,!:;'")
    s = re.sub(r"(?i)^(the|our|my)\s+", '', s)
    if len(s.split()) > 1:
        s = re.sub(r"(?i)\s+team$", '', s)
        s = re.sub(r"(?i)^team\s+", '', s)
    if not s or not NAME_OK.match(s) or s.lower() in NOT_NAMES:
        return None
    return s[:1].upper() + s[1:]


@functools.lru_cache(maxsize=512)
def read_name(text):
    """{'name': str|None, 'trying': bool} from what they typed for the team's name."""
    t = ' '.join(str(text).split())
    trying = bool(TRYING.search(t))
    m = re.search(r"(?i)\b(?:call(?:ed)? (?:it|us|this|the team)?|name(?:d)? (?:it|is)?|it'?s|we'?re(?: called)?|"
                  r"we are(?: called)?|team is)\s+[\"']?([\w][\w &'.-]{0,29}?)[\"']?\s*(?:team)?[.!]?$", t)
    if m and not trying:
        return {'name': _clean_name(m.group(1)), 'trying': False}
    words = t.split()
    if len(words) <= 3 and not trying and not re.search(r"(?i)\b(i|i'm|im|we|not|don'?t|no|yes|what|how|why)\b", t):
        return {'name': _clean_name(t), 'trying': False}
    out = _nine('A person is naming a team in an app. Give the team name they asked for, as they wrote it, at most '
                '4 words, without the word team ("call it Insights" gives "Insights"; "we are the M&E team" gives '
                '"M&E"). If they gave no name (for example "I am from IT, just testing"), name is null. trying_out '
                'is true if they say they are testing, trying it out, or setting it up for others.', t,
                {'type': 'object', 'properties': {'name': {'type': ['string', 'null']},
                                                  'trying_out': {'type': 'boolean'}},
                 'required': ['name', 'trying_out'], 'additionalProperties': False})
    name = _clean_name(out.get('name')) if out else None
    if name and name.lower() not in t.lower():  # only a name they actually typed
        name = None
    return {'name': name, 'trying': trying or bool(out and out.get('trying_out'))}


FILLER = re.compile(r"(?i)^(?:ok(?:ay)?|so|well|actually|um+|hmm+|basically|honestly|yes|yeah|i think|i guess|"
                    r"it'?s|it is|we(?:'re| are)|our team|the team|we)\b[\s,:;.-]*")


def _unfill(t):
    """Drop spoken lead-ins: "ok so: actually it's helping..." -> "helping..."."""
    for _ in range(6):
        cut = FILLER.sub('', t, count=1)
        if cut == t or not cut.strip():
            break
        t = cut
    return t[:1].upper() + t[1:] if t else t


@functools.lru_cache(maxsize=512)
def read_goal(text):
    """{'goal': str|None, 'trying': bool} from what they typed for what the team works towards."""
    t = _unfill(' '.join(str(text).split()))
    trying = bool(TRYING.search(t))
    vague = re.search(r"(?i)\b(not sure|don'?t know|dunno|no idea|skip|later|nothing|n/?a|none)\b", t)
    if not trying and not vague and t.strip(' .!?').lower() not in NOT_NAMES and re.search(r'\w\w', t):
        return {'goal': t[:140].rstrip(' .'), 'trying': False}
    if vague and not trying and len(t.split()) <= 4:
        return {'goal': None, 'trying': False}
    out = _nine('A person is describing what their team works towards. Give it as one short line in their own words '
                '(at most 14 words). If they did not say (for example "just testing", "not sure", "I am in IT"), '
                'goal is null. trying_out is true if they say they are testing or trying it out.', t,
                {'type': 'object', 'properties': {'goal': {'type': ['string', 'null']},
                                                  'trying_out': {'type': 'boolean'}},
                 'required': ['goal', 'trying_out'], 'additionalProperties': False})
    goal = ' '.join(str(out.get('goal') or '').split())[:140].rstrip(' .') if out else ''
    return {'goal': goal or None, 'trying': trying or bool(out and out.get('trying_out'))}


KEYWORDS = {
    'Data': [(r'\b(drive|google|sheets?|gsheet)\b', 'Google Drive'),
             (r'\b(computer|laptop|desktop|excel|csv|xlsx|folder|pc)\b', 'On this computer'),
             (r'\b(kobo|odk|zoho|paper|register|tally|salesforce|form|app|somewhere|whatsapp|email)\b',
              'Somewhere else')],
    'People': [(r"\b(just|only) me\b|\bmyself\b|\balone\b|\bsingle person\b|\bone person\b|\bsolo\b|\bi am the "
                r"(only|single)\b|\bonly one\b", 'Just me'),
               (r'\b(few|couple|two|three|four|five|2|3|4|5|colleagues?|small)\b', 'A few of us'),
               (r'\b(whole|everyone|all|entire|team|staff|many|lots|10|20|\d{2,})\b', 'The whole team')],
    'Private': [(r"\b(not sure|unsure|don'?t know|maybe|no idea|check)\b", 'Not sure'),
                (r'\b(no|none|nope|anonymi[sz]ed|no names)\b', 'No'),
                (r'\b(yes|yeah|yep|names?|phones?|numbers?|villages?|places?|addresses?|aadhaar|personal)\b', 'Yes')],
    'Outside service': [(r"\b(no|nope|don'?t|never|not)\b", 'No'),
                        (r'\b(yes|ok|okay|sure|fine|yeah|yep|allow)\b', 'Yes, ask me each time')],
    'Change': [(r'\b(name|call|rename)\b', 'Name'), (r'\b(goal|towards|aim|purpose|mission)\b', 'Goal'),
               (r'\b(outside|service|online|deepseek)\b', 'Outside service'),
               (r'\b(who|people|use|users?|colleagues?|team size)\b', 'Who uses it')],
    'Set up': [(r'\b(change|edit|back|wrong|fix)\b', 'Change something'),
               (r'\b(yes|set|go|ok|okay|sure|do it|create|make|looks good|fine|done)\b', 'Set it up')],
}
OPTIONS = {'Data': DATA, 'People': PEOPLE, 'Private': PRIVATE, 'Outside service': OUTSIDE, 'Change': CHANGE,
           'Set up': SETUP}


@functools.lru_cache(maxsize=512)
def read_choice(header, text):
    """{'choice': label|None, 'trying': bool} for an answer typed instead of clicked."""
    t = ' '.join(str(text).split())
    labels = [a for a, _ in OPTIONS[header]]
    exact = next((a for a in labels if a.lower() == t.lower().strip(' .!')), None)
    trying = bool(TRYING.search(t))
    if exact:
        return {'choice': exact, 'trying': trying}
    for pattern, label in KEYWORDS.get(header, []):
        if re.search('(?i)' + pattern, t):
            return {'choice': label, 'trying': trying}
    out = _nine('A person answered a multiple-choice question in their own words. Pick the option they mean, or null '
                'if none fits. trying_out is true if they say they are testing or trying it out.\nOptions: ' +
                json.dumps(labels), t,
                {'type': 'object', 'properties': {'choice': {'enum': labels + [None]},
                                                  'trying_out': {'type': 'boolean'}},
                 'required': ['choice', 'trying_out'], 'additionalProperties': False})
    return {'choice': out.get('choice') if out and out.get('choice') in labels else None,
            'trying': trying or bool(out and out.get('trying_out'))}


# ---------------------------------------------------------------- the conversation
def _answers(inp, text, card_answers):
    a = (card_answers(inp, text or '') or [None])[0]
    return a.strip() if isinstance(a, str) and a.strip() else None


ORDER = ('name', 'goal', 'data', 'people', 'private', 'outside')


def _next(st):
    for k in ORDER:
        if k not in st:
            return k
    return 'plan'


def replay(events, card_answers):
    """The team so far, from this chat's history since the last Make a team."""
    start = max((i for i, e in enumerate(events) if e[0] == 'said' and e[1].strip() == MAKE), default=None)
    if start is None:
        return None
    st = {'notes': []}
    for e in events[start + 1:]:
        st.pop('help', None)
        st.pop('nudge', None)
        if e[0] == 'said':
            _typed(st, e[1])
            continue
        _, name, inp, res = e
        if name == 'team_check':
            if res.get('ok'):
                st['name'] = res.get('name') or inp.get('name')
            else:
                st.pop('name', None)
                st['taken'] = res.get('error') or 'That name is taken. Pick another name.'
        elif name == 'team_create':
            if res.get('ok'):
                st['done'] = res
            else:
                st['failed'] = res.get('error') or 'Could not set it up.'
                if res.get('taken'):
                    st.pop('name', None)
                    st['taken'] = res['error']
        elif name == 'AskUserQuestion':
            head = (inp.get('questions') or [{}])[0].get('header')
            answer = _answers(inp, res.get('text'), card_answers)
            if answer:
                _card(st, head, answer)
    return st


def _typed(st, text):
    """Something typed in the chat: an answer to whatever is being asked now, or a word about the flow."""
    t = ' '.join(text.split())
    if st.get('done'):
        st['after'] = True
        return
    if STOP.match(t):
        st['stopped'] = True
        return
    if RESTART.search(t):
        st.clear()
        st['notes'] = []
        return
    for pattern, reply in HELP:
        if pattern.search(t) and (t.endswith('?') or len(t.split()) <= 6):
            st['help'] = reply
            return
    st.pop('stopped', None)
    step = st.get('expect') or _next(st)
    if step == 'name' or st.get('wants_name'):
        r = read_name(t)
        st['trying'] = st.get('trying') or r['trying']
        st.pop('wants_name', None)
        st.pop('taken', None)
        if r['name'] and r['name'].lower() in RESERVED:
            st['taken'] = f'{r["name"]} is already in your sidebar. Pick another name.'
        elif r['name']:
            st['proposed'] = r['name']
        else:
            st['no_name'] = True
        st.pop('expect', None)
        return
    if step == 'goal':
        r = read_goal(t)
        st['trying'] = st.get('trying') or r['trying']
        if r['goal']:
            st['goal'] = r['goal']
            st.pop('no_goal', None)
        else:
            st['no_goal'] = True
        st.pop('expect', None)
        return
    header = {'data': 'Data', 'people': 'People', 'private': 'Private', 'outside': 'Outside service',
              'plan': 'Set up', 'change': 'Change'}.get(step)
    if header:
        _card(st, header, t)


def _card(st, head, answer):
    labels = {a for a, _ in OPTIONS.get(head, [])} | {'Insights', 'Something else', 'Use an example', 'Leave it blank'}
    if head == 'Name':
        if answer == 'Insights':
            st['proposed'] = 'Insights'
        elif answer == 'Something else':
            st['wants_name'] = True
            st['expect'] = 'name'
        else:
            _typed_name(st, answer)
        st.pop('no_name', None)
        return
    if head == 'Goal':
        if answer == 'Use an example':
            st['goal'] = EXAMPLE_GOAL
        elif answer == 'Leave it blank':
            st['goal'] = ''
        else:
            r = read_goal(answer)
            st['goal'] = r['goal'] or ''
        st.pop('no_goal', None)
        return
    if head not in OPTIONS:
        return
    if STOP.match(answer):
        st['stopped'] = True
        return
    if RESTART.search(answer):
        st.clear()
        st['notes'] = []
        return
    for pattern, reply in HELP:
        if pattern.search(answer) and (answer.rstrip().endswith('?') or len(answer.split()) <= 6):
            st['help'] = reply
            return
    if answer in labels:
        choice, trying = answer, False
    else:
        r = read_choice(head, answer)
        choice, trying = r['choice'], r['trying']
        if answer.strip():
            st['notes'].append(answer.strip()[:200])
    st['trying'] = st.get('trying') or trying
    if not choice:
        st['nudge'] = head
        return
    if head == 'Data':
        st['data'] = choice
    elif head == 'People':
        st['people'] = choice
    elif head == 'Private':
        st['private'] = choice
    elif head == 'Outside service':
        st['outside'] = choice != 'No'
    elif head == 'Set up':
        if choice == 'Set it up':
            st['go'] = True
            st.pop('failed', None)
        else:
            st['expect'] = 'change'
    elif head == 'Change':
        st.pop('expect', None)
        key = {'Name': 'name', 'Goal': 'goal', 'Outside service': 'outside', 'Who uses it': 'people'}[choice]
        st.pop(key, None)
        st.pop('go', None)
        if key == 'name':
            st.pop('proposed', None)
            st['wants_name'] = True
            st['expect'] = 'name'


def _typed_name(st, text):
    r = read_name(text)
    st['trying'] = st.get('trying') or r['trying']
    if r['name'] and r['name'].lower() in RESERVED:
        st['taken'] = f'{r["name"]} is already in your sidebar. Pick another name.'
    elif r['name']:
        st['proposed'] = r['name']
    else:
        st['no_name'] = True


def plan_text(st):
    name = st['name']
    lines = [f'**{name}**']
    if st.get('goal'):
        goal = st['goal']
        lines.append(f'Works towards: {goal[:1].upper() + goal[1:]}.')
    lines.append('')
    lines.append(f'- Its own heading in your sidebar. Ask on the left, Claude helps on the right.')
    lines.append('- Files come from Google Drive and stay on this computer.')
    lines.append('- Names, places and phone numbers go to Claude as codes.' if st.get('private') != 'No' else
                 '- Idli still checks each file. Any names go to Claude as codes.')
    lines.append('- Minis answer on this computer. New questions go to an outside service only if you say yes.'
                 if st.get('outside') else '- Minis answer on this computer. New questions stay here too.')
    if st.get('people') == 'Just me' or st.get('trying'):
        lines.append('- For you for now. Others can join later.')
    elif st.get('people'):
        lines.append('- For your team. Each person uses their own Google login.')
    return '\n'.join(lines)


def spec_of(st):
    return {'name': st['name'], 'goal': st.get('goal') or '', 'data': st.get('data') or 'Google Drive',
            'people': st.get('people') or 'Just me', 'private': st.get('private') or 'Not sure',
            'outside': bool(st.get('outside')), 'trying': bool(st.get('trying')), 'notes': st.get('notes', [])[:6]}


def route(events, card_answers, has_tools):
    """The next step: ('say', text) | ('card', header, question, options, lead) | ('call', tool, args, lead) | None.
    events: lib/modes._events of the chat. has_tools: the Teams tools this chat has."""
    if not events or events[0] != ('said', TEAMS_CHAT):
        return None
    last = events[-1]
    if last == ('said', TEAMS_CHAT) or (last[0] == 'tool' and last[1] == 'team_page' and last[3].get('error')
                                        and len(events) < 3):
        return ('call', 'team_page', {}, None)
    if last[0] == 'tool' and last[1] == 'team_page':
        return ('say', last[3].get('reply') or last[3].get('error') or 'Send any word to show the Make a team '
                                                                          'button again.')
    st = replay(events, card_answers)
    if st is None:
        return ('call', 'team_page', {}, None)
    if st.get('done'):
        d = st['done']
        if st.get('after'):
            return ('say', f'{d.get("name")} is set up. To make another team, click Make a team above.')
        return ('say', f'{d.get("name")} is ready. It is in your sidebar.\n\nTo start, click **New chat** under '
                       f'{d.get("name")}. Then type @ to pick a sheet from Drive and ask a question about it. A good '
                       'answer can become your team\'s first Mini.')
    if st.get('stopped'):
        return ('say', 'OK. Nothing was set up. Click Make a team to start again.')
    pre = st.get('help')
    lead = (pre + '\n\n') if pre else ''
    if st.get('proposed') and 'name' not in st and not st.get('taken'):
        return ('call', 'team_check', {'name': st['proposed']}, None)
    if st.get('taken'):
        return ('say', lead + st['taken'])
    step = st.get('expect') or _next(st)
    if step == 'name':
        if st.get('no_name') and not st.get('wants_name'):
            first = 'No problem. ' if st.get('trying') else ''
            return ('card', 'Name', first + 'What should we call the team? Insights is fine for a try-out.',
                    [('Insights', 'You can make more teams later.'), ('Something else', 'Then type it in the chat.')], lead or None)
        return ('say', lead + ("Type the team's name." if st.get('wants_name') else ASK_NAME))
    if step == 'goal':
        if st.get('no_goal'):
            first = 'No problem. ' if st.get('trying') else ''
            return ('card', 'Goal', first + 'Use an example goal for now?',
                    [('Use an example', EXAMPLE_GOAL + '.'), ('Leave it blank', 'Add it later.')], lead or None)
        return ('say', lead + ask_goal(st['name']))
    nudge = 'Sorry, I did not catch that. Pick one, or type it another way.\n\n' if st.get('nudge') else ''
    name = st['name']
    if step == 'data':
        return ('card', 'Data', 'Where does the team keep its data?', DATA, (lead + nudge) or None)
    data_note = ''
    if step == 'people' and st.get('data') and st['data'] != 'Google Drive':
        data_note = f'{name} reads files from Google Drive for now. Put a copy there and it works the same.\n\n'
    if step == 'people':
        return ('card', 'People', f'Who will use {name}?', PEOPLE, (lead + nudge + data_note) or None)
    if step == 'private':
        trying = 'Fine. Set it up now and others can join when they are ready.\n\n' if st.get('trying') and \
            st.get('people') else ''
        return ('card', 'Private', 'Do the files have names, places or phone numbers?', PRIVATE,
                (lead + nudge + trying) or None)
    if step == 'outside':
        return ('card', 'Outside service', "When a Mini can't answer a question, may Idli ask an outside service?",
                OUTSIDE, (lead + nudge) or None)
    if step == 'change':
        return ('card', 'Change', 'What would you like to change?', CHANGE, (lead + nudge) or None)
    if st.get('go') and not st.get('failed'):
        if 'team_create' not in has_tools:
            return ('say', 'This computer cannot set up teams yet. Ask whoever set up Idli to update it.')
        return ('call', 'team_create', spec_of(st), f'Setting up {name}...')
    lead2 = lead + nudge + (f'Could not set it up: {st["failed"]}\n\n' if st.get('failed') else '')
    return ('card', 'Set up', f'Set up {name}?', [('Set it up', f'Adds {name} to your sidebar.'), SETUP[1]],
            lead2 + plan_text(st))


# ---------------------------------------------------------------- setup, on the person's computer
def _idli():
    return os.environ.get('IDLI_HOME') or os.path.expanduser('~/idli-insights')


def slug(name):
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return s[:40] or 'team'


def _paseo(*args, parse=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_') or k == 'PASEO_HOME'}
    exe = shutil.which('paseo') or os.path.expanduser('~/.local/bin/paseo')
    r = subprocess.run([exe, *args] + (['--json'] if parse else []), env=env, capture_output=True, text=True,
                       timeout=90, stdin=subprocess.DEVNULL)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-300:] or 'Paseo could not finish')
    return json.loads(r.stdout) if parse and r.stdout.strip() else r.stdout


def _same(a, b):
    return bool(a) and os.path.realpath(os.path.expanduser(a)) == os.path.realpath(os.path.expanduser(b))


def team_dir(path):
    """The resolved folder if path is a team's folder (~/idli-insights/teams/<name>), else None."""
    try:
        real = os.path.realpath(os.path.expanduser(str(path)))
    except (TypeError, ValueError):
        return None
    root = os.path.realpath(os.path.join(_idli(), 'teams'))
    if os.path.dirname(real) != root or not os.path.isfile(os.path.join(real, 'team.json')):
        return None
    return real


def claude_work(folder):
    """A team's Claude folder of masked copies, beside Drivey's (desktop/claude-masked.sh uses the same name)."""
    return os.path.join(_idli(), 'claude-masked-' + os.path.basename(os.path.realpath(folder)))


def start():
    """The Make a team button: say Make a team in Start here's Teams chat."""
    try:
        return _start()
    except Exception:
        return {'ok': False, 'error': 'Could not reach the Teams chat. Try again.'}


def _start():
    setup = os.path.join(_idli(), 'setup')
    chats = _paseo('ls', '--global')
    chats = chats.get('agents', []) if isinstance(chats, dict) else chats or []
    chat = next((c for c in chats if c.get('name') == TEAMS_CHAT and _same(c.get('cwd') or '', setup)), None)
    if not chat:
        return {'ok': False, 'error': 'The Teams chat is missing. Restart Idli to add it again.'}
    _paseo('send', '--no-wait', chat.get('id') or chat['agentId'], MAKE, parse=False)
    return {'ok': True}


def check(name, projects=None):
    """{'ok': True, 'name': clean name} or {'ok': False, 'error': ...} for a team name."""
    clean = _clean_name(name)
    if not clean:
        return {'ok': False, 'error': 'Use up to 30 letters, numbers or spaces for the name.'}
    taken = {clean.lower()} & RESERVED
    if projects is None:
        try:
            projects = _paseo('project', 'ls')
        except Exception:
            projects = []
    names = {str(p.get('name', '')).lower() for p in projects or []}
    folder = os.path.join(_idli(), 'teams', slug(clean))
    if taken or clean.lower() in names or os.path.exists(os.path.join(folder, 'team.json')):
        return {'ok': False, 'error': f'{clean} is already in your sidebar. Pick another name.'}
    return {'ok': True, 'name': clean}


def create(spec, cowork):
    """Make the team: its folder (instructions, tools, team.json) and its sidebar heading. Safe to run again for the
    same team (it finishes what is missing)."""
    name = _clean_name(spec.get('name'))
    if not name:
        return {'ok': False, 'error': 'The name is missing.'}
    folder = os.path.join(_idli(), 'teams', slug(name))
    meta = os.path.join(folder, 'team.json')
    if os.path.exists(meta):
        try:
            if json.load(open(meta)).get('name') != name:
                return {'ok': False, 'taken': True, 'error': 'Another team uses that folder. Pick another name.'}
        except (OSError, ValueError):
            pass
    else:
        c = check(name)
        if not c['ok']:
            return {'ok': False, 'taken': True, 'error': c['error']}
    os.makedirs(folder, exist_ok=True)
    record = {'name': name, 'kind': 'insights', 'goal': str(spec.get('goal') or '')[:200],
              'data': spec.get('data'), 'people': spec.get('people'), 'private': spec.get('private'),
              'outside': bool(spec.get('outside')), 'trying': bool(spec.get('trying')),
              'notes': [str(n)[:200] for n in (spec.get('notes') or [])][:6]}
    with open(meta, 'w') as f:
        json.dump(record, f, indent=2)
    shutil.copyfile(os.path.join(cowork, 'idli', 'CLAUDE.md'), os.path.join(folder, 'CLAUDE.md'))
    with open(os.path.join(folder, 'cowork.tools'), 'w') as f:
        f.write('\n'.join(TEAM_TOOLS) + '\n')
    with open(os.path.join(folder, 'cowork.sites'), 'w') as f:
        f.write(SITES)
    if not record['outside']:
        with open(os.path.join(folder, 'no-query-service'), 'w') as f:
            f.write('Set up without the outside query service.\n')
    proj = next((p for p in _paseo('project', 'ls') if _same(p.get('path'), folder)), None)
    if not proj:
        _paseo('project', 'create', folder, parse=False)
        proj = next((p for p in _paseo('project', 'ls') if _same(p.get('path'), folder)), None)
    if not proj:
        return {'ok': False, 'error': 'The sidebar heading did not appear. Try again.'}
    if proj.get('name') != name:
        _paseo('project', 'rename', proj['projectId'], name, parse=False)
    return {'ok': True, 'name': name, 'folder': folder}


# ---------------------------------------------------------------- the Teams page (lib/teams_page.html)
def _projects():
    try:
        out = _paseo('project', 'ls')
        return out if isinstance(out, list) else []
    except Exception:
        return []


def list_teams(projects=None):
    """The team cards: Drivey first (built in, it can't be deleted), then each team folder, newest first."""
    projects = _projects() if projects is None else projects
    cards = []
    drivey = os.path.join(_idli(), 'cowork-real')
    proj = next((p for p in projects if _same(p.get('path'), drivey)), None)
    if proj:
        cards.append({'id': 'drivey', 'name': proj.get('name') or 'Drivey', 'goal': 'Ask questions about Drive files.',
                      'builtin': True, 'ready': True})
    root = os.path.join(_idli(), 'teams')
    found = []
    for d in os.listdir(root) if os.path.isdir(root) else []:
        folder = team_dir(os.path.join(root, d))
        if not folder:
            continue
        try:
            with open(os.path.join(folder, 'team.json')) as f:
                meta = json.load(f)
        except (OSError, ValueError):
            continue
        found.append((os.path.getmtime(os.path.join(folder, 'team.json')), {
            'id': os.path.basename(folder), 'name': meta.get('name') or d, 'goal': meta.get('goal') or '',
            'people': meta.get('people') or '', 'outside': bool(meta.get('outside')),
            'ready': any(_same(p.get('path'), folder) for p in projects)}))
    cards += [c for _, c in sorted(found, key=lambda x: -x[0])]
    return {'teams': cards}


def _team_folder(team_id):
    if team_id == 'drivey':
        return os.path.join(_idli(), 'cowork-real')
    if not re.fullmatch(r'[a-z0-9-]{1,40}', str(team_id)):
        return None
    return team_dir(os.path.join(_idli(), 'teams', team_id))


def open_team(team_id):
    """Open: the team's latest workspace, or its first one in two halves (Paseo P21 window.__idliOpenTeam)."""
    folder = _team_folder(team_id)
    if not folder:
        return {'ok': False, 'error': 'That team is gone. Reload the page.'}
    proj = next((p for p in _projects() if _same(p.get('path'), folder)), None)
    if not proj:
        return {'ok': False, 'error': 'The team is not in your sidebar. Delete it and make it again.'}
    from lib import uiswitch
    try:
        page = next(t for t in uiswitch._targets() if t.get('type') == 'page'
                    and str(t.get('url', '')).startswith('paseo://app'))
        args = {'serverId': uiswitch.server_id(), 'projectId': proj['projectId'], 'path': folder,
                'title': proj.get('name') or 'Team'}
        got = uiswitch._ws_eval(page['webSocketDebuggerUrl'],
                                "(async () => { if (typeof window.__idliOpenTeam !== 'function') return 'old'; "
                                "try { return await window.__idliOpenTeam(" + json.dumps(args) + "); } "
                                "catch (e) { return 'error: ' + e.message; } })()", timeout=30)
    except Exception:
        got = None
    if isinstance(got, str) and got.startswith('wks_'):
        return {'ok': True}
    if got == 'old':
        return {'ok': False, 'error': 'This Paseo is too old to open teams from here. Click the team in the sidebar.'}
    return {'ok': False, 'error': f'Could not open {proj.get("name") or "the team"}. Click it in the sidebar.'}


def _stop_page_server(folder):
    """A team's own page server (lib/formserver.py ensure) stops with the team."""
    try:
        with open(os.path.join(folder, '.idli', 'form-server.json')) as f:
            pid = int(json.load(f).get('pid'))
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmd = f.read().replace(b'\0', b' ').decode(errors='replace')
        if 'formserver.py' in cmd and folder in cmd:
            os.kill(pid, 15)
    except (OSError, ValueError, TypeError):
        pass


def delete_team(team_id):
    """Delete: the heading (its workspaces and chats) goes from Paseo; the folder and Claude's masked copies move to
    ~/idli-insights/archive/teams, so nothing is lost by a wrong click."""
    if team_id == 'drivey':
        return {'ok': False, 'error': 'Drivey is built in. It stays.'}
    folder = _team_folder(team_id)
    if not folder:
        return {'ok': False, 'error': 'That team is gone. Reload the page.'}
    try:
        chats = _paseo('ls', '--global')
        chats = chats.get('agents', []) if isinstance(chats, dict) else chats or []
        for c in chats:
            if _same(c.get('cwd') or '', folder):
                _paseo('delete', c.get('id') or c['agentId'], parse=False)
        for p in _projects():
            if _same(p.get('path'), folder):
                _paseo('project', 'delete', p['projectId'], parse=False)
    except Exception:
        return {'ok': False, 'error': 'Paseo could not remove the heading. Try again.'}
    _stop_page_server(folder)
    import time
    dest = os.path.join(_idli(), 'archive', 'teams')
    os.makedirs(dest, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    for src in (folder, claude_work(folder)):
        if os.path.exists(src):
            shutil.move(src, os.path.join(dest, f'{os.path.basename(src)}-{stamp}'))
    return {'ok': True}


def name_from(text):
    """The Teams page's name box: "call it Field M&E" or "we are the M&E team" give the name (rules only, no 9B)."""
    t = ' '.join(str(text or '').split())[:80]
    m = re.search(r"(?i)\b(?:call(?:ed)? (?:it|us|this|the team)?|name(?:d)? (?:it|is)?|we'?re(?: called)?|"
                  r"we are(?: called)?|team is)\s+[\"']?([\w][\w &'.-]{0,29}?)[\"']?\s*(?:team)?[.!]?$", t)
    return check(m.group(1) if m else t)


def goal_from(text):
    """The Teams page's goal box, without spoken lead-ins ("ok so we help..." gives "Help...")."""
    t = _unfill(' '.join(str(text or '').split()))
    t = re.sub(r"(?i)^(help|reduc|improv|increas|lower|track|support)(s|es)\b", r"\1", t)
    return t[:140].rstrip(' .')
