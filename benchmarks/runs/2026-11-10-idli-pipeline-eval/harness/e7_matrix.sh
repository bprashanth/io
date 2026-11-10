#!/bin/bash
# E7 runs (after merging the product's 12-tool change). Run each in the background; logs in results/e7-logs.
#   e7-product: shipped as is (12 tools, model builds the spec)   e7-p12: same 12 tools + split + guards
#   e7-soft: 9 tools, clicks run steps, own-card guard            e7-hard: e7-soft, listed per phase
#   e7-today: the old 29 tools + split (reference)
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."
mkdir -p results/e7-logs
run() {  # name model spec variants scenarios par
  PIPE_SPEC_MODEL=$3 "$HERE/e7_env.sh" run.py --run "$1" --models "$2" --variants "$4" --scenarios "$5" --par "$6" \
    > "results/e7-logs/$1.log" 2>&1
}
case "$1" in
  ling)  run e7-ling or-qwen35-9b or-ling3-flash e7-product,e7-p12,e7-soft,e7-hard,e7-today dev,held,held2,held3 4 ;;
  local) run e7-local local-qwen35-9b local-qwen35-9b e7-product,e7-p12,e7-soft,e7-hard held3,held2 2 ;;
  local2) run e7-local local-qwen35-9b local-qwen35-9b e7-product,e7-p12,e7-soft,e7-hard dev,held 2 ;;
  muse)  run e7-muse muse30b muse30b e7-product,e7-p12 held3 2 ;;
esac
