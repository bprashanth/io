#!/bin/bash
# E7 runs. Each line: run name, chat model, spec-builder model, variants, scenarios, parallel chats.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."
mkdir -p results/e7-logs
run() {  # name model spec variants scenarios par
  PIPE_SPEC_MODEL=$3 "$HERE/e7_env.sh" run.py --run "$1" --models "$2" --variants "$4" --scenarios "$5" --par "$6" \
    > "results/e7-logs/$1.log" 2>&1
}
case "$1" in
  local) run e7-local local-qwen35-9b local-qwen35-9b e7-today,e7-today-g,e7-soft,e7-hard dev,held,held2,held3 2 ;;
  ling)  run e7-ling or-qwen35-9b or-ling3-flash e7-today,e7-today-g,e7-soft,e7-hard dev,held,held2,held3 4 ;;
  muse)  run e7-muse muse30b muse30b e7-today,e7-soft held3 2 ;;
esac
