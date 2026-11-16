"""Labels for the two Claude Code terminals (narrative/MODEL_TYPES.md): Claude Code itself is unchanged; only its
startup announcement and a coloured status line say Analyst or Builder, so a person can tell them apart at a glance."""
import json
import os
import shlex
import tempfile
from pathlib import Path

LABEL = Path(__file__).resolve().parent.parent / 'desktop' / 'idli-label.sh'
WORDS = {
    'analyst': lambda team: f'Analyst for {team}. Private values reach me as codes. I work within what {team} '
                            'knows how to do.',
    'builder': lambda team: f'Builder for {team}. I add new abilities to {team} with fake samples. I never see '
                            'your files.',
}


def apply(settings_path, role, team):
    path = Path(settings_path)
    settings = json.loads(path.read_text()) if path.exists() else {}
    settings['companyAnnouncements'] = [WORDS[role](team)]
    settings['statusLine'] = {'type': 'command', 'padding': 0,
                              'command': ' '.join(shlex.quote(str(x)) for x in (LABEL, role, team))}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, 'w') as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp, path)


def title(role):
    """The terminal's title (Paseo shows it on the tab)."""
    return '\033]0;' + role.capitalize() + '\007'
