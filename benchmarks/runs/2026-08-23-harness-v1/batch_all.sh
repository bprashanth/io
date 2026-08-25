#!/bin/bash
cd /home/beeps/src/github.com/bprashanth/io; R=benchmarks/runs/2026-08-23-harness-v1
EFFORT=none .venv-v2/bin/python $R/cx_batch.py qwen/qwen3.5-9b tools cx-9b-tools > $R/cx-9b-tools.log 2>&1 &
EFFORT=none .venv-v2/bin/python $R/cx_batch.py qwen/qwen3.5-9b free cx-9b-free > $R/cx-9b-free.log 2>&1 &
wait
.venv-v2/bin/python $R/cx_batch.py qwen/qwen3.8-27b free cx-27b-free > $R/cx-27b-free.log 2>&1 &
.venv-v2/bin/python $R/cx_batch.py qwen/qwen3.8-27b tools cx-27b-tools > $R/cx-27b-tools.log 2>&1 &
wait; echo BATCH-DONE
