"""Summarise a blind session for grading: the tester's commands (anything but ./ask is flagged as cheating), each
turn (question, route, commands Idli ran, time, wire leaks, the reply), and the tester's final trust report.

  python analyze.py <run-dir>/<session>    -> prints markdown (real values: keep it out of git)
"""
import json
import sys
from pathlib import Path


def main(d):
    d = Path(d)
    rows = [json.loads(ln) for ln in (d / 'tester.jsonl').read_text().splitlines() if ln.strip().startswith('{')]
    cmds, texts = [], []
    for r in rows:
        if r.get('type') == 'tool_call' and r.get('subtype') == 'started':
            tc = r.get('tool_call') or {}
            kind = next(iter(tc), '?')
            args = (tc.get(kind) or {}).get('args') or {}
            cmds.append((kind, args.get('command') or json.dumps(args)[:200], args.get('timeout')))
        if r.get('type') == 'assistant':
            for c in (r.get('message') or {}).get('content') or []:
                if c.get('type') == 'text':
                    texts.append(c.get('text', ''))
    cheat = [c for c in cmds if c[0] != 'shellToolCall' or not str(c[1]).lstrip().startswith(('./ask', 'ask '))]
    print(f'# {d.name}\n\nTester commands: {len(cmds)}; not ./ask: {len(cheat)}')
    for c in cheat:
        print(f'- FLAG {c[0]}: {str(c[1])[:200]}')
    turns = [json.loads(ln) for ln in (d / 'turns.jsonl').read_text().splitlines() if ln.strip()] \
        if (d / 'turns.jsonl').is_file() else []
    for i, t in enumerate(turns, 1):
        print(f'\n## {i}. {t.get("question")}\n- route: {t.get("route")}; ran: {t.get("ran")}; '
              f'{t.get("wall_secs")} s; wire leaks: {t.get("wire_leaks")}; mapped: {json.dumps(t.get("mapped"))[:300]}')
        print('\n```\n' + str(t.get('reply'))[:1800] + '\n```')
    wire = d / 'sandbox' / 'wire.jsonl'
    if wire.is_file():
        w = [json.loads(ln) for ln in wire.read_text().splitlines() if ln.strip()]
        print(f'\nWire: {len(w)} payloads ({sum(x["to"] == "sandbox-claude" for x in w)} to Sandbox Claude); '
              f'with known leaks: {sum(bool(x["leaks"]) for x in w)} {sorted({v for x in w for v in x["leaks"]})}')
    print('\n## Tester final message\n\n' + (texts[-1] if texts else '(none)'))


if __name__ == '__main__':
    main(sys.argv[1])
