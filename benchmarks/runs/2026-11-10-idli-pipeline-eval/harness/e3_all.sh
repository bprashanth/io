#!/bin/bash
# Run all E3 chats: the local 9B (2 repeats) and Muse (1), 3 at a time. Logs in results/e3-logs/all.log.
cd "$(dirname "$0")/.."
PY=/tmp/claude-1000/b9/sdkvenv/bin/python
convs=$(python3 -c "import json;print(' '.join(c['id'] for c in json.load(open('scenarios/e3.json'))['conversations']))")
jobs_list=()
for rep in r0 r1; do for c in $convs; do jobs_list+=("local-qwen35-9b $c $rep"); done; done
for c in $convs; do jobs_list+=("muse30b $c r0"); done
printf '%s\n' "${jobs_list[@]}" | xargs -P 3 -L 1 bash -c '
  m=$0; c=$1; rep=$2; out=results/e3/$m-$rep
  mkdir -p $out results/e3-logs/$m-$rep
  [ -f $out/$c.json ] && { echo "skip $m $c $rep"; exit 0; }
  echo "start $m $c $rep $(date +%T)"
  timeout 2400 '"$PY"' harness/e3_bounce.py --model $m --scenario scenarios/e3.json --conv $c --out $out > results/e3-logs/$m-$rep/$c.log 2>&1
  echo "end $m $c $rep rc=$? $(date +%T)"'
echo ALL DONE
