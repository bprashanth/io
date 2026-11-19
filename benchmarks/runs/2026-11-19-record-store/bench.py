"""Run task-bank sessions through `idli ask` on the real store. One process, so the masking scanner loads once.
    bench.py run --tasks bank/tasks_dev.json --mapper remote|nine --out results/dev-remote.jsonl [--only T01,T02]
"""
import argparse, json, os, sys, time
from pathlib import Path
COWORK = Path(__file__).resolve().parents[1] / '2026-11-06-oss-desktop-independent' / 'cowork'
sys.path.insert(0, str(COWORK))
os.chdir(COWORK)
from lib import recstore as rs, idlicli  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run'])
    ap.add_argument('--tasks', required=True)
    ap.add_argument('--mapper', default='remote')
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', default='')
    ap.add_argument('--sandbox', default=os.environ.get('IDLI_SANDBOX'))
    a = ap.parse_args()
    tasks = json.load(open(a.tasks))
    only = set(filter(None, a.only.split(',')))
    con = rs.connect(a.sandbox)
    out = open(a.out, 'a')
    for t in tasks:
        if only and t['id'] not in only:
            continue
        hist = []
        for i, q in enumerate(t['turns']):
            rec = idlicli.ask(con, q, hist, a.mapper, data_dir=a.sandbox)
            hist.append({k: rec.get(k) for k in ('q', 'commands', 'shown', 'reply')})
            rec.update(task=t['id'], turn=i, kind=t['kind'], site=t['site'])
            out.write(json.dumps(rec, default=str) + '\n'); out.flush()
            print(f"{t['id']}.{i} {rec.get('total_s')}s {rec.get('needs') or ''} {rec.get('commands')} {rec.get('errors') or ''}",
                  flush=True)
    print('size', rs.size_report(a.sandbox, con))


if __name__ == '__main__':
    main()
