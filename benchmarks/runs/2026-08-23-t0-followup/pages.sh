#!/bin/bash
cd /home/beeps/src/github.com/bprashanth/io
O=benchmarks/runs/2026-08-23-t0-followup; K=~/.config/idlisseus/openrouter.json
for m in qwen/qwen3.5-9b qwen/qwen3.6-35b-a3b google/gemma-4-26b-a4b-it mistralai/ministral-8b-2512 qwen/qwen3.8-27b google/gemini-3.7-flash; do slug=$(echo $m | tr / _)
  eff=none; case $m in google/gemini-3.7-flash) eff=low;; esac
  for mode in free template; do
    .venv-v2/bin/python benchmarks/t0/run_page_gate.py --model $m --api-key-file $K --reasoning-effort $eff --mode $mode --output $O/pages/$slug-$mode > $O/pages.$slug-$mode.log 2>&1 &
  done
done
wait; echo PAGES-DONE
