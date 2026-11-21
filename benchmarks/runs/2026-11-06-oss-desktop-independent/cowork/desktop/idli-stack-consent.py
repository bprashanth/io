#!/usr/bin/env python3
"""Claude Code PreToolUse hook for the Builder's stack_install (narrative/TEAM_STACKS.md, PAGES_AND_TOOLS.md).

Claude Code shows the person a yes/no prompt whose reason is this summary, written by Idli from the catalog (tool
names, what for, sizes, cautions and licences), or for an older team from its stack files. The Builder can't word
it. When this computer can't run the tools, the call is refused here with the reasons, so the person isn't asked.
Installed by desktop/claude-builder.sh through a --settings file kept outside extensions/, so the Builder can't
remove it."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    event = json.load(sys.stdin)
except ValueError:
    event = {}
tools = (event.get('tool_input') or {}).get('tools') if isinstance(event, dict) else None
tools = [tools] if isinstance(tools, str) else [str(t) for t in tools or []]
decision = 'ask'
try:
    data = sys.argv[1] if len(sys.argv) > 1 else os.environ['IDLI_DATA']
    from lib import toolhome
    listed = toolhome.catalog_tools(data)
    if tools or listed:
        ids = tools or listed
        plan = toolhome.plan(data, ids)
        if not plan['ok']:
            decision = 'deny'
            text = ("This computer can't take these tools: " + ' '.join(plan['check']['reasons'] + plan['conflicts']))
        elif toolhome.agreed(data, ids):
            decision, text = 'allow', 'You already said yes to these.'
        else:
            text = toolhome.consent_summary(data, plan['new'] or ids)
    else:
        from lib import stackwall
        text = stackwall.summary(data)
        if stackwall.agreed(data):  # the same things the person already said yes to (a retry with other versions)
            decision, text = 'allow', 'You already said yes to these.'
except Exception:
    text = "Idli couldn't read what is being installed. Say no, and ask the Builder to check the catalog."
print(json.dumps({'hookSpecificOutput': {
    'hookEventName': 'PreToolUse', 'permissionDecision': decision,
    'permissionDecisionReason': ('Install for this team?\n' if decision == 'ask' else '') + text}}))
