"""Judge the synthetic set with each candidate model and score it against labels.json.

    python run.py MODEL [--cond content|today]      writes results/MODEL-COND.jsonl
    python run.py --score                           prints the table from every results file

MODEL: nine_q5 (idli-9b, port 8291), nine_bf16 (idli-9b-bf16, port 8292), muse (port 8181),
       remote (idli-remote via OpenRouter), clef (Clef-flash via OpenRouter, provider Cloudflare only).
COND:  content = every file's text (the first 1200 characters), the design target;
       today   = what recstore.judge sends now: text only for PDFs and documents, name and folder for the rest.
The chat models get the same system and user prompt, answers and JSON schema as recstore.judge.
"""
import argparse
import csv
import io
import json
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
COWORK = HERE.parent / '2026-11-06-oss-desktop-independent' / 'cowork'
sys.path.insert(0, str(COWORK))

ASK = 'Is this about endangered species?'
ANSWERS = ['yes', 'no', 'unsure']
KIND = {'.pdf': 'pdf', '.docx': 'doc', '.csv': 'other', '.xlsx': 'sheet', '.txt': 'other', '.py': 'other'}
CHAT = {'nine_q5': ('http://127.0.0.1:8291', 'qwen3.5-9b'), 'nine_bf16': ('http://127.0.0.1:8292', 'qwen3.5-9b-bf16'),
        'muse': ('http://127.0.0.1:8181', 'muse-glimmer-30b')}
CLEF_UNSURE = (0.35, 0.65)  # Clef gives a probability; inside this band counts as unsure


def file_text(p):
    if p.suffix == '.pdf':
        from pypdf import PdfReader
        return '\n'.join(pg.extract_text() or '' for pg in PdfReader(p).pages)
    if p.suffix == '.docx':
        import docx
        return '\n'.join(x.text for x in docx.Document(p).paragraphs)
    if p.suffix == '.xlsx':
        import openpyxl
        ws = openpyxl.load_workbook(p, read_only=True).active
        return '\n'.join(', '.join('' if v is None else str(v) for v in row) for row in ws.iter_rows(values_only=True))
    return p.read_text()


def item_text(rel, cond):
    """The same shape as recstore._item_text for a file."""
    p = HERE / 'data' / rel
    out = f'File name: {p.name}\nKind: {KIND[p.suffix]}\nFolder: My Drive/{p.parent.relative_to(HERE / "data")}'
    if cond == 'content' or KIND[p.suffix] in ('pdf', 'doc'):
        out += '\n\nStart of the text:\n' + re.sub(r'[ \t]+', ' ', file_text(p))[:1200]
    return out


def messages(text):
    return [{'role': 'system', 'content': 'You label one item for the person. Answer with JSON only. '
             'If the item does not give enough to tell, answer unsure.'},
            {'role': 'user', 'content': f'{ASK}\nAnswers: {", ".join(ANSWERS)}\n\n---\n{text}\n---'}]


SCHEMA = {'type': 'object', 'properties': {'label': {'type': 'string', 'enum': ANSWERS}, 'why': {'type': 'string'}},
          'required': ['label', 'why']}


def post(url, body, headers=None, timeout=180):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def judge_chat(model, text):
    base, name = CHAT[model]
    body = {'model': name, 'temperature': 0, 'stream': False, 'max_tokens': 300,
            'messages': messages(text), 'chat_template_kwargs': {'enable_thinking': False},
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'schema': SCHEMA}}}
    if model == 'muse':  # Muse reasons whatever the template says; a schema grammar plus reasoning stalls it.
        # As lib/driveindex.py calls it: a JSON object, room to think, the shape in the prompt.
        body['messages'] = messages(text)
        body['messages'][0]['content'] += ' Reply as {"label": one of the answers, "why": a short reason}.'
        body.update(max_tokens=4000, response_format={'type': 'json_object'})
    r = post(base + '/v1/chat/completions', body)
    txt = r['choices'][0]['message']['content']
    m = re.search(r'\{.*\}', txt, re.S)
    out = json.loads(m.group(0) if m else txt)
    return out.get('label'), out.get('why', ''), None, r.get('usage', {})


def _or_key():
    from lib import minisql
    return minisql._key()


def judge_remote(text):
    from lib import minisql
    msgs = messages(text)
    msgs[0]['content'] += ' Reply as {"label": one of the answers, "why": a short reason}.'
    body = {'model': minisql.MODEL, 'temperature': 0, 'max_tokens': 600, 'response_format': {'type': 'json_object'},
            'reasoning': {'effort': 'low'}, 'provider': {'data_collection': 'deny'}, 'messages': msgs}
    r = post(minisql.URL, body, {'Authorization': 'Bearer ' + _or_key(), 'User-Agent': 'idli-judge-test/1'})
    txt = r['choices'][0]['message']['content'] or ''
    m = re.search(r'\{.*\}', txt, re.S)
    out = json.loads(m.group(0) if m else txt)
    return out.get('label'), out.get('why', ''), None, r.get('usage', {})


def judge_clef(text):
    body = {'model': 'cloudflare/clef-flash', 'state': text,
            'questions': {'about': {'type': 'noul', 'instructions': ASK}},
            'provider': {'order': ['Cloudflare'], 'allow_fallbacks': False}}
    r = post('https://openrouter.ai/api/v1/systemone', body,
             {'Authorization': 'Bearer ' + _or_key(), 'User-Agent': 'idli-judge-test/1'})
    if r.get('provider') != 'Cloudflare':
        raise RuntimeError(f'served by {r.get("provider")}, not Cloudflare')
    p = r['answers']['about']['noul']
    lab = 'unsure' if CLEF_UNSURE[0] < p < CLEF_UNSURE[1] else ('yes' if p >= 0.5 else 'no')
    return lab, '', p, r.get('usage', {})


def run(model, cond):
    labels = json.loads((HERE / 'labels.json').read_text())
    out = HERE / 'results' / f'{model}-{cond}.jsonl'
    out.parent.mkdir(exist_ok=True)
    with open(out, 'w') as f:
        for it in labels:
            text = item_text(it['path'], cond)
            t0 = time.time()
            for attempt in range(3):
                try:
                    if model in CHAT:
                        lab, why, prob, usage = judge_chat(model, text)
                    elif model == 'remote':
                        lab, why, prob, usage = judge_remote(text)
                    else:
                        lab, why, prob, usage = judge_clef(text)
                    err = None
                    break
                except Exception as e:
                    lab, why, prob, usage, err = None, '', None, {}, f'{type(e).__name__}: {str(e)[:200]}'
                    time.sleep(3)
            rec = {'path': it['path'], 'expected': it['expected'], 'hard': it['hard'], 'label': lab, 'prob_yes': prob,
                   'why': why[:200], 'seconds': round(time.time() - t0, 2), 'cost': usage.get('cost'), 'error': err}
            f.write(json.dumps(rec) + '\n')
            print(f'{model}/{cond} {it["path"]}: {lab} (expected {it["expected"]}) {rec["seconds"]} s', flush=True)


def score():
    rows = []
    for p in sorted((HERE / 'results').glob('*.jsonl')):
        rs = [json.loads(l) for l in p.read_text().splitlines()]
        right = sum(r['label'] == r['expected'] for r in rs)
        miss = sum(r['expected'] == 'yes' and r['label'] == 'no' for r in rs)
        alarm = sum(r['expected'] == 'no' and r['label'] == 'yes' for r in rs)
        unsure = sum(r['label'] == 'unsure' for r in rs)
        failed = sum(r['label'] is None for r in rs)
        hard = [r for r in rs if r['hard']]
        hard_right = sum(r['label'] == r['expected'] for r in hard)
        secs = statistics.median(r['seconds'] for r in rs)
        cost = sum(r['cost'] or 0 for r in rs)
        rows.append((p.stem, f'{right}/{len(rs)}', f'{hard_right}/{len(hard)}', miss, alarm, unsure, failed,
                     f'{secs:.2f}', f'{cost:.5f}' if cost else '-'))
    head = ('model-condition', 'right', 'hard right', 'missed yes', 'false yes', 'unsure', 'failed', 's/item (median)',
            'cost $')
    w = [max(len(str(x[i])) for x in rows + [head]) for i in range(len(head))]
    for r in [head] + rows:
        print(' | '.join(str(v).ljust(w[i]) for i, v in enumerate(r)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('model', nargs='?')
    ap.add_argument('--cond', default='content', choices=['content', 'today'])
    ap.add_argument('--score', action='store_true')
    a = ap.parse_args()
    score() if a.score else run(a.model, a.cond)
