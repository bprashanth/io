#!/bin/sh
# run.sh <mode> <script>... : a fresh data dir each time, the synthetic file, the copied households form
E=$(cd "$(dirname "$0")" && pwd)
C=$E/../2026-11-06-oss-desktop-independent/cowork
W=$(mktemp -d "${TMPDIR:-/tmp}/g9b.XXXXXX")
mkdir -p "$W/drive" "$W/home/config" && cp "$E/fixtures/drive/households.xlsx" "$W/drive/"
cd "$C" && MUSE_URL=${MUSE_URL:-http://127.0.0.1:8186} COWORK_DATA_DIR=$W IDLI_FILE_SKILLS=$E/fixtures/skills \
  IDLI_HOME=$W/home IDLI_NO_SHOW=1 exec .venv/bin/python "$E/harness.py" "$@"
