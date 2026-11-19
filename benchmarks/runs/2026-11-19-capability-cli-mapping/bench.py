"""Run and score the mapping benchmark (PLAN.md).

  python bench.py run --split dev --mappers remote,nine --conds 1,2,3 [--repeat 1] [--only q01,q02]
  python bench.py score --split dev

Raw answers go to results/<split>-<mapper>-c<cond>[-r<k>].jsonl. Masked questions only; nothing touches an account.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import menus

HERE = Path(__file__).resolve().parent
RES = HERE / 'results'
TODAY = dt.date(2026, 11, 19)
Q = {q['id']: q for q in json.load(open(HERE / 'questions.json'))['questions']}
SPLIT = json.load(open(HERE / 'split.json'))


# ---- calling the mappers ----

def call_remote(system, menu, question, schema):
    from lib import minisql
    body = {'model': minisql.MODEL, 'temperature': 0, 'max_tokens': 400, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': menu + '\n\nQuestion: ' + question}]}
    if 'openrouter.ai' in minisql.URL:
        body['provider'] = {'data_collection': 'deny'}
    req = urllib.request.Request(minisql.URL, json.dumps(body).encode(), {
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + minisql._key(),
        'User-Agent': 'idli-capbench/1'})
    empties = 0
    for _ in range(2):  # production uses max_tokens 400; reasoning can use it all and leave no content
        with urllib.request.urlopen(req, timeout=90) as r:
            text = json.load(r)['choices'][0]['message']['content']
        if text:
            break
        empties += 1
    if not text:
        return {'_error': 'empty content twice', '_empties': empties}
    try:
        out = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip()))
        if empties and isinstance(out, dict):
            out['_empties'] = empties
        return out
    except ValueError:
        return {'_unparsed': text[:500]}


def call_nine(system, menu, question, schema):
    from lib import routines
    return routines.judge(system + '\n\n' + menu + '\n\nQuestion: ' + question[:600], schema, timeout=180,
                          max_tokens=400)


def run(args):
    RES.mkdir(exist_ok=True)
    ids = SPLIT[args.split] if not args.only else args.only.split(',')
    for mapper in args.mappers.split(','):
        fn = call_remote if mapper == 'remote' else call_nine
        for cond in args.conds.split(','):
            for k in range(args.repeat):
                out = RES / f'{args.split}-{mapper}-c{cond}{f"-r{k}" if args.repeat > 1 else ""}.jsonl'

                def one(qid):
                    q = Q[qid]
                    system, menu, schema = menus.prompt(cond, q['mini'])
                    t = time.time()
                    try:
                        ans = fn(system, menu, q['q'], schema)
                    except Exception as e:  # noqa: BLE001 - record and go on
                        ans = {'_error': f'{type(e).__name__}: {e}'[:300]}
                    return {'id': qid, 'answer': ans, 'secs': round(time.time() - t, 2),
                            'prompt_chars': len(system) + len(menu) + len(q['q'])}
                with cf.ThreadPoolExecutor(4 if mapper == 'remote' else 2) as ex:
                    rows = list(ex.map(one, ids))
                out.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                print(f'{out.name}: {len(rows)} done', flush=True)


# ---- normalising answers ----

def _date(v):
    if v is None or v == '':
        return None
    s = str(v).strip()
    m = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
    if m:
        return dt.date(*map(int, m.groups())).isoformat()
    return s


def _gmail(query):
    """Parse a Gmail query into from, since, until and text."""
    out, words = {}, []
    for tok in re.findall(r'\S+:"[^"]*"|\S+:\([^)]*\)|"[^"]*"|\S+', str(query or '')):
        low = tok.lower()
        if low.startswith('from:'):
            out['from'] = tok[5:].strip('"()')
        elif low.startswith(('after:', 'since:')):
            out['since'] = _date(tok.split(':', 1)[1])
        elif low.startswith('before:'):
            out['until'] = _date(tok.split(':', 1)[1])
        elif low.startswith('newer_than:'):
            m = re.match(r'(\d+)([dhmy])', low[11:])
            if m:
                n, u = int(m.group(1)), m.group(2)
                days = n if u == 'd' else (1 if u == 'h' else n * 30 if u == 'm' else n * 365)
                out['since'] = (TODAY - dt.timedelta(days=days)).isoformat()
        elif low.startswith(('subject:', 'in:', 'is:', 'label:', 'category:')):
            words.append(tok.split(':', 1)[1].strip('"()'))
        elif low not in ('or', 'and'):
            words.append(tok.strip('"()'))
    if words:
        out['text'] = ' '.join(words)
    return out


def _key(k):
    return str(k).lstrip('-').replace('-', '_').lower()


# Conditions. A new condition (e.g. a kubectl/gh-style grammar) is: a menu builder in menus.prompt, an entry here
# naming its family, and, if its commands differ, a translation of its answer into the canonical items below (add
# a family branch in items()). Gold stays canonical, so the frozen held-out set is reused as is.
FAMILY = {'1': 'menu', '2': 'cli', '3': 'cli'}


def family(cond):
    return FAMILY[str(cond).rstrip('d')]


def gold_key(cond):
    return 'gold1' if family(cond) == 'menu' else 'gold23'


CMD = {'sheet rows': 'sheet_rows', 'mail search': 'mail_search', 'mail read': 'mail_read',
       'calendar meetings': 'meetings', 'calendar free': 'free_times', 'nine-b judge': 'judge', 'whole': 'whole'}


def items(answer, cond):
    """[(item, args)] in a common form, or [('none', {})]."""
    if not isinstance(answer, dict) or '_error' in answer or '_unparsed' in answer or answer.get('unclear'):
        return [('invalid', {})]
    uses = answer.get('use') if family(cond) == 'menu' else answer.get('run')
    if not uses:
        return [('none', {})] if answer.get('none') or uses == [] else [('invalid', {})]
    out = []
    for u in uses[:2]:
        if not isinstance(u, dict):
            continue
        a = {_key(k): v for k, v in (u.get('args') or {}).items()} if isinstance(u.get('args'), dict) else {}
        if family(cond) == 'menu':
            name = str(u.get('item', ''))
            if name == 'mail_search':
                a = {**_gmail(a.get('query')), **({'from_sheet': a['from_sheet']} if a.get('from_sheet') else {})}
        else:
            raw = str(u.get('cmd', '')).strip().lstrip('-').lower()
            m = re.match(r'step\s*[: ]?\s*(\d+)?', raw)
            if m and raw.startswith('step'):
                n = m.group(1) or a.pop('n', None)
                a.pop('n', None)
                name = f'step:{n}'
            else:
                name = CMD.get(raw, raw)
        for d in ('since', 'until', 'start', 'end'):
            if d in a:
                a[d] = _date(a[d])
        if 'text' in a and isinstance(a['text'], list):
            a['text'] = ' '.join(map(str, a['text']))
        out.append((name, a))
    return out or [('invalid', {})]


def _ok(alt, item, a):
    if alt['item'] != item:
        return False
    for k, want in alt.items():
        if k == 'item':
            continue
        if k == 'text_any':
            text = str(a.get('text', '')).lower()
            if not any(w in text for w in want):
                return False
            continue
        have = a.get(k)
        if have in ('', [], False):
            have = None
        if isinstance(want, list):
            if not any((w is None and have is None) or (w is not None and have is not None and str(w) == str(have))
                       for w in want):
                return False
        elif want is None:
            if have is not None:
                return False
        elif have is None or str(have) != str(want):
            return False
    return True


def grade(qid, answer, cond):
    golds = Q[qid][gold_key(cond)]
    got = items(answer, cond)
    if any(_ok(alt, i, a) for alt in golds for i, a in got):
        return 'exact'
    if any(alt['item'] == i for alt in golds for i, _ in got):
        return 'partial'
    return 'wrong'


def score(args):
    rows = []
    for f in sorted(RES.glob(f'{args.split}-*.jsonl')):
        m = re.match(rf'{args.split}-(\w+)-c(\w+?)(?:-r(\d))?\.jsonl', f.name)
        mapper, condname, rep = m.group(1), m.group(2), m.group(3)
        cond = condname
        res = [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()]
        g = {r['id']: grade(r['id'], r['answer'], cond) for r in res}
        same = [i for i in g if not Q[i]['cli_only']]
        only = [i for i in g if Q[i]['cli_only']]
        nones = [i for i in g if Q[i][gold_key(condname)][0]['item'] == 'none']
        secs = sorted(r['secs'] for r in res)
        rows.append({'file': f.name, 'mapper': mapper, 'cond': condname, 'rep': rep,
                     'exact': sum(v == 'exact' for v in g.values()), 'n': len(g),
                     'same_exact': sum(g[i] == 'exact' for i in same), 'same_n': len(same),
                     'cli_only_exact': sum(g[i] == 'exact' for i in only), 'cli_only_n': len(only),
                     'partial': sum(v == 'partial' for v in g.values()),
                     'none_ok': sum(g[i] == 'exact' for i in nones), 'none_n': len(nones),
                     'median_s': secs[len(secs) // 2] if secs else 0,
                     'prompt_chars': round(sum(r['prompt_chars'] for r in res) / max(1, len(res))),
                     'misses': {i: v for i, v in g.items() if v != 'exact'}})
    for r in rows:
        print(f"{r['file']:28} exact {r['exact']:2}/{r['n']}  same-cap {r['same_exact']}/{r['same_n']}  "
              f"cli-only {r['cli_only_exact']}/{r['cli_only_n']}  partial {r['partial']}  none {r['none_ok']}/"
              f"{r['none_n']}  med {r['median_s']}s  prompt {r['prompt_chars']}  misses {r['misses']}")
    (RES / f'score-{args.split}.json').write_text(json.dumps(rows, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--split', default='dev')
    r.add_argument('--mappers', default='remote,nine')
    r.add_argument('--conds', default='1,2,3')
    r.add_argument('--repeat', type=int, default=1)
    r.add_argument('--only', default='')
    s = sub.add_parser('score')
    s.add_argument('--split', default='dev')
    a = p.parse_args()
    run(a) if a.cmd == 'run' else score(a)
