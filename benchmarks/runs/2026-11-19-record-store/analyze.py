"""Tables from a run and its grades: coverage, correctness and reply quality by kind of ask; latency; judging.
    analyze.py RESULTS.jsonl [GRADES.json]
"""
import json, statistics as st, sys
from collections import Counter, defaultdict
res = [json.loads(l) for l in open(sys.argv[1])]
grades = {g['id']: g for g in json.load(open(sys.argv[2]))} if len(sys.argv) > 2 else {}
by_task = defaultdict(list)
for r in res:
    by_task[r['task']].append(r)
kinds = defaultdict(list)
for tid, rs_ in by_task.items():
    kinds[rs_[0]['kind']].append(tid)
lat = [r['total_s'] for r in res if r.get('total_s') is not None]
nonjudge = [r['total_s'] for r in res if not r.get('judge_s')]
print(f'turns {len(res)}, tasks {len(by_task)}; median turn {st.median(lat):.1f}s, without judging {st.median(nonjudge):.1f}s, '
      f'max {max(lat):.0f}s; 9B judging total {sum(r.get("judge_s") or 0 for r in res):.0f}s')
print('mapper said cannot:', Counter(r.get('needs') for r in res if r.get('needs')))
print('turns with a failed command:', sum(1 for r in res if r.get('errors')), '; reply wording discarded:',
      Counter((r.get('compose_fallback') or '').split(':')[0] for r in res if r.get('compose_fallback')))
if grades:
    print(f'\n| kind | tasks | coverage yes | new connector | new write | design miss | correct | partial | wrong | refused ok | refused wrong | failed | fit | ack | not repetitive |')
    print('|---|' + '---|' * 14)
    for k in ['trust', 'own_definition', 'own_workflow', 'other_site', 'ALL']:
        ids = [t for t in by_task if (k == 'ALL' or by_task[t][0]['kind'] == k) and t in grades]
        g = [grades[t] for t in ids]
        c, k2 = Counter(x.get('coverage') for x in g), Counter(x.get('correctness') for x in g)
        multi = {t for t in ids if len(by_task[t]) > 1}
        def avg(f):
            v = [grades[t][f] for t in ids if isinstance(grades[t].get(f), (int, float)) and (f == 'fit' or t in multi)]
            return f'{st.mean(v):.1f}' if v else '-'
        print(f'| {k} | {len(g)} | {c["yes"]} | {c["new_connector"]} | {c["new_write"]} | {c["design_miss"]} | {k2["correct"]} | '
              f'{k2["partial"]} | {k2["wrong"]} | {k2["refused_ok"]} | {k2["refused_wrong"]} | {k2["failed"]} | {avg("fit")} | {avg("ack")} | {avg("repetitive")} |')
    print('\nDesign misses and wrong answers:')
    for t, x in sorted(grades.items()):
        if x.get('coverage') == 'design_miss' or x.get('correctness') in ('wrong', 'refused_wrong', 'failed'):
            print(f'- {t} [{x.get("coverage")}/{x.get("correctness")}] {x.get("notes")}')
