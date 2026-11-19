"""Two gates for Sandbox Claude's script_try, both in Idli's left chat (owner, 2026-11-19).

Gate 1: "Claude wants Idli to read more from your accounts: <title>." Yes runs the script here.
Gate 2: the real output on the left, then "Claude would get this, with private values as codes:" and a short masked
sample. Yes sends the masked output to Claude; No sends nothing.

Claude's MCP call (lib/idli_mcp.script_try) and the left chat (binder_item kind "Try", lib/modes.py) meet through one
small file per try in <sandbox>/.idli/tries/<id>.json. Its state moves: ask1 -> run | no1 -> ask2 | failed -> send |
keep. Nothing reaches Claude before "send".
"""
import json
import os
import time
from pathlib import Path

GATE_WAIT = 600     # seconds a gate waits for the person
RUN_WAIT = 330      # seconds the left chat waits for the script to finish
REFUSED_RUN = 'The person chose not to run this. Try another way, or ask them what they want.'
REFUSED_SEND = 'The person ran it and saw the output, but chose not to share it with you. Try another way, or ask them.'
NO_ANSWER = 'No answer from the person. Ask them in one short line to answer the card on the left.'


def folder(data_dir):
    p = Path(data_dir) / '.idli' / 'tries'
    p.mkdir(parents=True, exist_ok=True)
    return p


def path(data_dir, ident):
    ident = str(ident)
    if not ident.isdigit():
        raise ValueError('That request is no longer here.')
    return folder(data_dir) / f'{ident}.json'


def read(data_dir, ident):
    try:
        return json.loads(path(data_dir, ident).read_text())
    except (OSError, ValueError):
        raise ValueError('That request is no longer here. Ask Claude to try again.')


def write(data_dir, ident, rec):
    p = path(data_dir, ident)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(rec))
    os.replace(tmp, p)


def update(data_dir, ident, **changes):
    rec = read(data_dir, ident)
    rec.update(changes)
    write(data_dir, ident, rec)
    return rec


def wait(data_dir, ident, states, timeout, step=0.4):
    """Wait until the try's state is one of states; None on timeout."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            rec = read(data_dir, ident)
        except ValueError:
            return None
        if rec.get('state') in states:
            return rec
        time.sleep(step)
    return None


def gate1_text(rec):
    title = rec.get('title') or 'a script'
    if rec.get('preview', True):
        return (f'Claude wants Idli to read more from your accounts: **{title}**. Nothing is written. '
                "You'll see what it finds here.")
    return (f'Claude wants Idli to run this on your accounts for real: **{title}**. It may draft, book or send. '
            "You'll see what it did here.")


def sample(masked_output, lines=12, width=160):
    rows = [r[:width] for r in str(masked_output or '').strip().splitlines() if r.strip()]
    more = len(rows) - lines
    return '\n'.join(rows[:lines]) + (f'\n... and {more} more lines' if more > 0 else '') or '(no output)'


# ---- the left chat's side (binder_item kind "Try") ----

def left(data_dir, ident, answer=None):
    """What the left chat shows for this try, after the person's answer (if any)."""
    from lib import home
    rec = read(data_dir, ident)
    if not answer:
        if rec.get('state') != 'ask1':
            return {'reply': 'That request was already answered.'}
        return {'gate': 1, 'id': str(ident), 'text': gate1_text(rec)}
    if answer == 'no':
        update(data_dir, ident, state='no1')
        return {'reply': 'OK. Nothing was run. Claude is told no and will try another way.'}
    if answer == 'run':
        if rec.get('state') == 'ask1':
            update(data_dir, ident, state='run')
        done = wait(data_dir, ident, ('ask2', 'failed'), RUN_WAIT)
        if not done:
            return {'reply': 'It is taking too long. Claude is told it did not finish.'}
        shown = home.binder_item(data_dir, 'Run', done.get('title', ''), done.get('workspace'))['reply']
        if done['state'] == 'failed':
            return {'reply': shown}
        return {'gate': 2, 'id': str(ident), 'shown': shown, 'sample': done.get('sample', '')}
    if answer in ('send', 'keep'):
        if rec.get('state') == 'ask2':
            update(data_dir, ident, state=answer)
        return {'reply': 'Sent to Claude, with private values as codes.' if answer == 'send' else
                'Not sent. Claude is told no and will try another way.'}
    raise ValueError('Unknown answer')
