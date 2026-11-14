"""Run fixed synthetic Mini mappings against the REAL local 9B; no credentials or real data.

.venv/bin/python -m lib.eval_chat_mapping
"""
import collections
import json
import os
from pathlib import Path
import time
from lib import home

FIXTURE = Path(__file__).with_name('chat_fixtures')


def main():
    os.environ.setdefault('IDLI_9B_URL', 'http://127.0.0.1:8291')
    questions = home.read(FIXTURE / 'mini.json')['questions']
    cases = home.read(FIXTURE / 'mapping_cases.json')
    results = []
    for i, case in enumerate(cases):
        start = time.monotonic()
        mapped = home.map_questions(questions, case['text'])
        exact = mapped['qid'] == case['qid'] and mapped['params'] == case['params'] and mapped['method'] == 'idli-9b'
        results.append({**case, 'actual': mapped, 'correct': exact, 'seconds': round(time.monotonic()-start, 2)})
        print(f"{i+1}/{len(cases)} {case['type']}: {'pass' if exact else 'FAIL'}", flush=True)
    counts = collections.defaultdict(lambda: {'correct': 0, 'total': 0})
    for r in results:
        counts[r['type']]['total'] += 1
        counts[r['type']]['correct'] += r['correct']
    output = {'model': 'qwen3.5-9b', 'cases': len(results), 'correct': sum(r['correct'] for r in results),
              'by_type': dict(counts), 'results': results}
    home.write(Path(__file__).with_name('chat_mapping_results.json'), output)
    print(json.dumps({k:v for k,v in output.items() if k != 'results'}, indent=2))


if __name__ == '__main__':
    main()
