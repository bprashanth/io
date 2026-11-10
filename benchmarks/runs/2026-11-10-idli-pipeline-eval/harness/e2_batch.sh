#!/bin/bash
# E2: teach all 5 files in one mode, 3 at a time. Usage: harness/e2_batch.sh <mode: real|fixed|...> [env...]
cd "$(dirname "$0")/.."
MODE=$1
STEMS="tree_plots_transects germination_protocol_filled household_survey_messy field_visits_messy tax_missing_info_fake"
for s in $STEMS; do
  while [ "$(jobs -r | wc -l)" -ge 3 ]; do sleep 5; done
  harness/e6_run.sh $s $MODE > /dev/null 2>&1 &
done
wait
echo "batch $MODE done"
