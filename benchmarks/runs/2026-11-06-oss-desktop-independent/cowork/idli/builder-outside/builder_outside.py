"""Write the Builder folder's Claude Code files: its instructions, the /sandbox command, Idli's MCP server in the
outside role (sandbox tools only) and settings that load it. Called by desktop/idli-bootstrap.py."""
import json
import os
import shutil
import sys


def _q(p):
    return "'" + p.replace("'", "'\\''") + "'"


def setup(folder, cowork):
    here = os.path.join(cowork, 'idli', 'builder-outside')
    os.makedirs(os.path.join(folder, '.claude', 'commands'), exist_ok=True)
    shutil.copyfile(os.path.join(here, 'CLAUDE.md'), os.path.join(folder, 'CLAUDE.md'))
    shutil.copyfile(os.path.join(here, 'commands', 'sandbox.md'), os.path.join(folder, '.claude', 'commands',
                                                                                'sandbox.md'))
    with open(os.path.join(folder, '.mcp.json'), 'w') as f:
        json.dump({'mcpServers': {'idli': {'command': os.path.join(cowork, '.venv', 'bin', 'python'),
                                           'args': ['-I', os.path.join(cowork, 'lib', 'idli_mcp.py')],
                                           'env': {'IDLI_ROLE': 'outside'}}}}, f, indent=2)
    path = os.path.join(folder, '.claude', 'settings.json')
    s = json.load(open(path)) if os.path.exists(path) else {}
    s['enableAllProjectMcpServers'] = True
    s['enabledMcpjsonServers'] = sorted(set(s.get('enabledMcpjsonServers', []) + ['idli']))
    perms = s.setdefault('permissions', {})
    perms['allow'] = sorted(set(perms.get('allow', []) + ['mcp__idli__sandbox_blocks', 'mcp__idli__sandbox_list',
                                                          'mcp__idli__block_kit', 'mcp__idli__block_check']))
    # block_add: Idli checks the block and asks the person with one card (desktop/idli-block-consent.py)
    hook = {'matcher': 'mcp__idli__block_add', 'hooks': [{'type': 'command', 'command': ' '.join([
        _q(os.path.join(cowork, '.venv', 'bin', 'python')), '-I',
        _q(os.path.join(cowork, 'desktop', 'idli-block-consent.py'))])}]}
    pre = [h for h in s.setdefault('hooks', {}).get('PreToolUse', []) if h.get('matcher') != hook['matcher']]
    s['hooks']['PreToolUse'] = pre + [hook]
    with open(path, 'w') as f:
        json.dump(s, f, indent=2)


if __name__ == '__main__':
    setup(sys.argv[1], sys.argv[2])
