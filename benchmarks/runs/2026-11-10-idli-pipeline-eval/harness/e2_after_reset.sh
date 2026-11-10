#!/bin/bash
# Wait for the Claude usage limit to reset (23:00 IST), then finish E2: the real file for the 4 files the limit
# broke, then the fixed fake copy for all 5. Usage: harness/e2_after_reset.sh
cd "$(dirname "$0")/.."
until [ "$(date +%H%M)" -ge 2303 ] || [ "$(date +%H)" -lt 12 ]; do sleep 30; done
claude -p --model claude-haiku-5-5 --max-turns 1 "reply ok" > results/e2-logs/limit-check.log 2>&1
if grep -q "hit your" results/e2-logs/limit-check.log; then echo "still limited"; exit 3; fi
harness/e2_batch.sh real tree_plots_transects germination_protocol_filled field_visits_messy tax_missing_info_fake
harness/e2_batch.sh fixed
python3 harness/e2_table.py > results/e2-logs/table.txt
echo "E2 after reset done"
