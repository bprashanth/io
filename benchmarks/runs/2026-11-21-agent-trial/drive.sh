#!/bin/bash
# drive.sh SANDBOX: run turns.txt through the real CLI like a person would; a yes card gets "yes"
cd ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
export IDLI_SANDBOX=$1
OUT=~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-21-agent-trial/transcript.md
: > $OUT
while IFS='|' read -r mode q; do
  [ -z "$q" ] && continue
  flag=""; [ "$mode" = NEW ] && flag="--new"
  { echo "## $q"; echo '```'; } >> $OUT
  t0=$(date +%s.%N)
  ans=$(desktop/idli ask $flag "$q" < /dev/null 2>&1)
  echo "$ans" >> $OUT
  if echo "$ans" | grep -q "To keep it: idli ask yes"; then
    echo "--- (said: yes)" >> $OUT
    desktop/idli ask yes < /dev/null >> $OUT 2>&1
  fi
  printf '```\n(%.1f s)\n\n' "$(echo "$(date +%s.%N) - $t0" | bc)" >> $OUT
done < ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-21-agent-trial/turns.txt
echo done
