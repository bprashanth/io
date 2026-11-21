"""The three menus the mapper sees, per Mini. Condition 1 is production (lib/miniscope.menu_text and MAP_SYSTEM, run
with the Mini's real steps, the sandbox's blocks and a fixed date). Conditions 2 and 3 are hand-written CLI schemas;
3 adds a short man page with examples. Nothing here touches an account."""
import json
import re
import sys
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COWORK = HERE.parent / '2026-11-06-oss-desktop-independent' / 'cowork'
sys.path.insert(0, str(COWORK))
from lib import miniscope  # noqa: E402

TODAY_LINE = 'Today is Thursday 2026-11-19, time zone UTC+05:30.'
SANDBOX_BLOCKS = ['sheet_read', 'gmail_draft', 'gmail_search', 'gmail_read', 'nine_b', 'calendar_freebusy',
                  'calendar_book']
MINIS = {  # the three Minis in merry-parrot-7ac1 (copied from the laptop 2026-11-19; goals have no private values)
    'steps': {'name': 'Lead replies in steps', 'sheets': ['S1'],
              'steps': ['Read the leads sheet', 'Find their replies', 'Read each reply',
                        'Draft open times for leads who agreed', 'Book the time for leads who picked one', 'Totals'],
              'goal': "Every morning: read the leads sheet, find each lead's replies from the last two weeks (calendar "
                      "notices such as accepted, declined or invitations are skipped), let the private model read each "
                      "reply, draft three open 30-minute times for leads who agreed, and book the time for leads who "
                      "picked one. Runs in six named steps, so you can run and check any one step on its own. Safe to "
                      "run again: replies already answered and times already on the calendar are skipped."},
    'plain': {'name': 'Lead replies', 'sheets': ['S1'], 'steps': [],
              'goal': 'Every morning: for each lead on the leads sheet who replied in the last two weeks, the private '
                      'model reads the reply. If they agreed to meet, a reply with three open 30-minute times is '
                      'drafted in Gmail (you press Send). If they picked a time, it is booked on your calendar with '
                      'them invited. Replies already answered and times already on the calendar are skipped, so it is '
                      'safe to run again.'},
    'meetings': {'name': 'My meetings this week', 'sheets': [],
                 'steps': ['Work out this week', 'Read my meetings', 'List them by day'],
                 'goal': 'Lists the meetings on my calendar from Monday to Sunday of the current week, grouped by day, '
                         'with the time, title and guests of each one. It only reads the calendar and changes nothing.'},
    'fixity': {'name': 'Fixity checks 2021 and 2025', 'sheets': [], 'steps': [], 'drive': True,
               'goal': 'Charts how often organisations check the fixity of stored files, from the 2021 and 2025 survey '
                       'data: answers per year, side by side. It reads the two data files in the study folder.'},
}
DRIVE_FILES = ('Folder: FOLDER_1 (the study folder). Files in it: FILE_1 (the 2021 report, a PDF), FILE_2 (the 2021 '
               'data, a spreadsheet), FILE_3 (the 2025 data, a spreadsheet), FILE_4 (the 2025 report, a PDF).')


def cond1(key):
    m = MINIS[key]
    mini = {'steps': m['steps'], 'name': m['name']}
    with mock.patch.object(miniscope, 'sheets', lambda d, mi: m['sheets']), \
            mock.patch('lib.blocks.enabled', lambda d=None: SANDBOX_BLOCKS), \
            mock.patch('lib.blocks.accounts', lambda d=None: {'me': 'x', 'lead': 'y'}):
        text = miniscope.menu_text('/nonexistent', mini, m['goal'])
    return re.sub(r'Today is .*', TODAY_LINE, text)


# ---- conditions 2 and 3: commands ----

CHAINS = {  # each step as a command with the arguments a question may change
    'steps': [
        ('Read the leads sheet', 'sheet rows --sheet SHEET_1', ''),
        ('Find their replies', 'mail search --from-sheet SHEET_1 --since <14 days ago> --skip-notices',
         'may change: --since, --until, --text'),
        ('Read each reply', 'nine-b judge --over 2 --question "did they agree to meet, and did they pick a time?" '
         '--answers picked,agreed,other', ''),
        ('Draft open times for leads who agreed', 'mail draft (preview) for each "agreed" from step 3', ''),
        ('Book the time for leads who picked one', 'calendar book (preview) for each "picked" from step 3', ''),
        ('Totals', 'counts per answer from step 3', ''),
    ],
    'plain': [],
    'fixity': [],
    'meetings': [
        ('Work out this week', 'Monday to Sunday of this week', ''),
        ('Read my meetings', 'calendar meetings --start <Monday> --end <Sunday>', 'may change: --start, --end'),
        ('List them by day', 'groups step 2 by day', ''),
    ],
}

COMMANDS = [  # (name, synopsis, arguments, man page: description and examples)
    ('sheet rows', 'sheet rows --sheet SHEET',
     '--sheet: a sheet code below',
     'The rows of a sheet the Mini reads, as a table.\n'
     '  "what columns does the sheet have?" -> {"cmd": "sheet rows", "args": {"sheet": "SHEET_1"}}'),
    ('mail search', 'mail search [--from-sheet SHEET] [--from EMAIL] [--since DATE] [--until DATE] [--text WORDS] '
                    '[--skip-notices] [--limit N]',
     '--from-sheet: only mail from the people listed on that sheet; --from: only mail from this address code; '
     '--since/--until: YYYY-MM-DD, both days included; --text: words that must appear (any of them); '
     '--skip-notices: leave out calendar notices (accepted, declined, invitations); --limit: at most 20 (default 10)',
     'Emails, newest first: date, sender, subject and first words. Use --from-sheet when the question is about the '
     "Mini's own people (leads); leave it out for broad questions about all mail.\n"
     '  "new mail from leads since the 10th" -> {"cmd": "mail search", "args": {"from_sheet": "SHEET_1", '
     '"since": "2026-11-10", "skip_notices": true}}\n'
     '  "all emails from last weekend" -> {"cmd": "mail search", "args": {"since": "2026-11-14", "until": "2026-11-15"}}\n'
     '  "mail from EMAIL_002 about the invoice" -> {"cmd": "mail search", "args": {"from": "EMAIL_002", "text": '
     '"invoice"}}'),
    ('mail read', 'mail read (--from EMAIL | --id ID) [--latest]',
     '--from: the sender\'s address code; --id: a message id from mail search; --latest: only the newest one',
     'One email in full (the whole body, not the first words).\n'
     '  "show me EMAIL_003\'s last email in full" -> {"cmd": "mail read", "args": {"from": "EMAIL_003", '
     '"latest": true}}'),
    ('calendar meetings', 'calendar meetings --start DATE --end DATE [--guest EMAIL] [--with-sheet SHEET]',
     '--start/--end: YYYY-MM-DD, the last day included; --guest: only meetings with this address code; '
     '--with-sheet: only meetings with someone listed on that sheet',
     'The meetings on the calendar (title, time, guests, declined or not). Busy times are the same as meetings.\n'
     '  "my meetings next Tuesday" -> {"cmd": "calendar meetings", "args": {"start": "2026-11-24", "end": "2026-11-24"}}\n'
     '  "meetings with leads in December" -> {"cmd": "calendar meetings", "args": {"start": "2026-12-01", '
     '"end": "2026-12-31", "with_sheet": "SHEET_1"}}'),
    ('calendar free', 'calendar free [--days N] [--minutes N] [--count N]',
     '--days: working days ahead (default 5); --minutes: slot length (default 30); --count: how many (default 3)',
     'Open times in working hours on the next working days.\n'
     '  "two free 45 minute slots this week" -> {"cmd": "calendar free", "args": {"days": 2, "minutes": 45, '
     '"count": 2}}'),
    ('nine-b judge', 'nine-b judge --over STEP --question TEXT --answers A,B,C',
     '--over: the step number whose items are judged (each email or row); --question: what to decide about each; '
     '--answers: the allowed answers',
     "The private model reads each item of a step's output on this computer and gives one answer per item. Use it "
     'for a judgement about content the Mini already reads that no step makes.\n'
     '  "which replies ask about the venue?" -> {"cmd": "nine-b judge", "args": {"over": 2, "question": "does this '
     'reply ask where the meeting is?", "answers": "yes,no"}}'),
]
DRIVE_COMMANDS = [
    ('drive list', 'drive list [--in FOLDER] [--type pdf|sheet|doc] [--since DATE] [--until DATE] [--text WORDS] [--shared]',
     '--in: only files in this folder code; --type: only this kind; --since/--until: changed on these days, '
     'YYYY-MM-DD, both included; --text: words in the name (any of them); --shared: only files others shared with you',
     'Files in Drive, newest change first: name, kind, folder, last change.\n'
     '  "the documents in FOLDER_2" -> {"cmd": "drive list", "args": {"in": "FOLDER_2", "type": "doc"}}\n'
     '  "anything new in Drive since the 10th" -> {"cmd": "drive list", "args": {"since": "2026-11-10"}}'),
    ('file read', 'file read --file FILE',
     '--file: a file code',
     "One file's content: a PDF's text page by page, or a spreadsheet's columns and first rows.\n"
     '  "what is in FILE_7?" -> {"cmd": "file read", "args": {"file": "FILE_7"}}'),
]
ALWAYS = [('step', 'step --n N [overrides]', '--n: the step number; overrides: the arguments that step says may change',
           'Runs steps 1 to N in preview and shows step N.\n'
           '  "what would step 2 give for the last 5 days?" -> {"cmd": "step", "args": {"n": 2, "since": '
           '"2026-11-14"}}'),
          ('whole', 'whole', '(none)',
           'The whole Mini in preview: what it finds and what it would draft or book.\n'
           '  "what would you draft right now?" -> {"cmd": "whole", "args": {}}')]

CLI_SYSTEM = """You map a person's question about a saved workflow (a "Mini") to the one or two commands that
answer it. You never see their data. Private values are codes like EMAIL_002 or NAME_004: copy them exactly.

Answer with JSON only, one of:
{"run": [{"cmd": "<a command name>", "args": {<argument: value>}, "role": "<an account role>"}],
 "title": "<the question, made specific, as a short heading>"}
{"none": "<one plain sentence: what the Mini and the commands cannot do>"}

Rules:
- Use only the commands listed. One command, two at most. Argument names use underscores (from_sheet, not
  --from-sheet). Dates are YYYY-MM-DD.
- Prefer a step of the Mini when it is what the question asks about ("who replied", "what would step 2 give"),
  with overrides when the question narrows it.
- Use another command for a plain look at the accounts the Mini works on ("my meetings yesterday", "list my
  leads").
- "whole" only for what the Mini would do overall (what it would draft or book).
- When the question is about the Mini's own people, limit to the sheet (from_sheet or with_sheet). Leave it out
  only when the question is broad ("all my emails today").
- If no command answers it (it needs a change to the Mini, a write, sending, posting, another account), answer
  none."""
CLI_SCHEMA = {'type': 'object', 'properties': {
    'run': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'cmd': {'type': 'string'}, 'args': {'type': 'object'}, 'role': {'type': 'string'}}, 'required': ['cmd']}},
    'title': {'type': 'string'}, 'none': {'type': 'string'}}}


def cli(key, man):
    m = MINIS[key]
    lines = [f'The Mini: {m["goal"]}', '']
    chain = CHAINS[key]
    if chain:
        lines.append('The Mini is this chain of commands:')
        for n, (title, cmd, may) in enumerate(chain, 1):
            lines.append(f'  step {n}: {title}: {cmd}' + (f' ({may})' if may else ''))
        lines.append('')
    lines.append('Commands:')
    if m.get('drive'):
        cmds = DRIVE_COMMANDS
    else:
        cmds = ALWAYS if chain else ALWAYS[1:]
        cmds = cmds + [c for c in COMMANDS if c[0] != 'sheet rows' or m['sheets']]
    for name, synopsis, args, page in cmds:
        lines.append(f'- {synopsis}')
        lines.append(f'    arguments: {args}')
        if man:
            lines += ['    ' + ln for ln in page.split('\n')]
    if m['sheets']:
        lines += ['', 'Sheet codes: SHEET_1 (sheet 1 the Mini reads)']
    if m.get('drive'):
        lines += ['', DRIVE_FILES]
    lines += ['', 'Account roles (give one as "role"): me, lead. Default: me.', '', TODAY_LINE]
    return '\n'.join(lines)


# ---- condition 4: one grammar, kubectl/gh style (narrative/CLI_CHOICES.md) ----
# idli VERB RESOURCE [NAME] [flags]. Read verbs only in this menu; write verbs exist but are never offered here.

G_STEPS = {  # each step as the command it runs
    'steps': [('Read the leads sheet', 'idli list leads', ''),
              ('Find their replies', 'idli list replies --since 2026-11-05', 'may change: --since, --until, --search'),
              ('Read each reply', 'idli judge replies --question "did they agree to meet, and did they pick a time?" '
               '--answers picked,agreed,other', ''),
              ('Draft open times for leads who agreed', 'idli draft mail ... for each "agreed" (a write: preview only)', ''),
              ('Book the time for leads who picked one', 'idli book event ... for each "picked" (a write: preview only)', ''),
              ('Totals', 'counts per answer from step 3', '')],
    'plain': [],
    'fixity': [],
    'meetings': [('Work out this week', 'Monday to Sunday of this week', ''),
                 ('Read my meetings', 'idli list events --since 2026-11-16 --until 2026-11-22',
                  'may change: --since, --until, --where'),
                 ('List them by day', 'groups step 2 by day', '')],
}
G_VIEWS = {  # resources a Mini defines on top of the account resources
    'steps': [('leads', 'the people on the leads sheet SHEET_1 (name, email)'),
              ('replies', 'mail from leads, newest first, calendar notices (accepted, declined, invitations) left out')],
    'plain': [('leads', 'the people on the leads sheet SHEET_1 (name, email)'),
              ('replies', 'mail from leads, newest first, calendar notices (accepted, declined, invitations) left out')],
    'meetings': [], 'fixity': [],
}
G_RESOURCES = {  # account resources, with what get shows and their own flags
    'mail': ('emails: date, sender, subject, first words', 'get mail: one email in full; use --where from=X --latest '
             'or its id'),
    'events': ('meetings on the calendar: title, time, guests, declined or not (busy times are events)', ''),
    'freetimes': ('open slots in working hours on the next working days',
                  'own flags: --days N (default 5) --minutes N (default 30) --count N (default 3)'),
    'rows': ('the rows of a sheet: list rows SHEET', ''),
    'files': ('Drive files: name, kind (type=pdf, sheet or doc), folder (in=FOLDER), last change; shared=true for '
              'files others shared with you', 'get file FILE: its content (a PDF\'s text, or a '
              'spreadsheet\'s columns and first rows)'),
}
G_EXAMPLES = {  # the same examples as condition 3, in this grammar (none copies a benchmark question)
    'leads': [('new mail from leads since the 10th', 'idli list replies --since 2026-11-10'),
              ('all emails from last weekend', 'idli list mail --since 2026-11-14 --until 2026-11-15'),
              ('mail from EMAIL_002 about the invoice', 'idli list mail --where from=EMAIL_002 --search invoice'),
              ("show me EMAIL_003's last email in full", 'idli get mail --where from=EMAIL_003 --latest'),
              ('my meetings next Tuesday', 'idli list events --since 2026-11-24 --until 2026-11-24'),
              ('meetings with leads in December', 'idli list events --since 2026-12-01 --until 2026-12-31 '
               '--where guest=leads'),
              ('two free 45 minute slots this week', 'idli list freetimes --days 2 --minutes 45 --count 2'),
              ('which replies ask about the venue?', 'idli judge replies --question "does this reply ask where the '
               'meeting is?" --answers yes,no'),
              ('what would step 2 give for the last 5 days?', 'idli run step 2 --since 2026-11-14'),
              ('what would you draft right now?', 'idli run mini')],
    'drive': [('the documents in FOLDER_2', 'idli list files --where in=FOLDER_2 --where type=doc'),
              ('anything new in Drive since the 10th', 'idli list files --since 2026-11-10'),
              ('what is in FILE_7?', 'idli get file FILE_7')],
}
G_EXAMPLES_4B = [('how big is FILE_8?', 'idli describe file FILE_8'),
                 ('give me the gist of FILE_9', 'idli summarise file FILE_9')]
G_SYSTEM = """You turn a person's question about a saved workflow (a "Mini") into the one or two idli commands that
answer it. You never see their data. Private values are codes like EMAIL_002 or NAME_004: copy them exactly.

Answer with JSON only, one of:
{"run": ["idli <verb> <resource> [name] [flags]"], "title": "<the question, made specific, as a short heading>"}
{"none": "<one plain sentence: what the Mini and the commands cannot do>"}

Rules:
- Use only the verbs, resources and flags listed. One command, two at most. Dates are YYYY-MM-DD.
- Prefer the Mini's own resources (leads, replies) and steps when the question is about the Mini's people or work;
  use mail, events or files for a broad look ("all my emails today").
- "run mini" only for what the Mini would do overall (what it would draft or book).
- No write verbs here. If the question needs a change to the Mini, a write, sending, posting, deleting or another
  account, answer none."""


def grammar(key, extended=False):
    m = MINIS[key]
    drive = bool(m.get('drive'))
    lines = [f'The Mini: {m["goal"]}', '', 'Usage: idli VERB RESOURCE [NAME] [flags]', '',
             'Verbs (read only here):',
             '  list RESOURCE      many items, short',
             '  get RESOURCE NAME  one item in full',
             '  judge RESOURCE --question Q --answers A,B,C   the private model reads each item and answers any question you '
             'set (tone, topic, a yes or no), not only the Mini\'s own']
    if extended and drive:
        lines += ['  describe RESOURCE NAME   its shape: a PDF\'s pages, a spreadsheet\'s columns and rows, a folder\'s '
                  'files by kind',
                  '  summarise file NAME [--question Q]   the private model reads it on this computer and sums it up']
    if not drive:
        lines += ['  run step N [flags]  steps 1 to N in preview, shows step N (the step\'s "may change" flags apply)']
        if G_STEPS[key] or key == 'plain':
            lines += ['  run mini           the whole Mini in preview: what it finds, each draft in full and what it '
                      'would book; nothing is sent']
    lines += ['', 'Shared flags (the same meaning on every resource):',
              '  --since DATE --until DATE   both days included',
              '  --search WORDS              any of the words appear',
              '  --where KEY=VALUE           a field equals a value, e.g. from=, guest=, in=, type=, shared=true'
              + ('' if drive or not G_VIEWS[key] else ' the value "leads" means anyone on the leads list'),
              '  --latest                    only the newest one',
              '  --limit N', '  --as ROLE                   an account role (me by default)', '']
    if G_STEPS[key]:
        lines.append('Its steps:')
        for n, (title, cmd, may) in enumerate(G_STEPS[key], 1):
            lines.append(f'  step {n}: {title}: {cmd}' + (f' ({may})' if may else ''))
        lines.append('')
    views = G_VIEWS[key]
    if views:
        lines.append('Resources this Mini defines:')
        lines += [f'  {n:10} {d}' for n, d in views]
    lines.append('Account resources:')
    names = ['files'] if drive else ['mail', 'events', 'freetimes'] + (['rows'] if m['sheets'] else [])
    for n in names:
        d, extra = G_RESOURCES[n]
        lines.append(f'  {n:10} {d}' + (f'. {extra}' if extra else ''))
    lines += ['', 'Examples (today is Thursday 2026-11-19):']
    examples = G_EXAMPLES['drive' if drive else 'leads'] + (G_EXAMPLES_4B if extended and drive else [])
    for q, c in examples:
        if not drive and (('run' in c and not G_STEPS[key] and key != 'plain') or
                          ('run step' in c and not G_STEPS[key]) or (('replies' in c or 'leads' in c) and not views)):
            continue
        lines.append(f'  "{q}" -> {c}')
    if m['sheets']:
        lines += ['', 'Sheet codes: SHEET_1 (the leads sheet)']
    if drive:
        lines += ['', DRIVE_FILES]
    lines += ['', 'Account roles: me, lead. Default: me.', '', TODAY_LINE]
    return '\n'.join(lines)


G_SCHEMA = {'type': 'object', 'properties': {'run': {'type': 'array', 'items': {'type': 'string'}},
                                             'title': {'type': 'string'}, 'none': {'type': 'string'}}}


DATES_LINE = ('This week: Monday 2026-11-16 to Sunday 2026-11-22. Yesterday: Wednesday 2026-11-18. Tomorrow: Friday '
              '2026-11-20. Next week: Monday 2026-11-23 to Sunday 2026-11-29.')
EXAMPLES_NOTE = 'Examples use real dates for today, Thursday 2026-11-19.'


def prompt(cond, key):
    """(system, menu text, schema) for a condition ('1', '2', '3', or with 'd': a line of worked-out dates) and a
    Mini. The 'd' line is what code could compute at run time; it is tested on its own."""
    cond = str(cond)
    base = cond.rstrip('d')
    if base == '1':
        system, text, schema = miniscope.MAP_SYSTEM, cond1(key), miniscope.MAP_SCHEMA
    elif base in ('4', '4b'):
        system, text, schema = G_SYSTEM, grammar(key, extended=base == '4b'), G_SCHEMA
    else:
        system, text, schema = CLI_SYSTEM, cli(key, man=base == '3'), CLI_SCHEMA
        if base == '3':
            text = text.replace(TODAY_LINE, TODAY_LINE + ' ' + EXAMPLES_NOTE)
    if cond.endswith('d'):
        text = text.replace(TODAY_LINE, TODAY_LINE + '\n' + DATES_LINE)
    return system, text, schema


if __name__ == '__main__':
    for c in ('1', '2', '3', '4', '4b'):
        s, t, _ = prompt(c, sys.argv[1] if len(sys.argv) > 1 else 'steps')
        print(f'===== condition {c}: {len(s) + len(t)} chars\n{t}\n')
