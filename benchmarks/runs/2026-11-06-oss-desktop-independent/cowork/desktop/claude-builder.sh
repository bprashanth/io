#!/bin/sh
# The Builder (narrative/MODEL_TYPES.md): the person's own Claude Code, working on one team's extensions/ folder.
# It adds capabilities (file readers, Analyst skills) with tests on fake samples. It reads the platform source as
# reference but can only change extensions/, and Claude Code's sandbox keeps it out of the team's real files, other
# teams and Idli's private folders. A checkpoint is saved before it starts, so the team card can go back.
# Started by lib/builder.py with IDLI_DATA (the team folder) and the masked request as the first prompt.
COWORK="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DATA=${IDLI_DATA:?IDLI_DATA is the team folder}
EXT="$DATA/extensions"
"$COWORK/.venv/bin/python" -I - "$COWORK" "$DATA" "$*" <<'PY' || { echo "Idli couldn't prepare the Builder." >&2; exit 1; }
import json, os, shutil, sys
from pathlib import Path
root, data, request = sys.argv[1:4]
sys.path.insert(0, root)
from lib import capmenu, catalog, launchsettings, rolelabels, teamcaps
ext = teamcaps.ensure(data)
teamcaps.checkpoint(data, ('Before: ' + request.split('"')[1] if request.count('"') >= 2 else 'Before the Builder')[:100])
team = teamcaps.team_name(data)
claude = ext / '.claude'
(claude / 'skills').mkdir(parents=True, exist_ok=True)
for sk in sorted((Path(root) / 'idli/builder-skills').iterdir()):
    if (sk / 'SKILL.md').is_file():
        shutil.rmtree(claude / 'skills' / sk.name, ignore_errors=True)
        shutil.copytree(sk, claude / 'skills' / sk.name)
caps, problems = teamcaps.manifest(data)
active = [c['title'] for c in teamcaps.capabilities(data)]
text = (Path(root) / 'idli/CLAUDE-builder.md').read_text().replace('{team}', team).replace('{platform}', root)
text += '\n## What ' + team + ' can do now (tested)\n' + '\n'.join('- ' + t for t in active) + '\n'
if problems:
    text += '\nProblems in manifest.json: ' + '; '.join(problems) + '\n'
text += '\n## The capability menu on this computer\n' + capmenu.describe() + '\n'
text += '\n## This computer\n' + catalog.describe_computer()
(claude / 'CLAUDE.md').write_text(text)
launchsettings.merge_builder(ext, data, root)
launchsettings.builder_hooks(data, root)
rolelabels.apply(claude / 'settings.json', 'builder', team)
mcp = {'mcpServers': {'idli': {'command': root + '/.venv/bin/python', 'args': ['-I', root + '/lib/idli_mcp.py'],
       'env': {'IDLI_ROLE': 'builder', 'IDLI_DATA': str(Path(data).resolve())}}}}
fd = os.open(claude / 'idli-mcp.json', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump(mcp, f)
# Claude Code's one-time "do you trust this folder?": answered for Idli's own folder, as for the Analyst.
p = os.path.expanduser('~/.claude.json')
try:
    conf = json.load(open(p))
except (OSError, ValueError):
    conf = None  # never rewrite a file we couldn't read
if conf is not None:
    e = conf.setdefault('projects', {}).setdefault(str(ext.resolve()), {})
    if not e.get('hasTrustDialogAccepted'):
        e['hasTrustDialogAccepted'] = True
        with open(p + '.idli-tmp', 'w') as f:
            json.dump(conf, f, indent=2)
        os.replace(p + '.idli-tmp', p)
PY
cd "$EXT" || exit 1
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CONFIG_DIR ANTHROPIC_BASE_URL
CLAUDE_BIN=${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}
export CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1
printf '\033]0;Builder\007'
# The account's claude.ai connectors (Drive, Gmail, Calendar) would reach real data around Idli's masking: off.
export ENABLE_CLAUDEAI_MCP_SERVERS=false
export MCP_TOOL_TIMEOUT=${MCP_TOOL_TIMEOUT:-3600000}
exec "$CLAUDE_BIN" "--mcp-config=$EXT/.claude/idli-mcp.json" --settings "$DATA/.idli/builder-settings.json" "$@"
