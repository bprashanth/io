#!/bin/bash
# Ask Codex to implement SPEC.md here. Usage: run_codex.sh "<prompt>" <log>
cd "$(dirname "$0")/.."
timeout 2400 codex exec -s workspace-write --skip-git-repo-check -C . "$1" > "$2" 2>&1
echo "exit $?" >> "$2"
