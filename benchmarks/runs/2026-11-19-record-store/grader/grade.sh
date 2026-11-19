#!/bin/bash
# grade.sh NAME RESULTS.jsonl TASKS.json STORE_DIR PORT : a blind grader (Cursor agent in the wall) writes grades.json
set -euo pipefail
G=$(dirname "$(realpath "$0")"); NAME=$1; RES=$(realpath "$2"); TASKS=$(realpath "$3"); STORE=$(realpath "$4"); PORT=$5
RUN=${RS_RUN:-/tmp/rs}/grade-$NAME; rm -rf "$RUN"; mkdir -p "$RUN/work"
cp "$STORE/store.duckdb" "$RUN/store.duckdb"
PY="$G/../../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python"
"$PY" - "$RES" "$TASKS" "$RUN/work/transcripts.json" <<'PY'
import json, sys
res = [json.loads(l) for l in open(sys.argv[1])]
tasks = {t['id']: t for t in json.load(open(sys.argv[2]))}
out = []
for tid, t in tasks.items():
    turns = [r for r in res if r['task'] == tid]
    if not turns: continue
    out.append({'id': tid, 'kind': t['kind'], 'site': t['site'], 'request_turns': t['turns'], 'expect': t['expect'],
                'changes_things': t['changes_things'],
                'turns': [{'said': r['q'], 'commands': r.get('commands'), 'cannot': (r.get('plan') or {}).get('cannot'),
                           'needs': r.get('needs'), 'errors': r.get('errors'), 'rows_shown': (r.get('shown') or '')[:2500],
                           'reply': r.get('reply')} for r in sorted(turns, key=lambda r: r['turn'])]})
json.dump(out, open(sys.argv[3], 'w'), indent=1, ensure_ascii=False)
print(len(out), 'tasks')
PY
sed "s/{TODAY}/${RS_TODAY:-2026-11-19 (Thursday)}/" "$G/RUBRIC.md" > "$RUN/work/RUBRIC.md"
"$PY" -c "import sys; sys.path.insert(0, '$G/../../2026-11-06-oss-desktop-independent/cowork'); import os; os.chdir('$G/../../2026-11-06-oss-desktop-independent/cowork'); from lib import idlicli; open('$RUN/work/grammar.md','w').write(idlicli.grammar())"
"$PY" "$G/sqlserve.py" "$RUN/store.duckdb" "$PORT" > "$RUN/sql.out" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null || true' EXIT
for i in $(seq 1 30); do grep -q serving "$RUN/sql.out" && break; sleep 1; done
echo "Read RUBRIC.md and follow it exactly. Grade every task in transcripts.json and write grades.json." > "$RUN/prompt.txt"
cd /tmp && timeout 5400 "$G/../../2026-11-19-blind-tester/wall.sh" "$RUN/work" "$PORT" "$RUN/prompt.txt" > "$RUN/grader.jsonl" 2> "$RUN/grader.err" || true
ls -la "$RUN/work"
