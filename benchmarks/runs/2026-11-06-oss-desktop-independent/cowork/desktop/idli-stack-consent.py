#!/usr/bin/env python3
"""Claude Code PreToolUse hook for the Builder's stack_install (narrative/TEAM_STACKS.md).

Claude Code shows the person a yes/no prompt whose reason is this summary, written by Idli from the stack files.
The Builder can't word it, and it never reaches the Builder. Installed by desktop/claude-builder.sh through a
--settings file kept outside extensions/, so the Builder can't remove it."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    json.load(sys.stdin)
except ValueError:
    pass
decision = 'ask'
try:
    from lib import stackwall
    data = sys.argv[1] if len(sys.argv) > 1 else os.environ['IDLI_DATA']
    text = stackwall.summary(data)
    if stackwall.agreed(data):  # the same things the person already said yes to (a retry with other versions)
        decision, text = 'allow', 'You already said yes to these.'
except Exception:
    text = "Idli couldn't read the stack. Say no, and ask the Builder to check stack.json and pixi.toml."
print(json.dumps({'hookSpecificOutput': {
    'hookEventName': 'PreToolUse', 'permissionDecision': decision,
    'permissionDecisionReason': ('Install for this team?\n' if decision == 'ask' else '') + text}}))
