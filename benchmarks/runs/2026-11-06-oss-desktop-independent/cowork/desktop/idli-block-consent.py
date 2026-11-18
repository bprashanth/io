#!/usr/bin/env python3
"""Claude Code PreToolUse hook for the Builder's block_add (lib/transforms.py, narrative/SANDBOXES.md).

Idli checks the block first (a quick scan and its fake-data test). A block that fails is refused here with the
plain reason, and the person isn't asked. One that passes gets one card, worded by Idli, not the Builder:
"Add block: Read PDFs. Uses pypdf. Reads PDFs you give it. Sends nothing." Installed by
idli/builder-outside/builder_outside.py."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def decide(event):
    from lib import sandboxes, transforms
    args = (event.get('tool_input') or {}) if isinstance(event, dict) else {}
    name, want = str(args.get('name') or ''), ' '.join(str(args.get('sandbox') or '').split()).lower()
    root = (Path(sandboxes.builder_dir()) / 'blocks').resolve()
    folder = (root / name).resolve()
    if not name or not folder.is_relative_to(root) or not folder.is_dir():
        return 'deny', f'There is no block called {name} to add.'
    sb = next((s for s in sandboxes.list_all() if want and (want in (s['id'], str(s.get('name')).lower()) or
                                                           want in str(s.get('name')).lower())), None)
    if not sb:
        return 'deny', f'There is no sandbox called {args.get("sandbox")}.'
    res = transforms.check(folder)
    if not res['ok']:
        return 'deny', 'Idli did not add this block: ' + '; '.join(res['problems'][:4]) + '.'
    return 'ask', f'{res["card"]}\nFor {sb.get("name")}.'


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    try:
        decision, text = decide(event)
    except Exception:  # noqa: BLE001
        decision, text = 'deny', "Idli couldn't check this block. Ask the Builder to try again."
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision,
                                             'permissionDecisionReason': text}}))


if __name__ == '__main__':
    os.environ.setdefault('PYTHONUTF8', '1')
    main()
