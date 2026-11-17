#!/usr/bin/env python3
"""Claude Code PreToolUse hook for the Builder's test_account_set (narrative/BUILDER_JOURNEY.md).

The person sees a yes/no prompt that Idli words, not the Builder. When the email is not signed in to that profile,
the call is refused here and the person isn't asked. Installed by desktop/claude-builder.sh through
<team>/.idli/builder-settings.json, outside extensions/, so the Builder can't remove it. Same pattern as
idli-stack-consent.py."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def decide(event, data):
    from lib import chromeprofiles
    args = (event.get('tool_input') or {}) if isinstance(event, dict) else {}
    profile, email, role = (str(args.get(k) or '').strip() for k in ('profile', 'email', 'role'))
    email = email.lower()
    why = chromeprofiles.check_new_account(profile, email, role)
    if why:
        return 'deny', why
    if chromeprofiles.is_confirmed(data, profile, email, role):
        return 'allow', 'You already said yes to this test account.'
    return 'ask', (f'Use {email} in Chrome profile {chromeprofiles.label(profile)} as a TEST account for this team?\n'
                   'Only say yes if it is not a real account.\n'
                   f'The Builder will use it as "{role}", and may send email between this team\'s test accounts.')


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    try:
        data = sys.argv[1] if len(sys.argv) > 1 else os.environ['IDLI_DATA']
        decision, text = decide(event, data)
    except Exception:
        decision, text = 'deny', "Idli couldn't check this account. Ask the Builder to try again."
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision,
                                             'permissionDecisionReason': text}}))


if __name__ == '__main__':
    main()
