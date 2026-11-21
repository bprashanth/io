"""Read-only end-to-end check on the laptop (test accounts 87 and 88): run a few mapped answers through production's
miniscope.run_item in the merry-parrot sandbox and print what came back (counts and subjects only). CLI answers
are translated to today's items, plus a guest filter done here for the CLI-only case. Nothing is written.

  cd <cowork> && .venv/bin/python <this file>
"""
import os
import sys

sys.path.insert(0, os.getcwd())
from lib import home, miniscope  # noqa: E402

DD = os.path.expanduser('~/idli-insights/teams/merry-parrot-7ac1')
mini = {**home.read(os.path.join(DD, 'minis/lead-replies-in-steps-9366ed32/mini.json')),
        'id': 'lead-replies-in-steps-9366ed32'}
CASES = [  # (question, what the best condition chose, as today's item)
    ('q01 this morning\'s lead replies', {'item': 'mail_search', 'args': {'query': 'after:2026/11/19', 'from_sheet': 'SHEET_1'}}),
    ('q01 as the 9B chose it in condition 1 (from:SHEET_1 in the query)',
     {'item': 'mail_search', 'args': {'query': 'from:SHEET_1 newer_than:1d', 'from_sheet': 'SHEET_1'}}),
    ('q02 all emails from today', {'item': 'mail_search', 'args': {'query': 'after:2026/11/19'}}),
    ('q09 did any lead write since Monday', {'item': 'mail_search', 'args': {'query': 'after:2026/11/16', 'from_sheet': 'SHEET_1'}}),
    ('q04 meetings yesterday', {'item': 'meetings', 'args': {'start': '2026-11-18', 'end': '2026-11-18'}}),
    ('q31 meetings with EMAIL_001 this month (CLI --guest, filtered here)',
     {'item': 'meetings', 'args': {'start': '2026-11-01', 'end': '2026-11-30'}, 'guest': '88profligate@gmail.com'}),
]
os.environ['IDLI_PREVIEW'] = '1'
for name, use in CASES:
    head, body = miniscope.run_item(DD, mini, {'item': use['item'], 'args': use['args'], 'role': 'me'})
    lines = [ln for ln in body.splitlines() if ln.strip().startswith('- ')]
    if use.get('guest'):
        lines = [ln for ln in lines if use['guest'] in ln or '88' in ln]
    print(f'== {name}: {head}: {len(lines)} items')
    for ln in lines[:5]:
        print('   ', ln[:110])
