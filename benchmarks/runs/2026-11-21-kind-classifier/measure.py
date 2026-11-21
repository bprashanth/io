"""Can Clef tell what kind of ask a question is? Measured on every labelled task (dev, held-out, owner).
    python measure.py            # writes results.jsonl and prints accuracy and the confusion table
"""
import json, sys, time
from collections import Counter
from pathlib import Path
HERE = Path(__file__).parent
COWORK = HERE.parent / '2026-11-06-oss-desktop-independent' / 'cowork'
sys.path.insert(0, str(COWORK))
from lib import idlicli  # noqa: E402

KIND = {'trust': 'lookup', 'own_definition': 'judgement', 'own_workflow': 'workflow', 'other_site': 'elsewhere'}
bank = HERE.parent / '2026-11-19-record-store' / 'bank'
tasks = []
for f in ('tasks_dev.json', 'tasks_heldout.json', 'tasks_owner_dev.json'):
    for t in json.load(open(bank / f)):
        tasks.append((f, t['id'], t['kind'], t['turns'][0]))
out, conf = open(HERE / 'results.jsonl', 'w'), Counter()
right = 0
for f, tid, kind, q in tasks:
    t0 = time.time()
    lab, probs = idlicli.classify(q)
    exp = KIND[kind]
    right += lab == exp
    conf[(exp, lab)] += 1
    out.write(json.dumps({'bank': f, 'id': tid, 'q': q, 'expected': exp, 'got': lab, 'probs': probs,
                          'seconds': round(time.time() - t0, 2)}) + '\n')
print(f'{right} of {len(tasks)} right')
labs = ['lookup', 'judgement', 'workflow', 'elsewhere']
print('expected \\ got | ' + ' | '.join(labs))
for e in labs:
    print(f'{e} | ' + ' | '.join(str(conf[(e, g)]) for g in labs))
