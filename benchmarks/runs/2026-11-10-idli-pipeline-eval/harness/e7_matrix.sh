#!/bin/bash
# E7 runs (after merging the product's 12-tool change). Run each in the background; logs in results/e7-logs.
#   e7-product: shipped as is (12 tools, model builds the spec)   e7-p12: same 12 tools + split + guards
#   e7-soft: 9 tools, clicks run steps, own-card guard            e7-hard: e7-soft, listed per phase
#   e7-today: the old 29 tools + split (reference)
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."
mkdir -p results/e7-logs
run() {  # name model spec variants scenarios par reps
  PIPE_SPEC_MODEL=$3 "$HERE/e7_env.sh" run.py --run "$1" --models "$2" --variants "$4" --scenarios "$5" --par "$6" \
    --reps "${7:-1}" >> "results/e7-logs/$1.log" 2>&1
}
# Ling-3.0-flash and the OpenRouter 9B were dropped (not free-tier options): results/ling-not-free-tier.
# The local 9B serves 4 slots (harness/serve9b.sh); its own dial-setting call shares them.
case "$1" in
  # the owner's narrowed E7: local 9B + split on the 12 shipped tools, soft and hard phases, 2 repeats
  local12) run e7-local12 local-qwen35-9b local-qwen35-9b e7-soft12,e7-hard12 held3,held2,dev,held 4 2 ;;
  muse)  run e7-muse muse30b muse30b e7-product held3 2 ;;
esac
