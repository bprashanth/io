"""Trimmed menu vs full menu, same tasks, same code: errors, repairs, failures, empty results, menu misses, size.
    python compare.py   (after both runs)"""
import json, statistics as st
from pathlib import Path
R = Path(__file__).parent / 'results'
for t in ('tasks_dev', 'tasks_owner_dev'):
    for v in ('nine', 'nine-fullmenu'):
        p = R / f'{t}-{v}.jsonl'
        if not p.exists():
            continue
        rs = [json.loads(l) for l in p.read_text().splitlines()]
        misses = [r for r in rs if r.get('menu_miss')]
        print(f'{t:16} {v:14} turns {len(rs):3} | step errors {sum(bool(r.get("errors")) for r in rs):2} | '
              f'repaired {sum(bool(r.get("repaired")) for r in rs):2} | mapper failed '
              f'{sum(r.get("needs") == "mapper_failed" for r in rs):2} | empty '
              f'{sum("Nothing matches" in (r.get("shown") or "") for r in rs):2} | menu misses {len(misses):2} '
              f'(with an error {sum(m["menu_miss"]["had_errors"] for m in misses)}) | prompt chars median '
              f'{int(st.median([r.get("prompt_chars") or 0 for r in rs]))}')
        for m in misses:
            print(f'      miss {m["task"]}.{m["turn"]}: {m["menu_miss"]} | {m.get("commands")}'[:300])
