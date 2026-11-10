#!/bin/bash
# E6 for one fixture: teach (headless) then score.  Usage: harness/e6_run.sh <stem> [fake|real] [model]
set -u
cd "$(dirname "$0")/.."
STEM=$1; MODE=${2:-fake}; MODEL=${3:-claude-sonnet-5-5}
export PIPE_TMP=${PIPE_TMP:-/tmp/claude-1000/pipe-eval}
mkdir -p "$PIPE_TMP" results/e6/$MODE
SDK=/tmp/claude-1000/b9/sdkvenv/bin/python
VENV=../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python
OUT=results/e6/$MODE/$STEM
EXTRA=""; [ "$MODE" = real ] && EXTRA="--real-teach"
timeout 3600 $SDK harness/teach_run.py fixtures/$STEM.xlsx $OUT --model "$MODEL" $EXTRA > $OUT.teach.log 2>&1
echo "teach exit $?" >> $OUT.teach.log
$VENV harness/e6_score.py fixtures/$STEM.xlsx $OUT $OUT.score.json > $OUT.score.log 2>&1
echo "score exit $?" >> $OUT.score.log
tail -2 $OUT.teach.log; tail -2 $OUT.score.log
