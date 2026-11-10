#!/bin/bash
# Run the list_changed probe through the real Claude Code CLI (Haiku, one chat).
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(dirname "$HERE")/results/e7-listchanged"
mkdir -p "$OUT"
rm -f "$OUT/server.log"
cat > "$OUT/mcp.json" <<EOF
{"mcpServers": {"probe": {"command": "python3", "args": ["$HERE/listchanged_probe.py", "$OUT/server.log"]}}}
EOF
cd /tmp
timeout 300 claude -p --model claude-haiku-5-5 --setting-sources "" --strict-mcp-config --mcp-config "$OUT/mcp.json" \
  --allowedTools "mcp__probe__phase_one,mcp__probe__phase_two" --output-format json \
  "Call the tool mcp__probe__phase_one. Then, if a tool mcp__probe__phase_two exists, call it. Finally list the exact names of every mcp__probe tool you can see now, and say whether you called phase_two and what it returned." \
  > "$OUT/claude.json" 2>"$OUT/claude.err"
echo "exit $?"
python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['result'])" "$OUT/claude.json"
cat "$OUT/server.log"
claude --version
