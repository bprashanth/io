#!/usr/bin/env python3
"""Exercise the real launcher in a temporary fake installation, without services or user state."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
COWORK = HERE.parent / "2026-11-06-oss-desktop-independent/cowork"


def executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


def main():
    with tempfile.TemporaryDirectory(prefix="relviz-launcher-") as temp:
        root = Path(temp)
        install, work, home, data = (root / name for name in ["fake cowork", "claude work", "fake home", "fake data"])
        for path in [install / "desktop", install / "idli", install / ".venv/bin", home, data / "drive"]:
            path.mkdir(parents=True)
        launcher = install / "desktop/claude-masked.sh"
        shutil.copy2(COWORK / "desktop/claude-masked.sh", launcher)
        shutil.copy2(COWORK / "idli/CLAUDE-masked.md", install / "idli/CLAUDE-masked.md")
        shutil.copytree(COWORK / "idli/claude-skills", install / "idli/claude-skills")
        # Simulate proxy readiness and skip the server. Execute only the launcher's
        # configuration-writing Python against our temporary paths.
        executable(install / ".venv/bin/python", f"#!{sys.executable}\n" + '''
import subprocess, sys
if len(sys.argv) > 2 and sys.argv[2].endswith('/lib/ccproxy.py'):
    print('12345')
elif len(sys.argv) > 2 and sys.argv[2] == '-':
    result = subprocess.run([sys.executable, *sys.argv[1:]], input=sys.stdin.buffer.read(), check=False)
    sys.exit(result.returncode)
''')
        fake_claude = root / "fake claude"
        executable(fake_claude, f"#!{sys.executable}\n" + '''
import json, os, pathlib, sys
assert 'ANTHROPIC_API_KEY' not in os.environ
assert 'ANTHROPIC_AUTH_TOKEN' not in os.environ
assert os.environ['ANTHROPIC_BASE_URL'] == 'http://127.0.0.1:12345'
pathlib.Path('launch-result.json').write_text(json.dumps({'cwd':os.getcwd(), 'args':sys.argv[1:]}))
''')
        env = {**os.environ, "HOME": str(home), "IDLI_DATA": str(data), "IDLI_CLAUDE_WORK": str(work),
               "CLAUDE_BIN": str(fake_claude), "ANTHROPIC_API_KEY": "synthetic-test-sentinel",
               "ANTHROPIC_AUTH_TOKEN": "synthetic-test-sentinel"}
        custom = work / ".claude/skills/custom/SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("User's unrelated local skill\n")

        def launch():
            subprocess.run(["sh", str(launcher), "--print", "synthetic question"], env=env, check=True,
                           capture_output=True, text=True)

        def verify():
            for source in (install / "idli/claude-skills").rglob("*"):
                if source.is_file():
                    target = work / ".claude/skills" / source.relative_to(install / "idli/claude-skills")
                    assert target.read_bytes() == source.read_bytes(), f"Skill resource did not copy: {source.name}"
            assert custom.read_text() == "User's unrelated local skill\n"
            assert (work / "CLAUDE.md").read_bytes() == (install / "idli/CLAUDE-masked.md").read_bytes()
            assert (work / "drive").resolve() == data / "drive"
            result = json.loads((work / "launch-result.json").read_text())
            assert result == {"cwd": str(work), "args": [f"--mcp-config={work}/.idli-mcp.json", "--print", "synthetic question"]}
            config = work / ".idli-mcp.json"
            assert config.stat().st_mode & 0o777 == 0o600
            assert json.loads(config.read_text())["mcpServers"]["idli"]["args"] == ["-I", str(install / "lib/idli_mcp.py")]

        launch()
        verify()
        # A second launch must refresh an already installed skill and its templates.
        (work / ".claude/skills/relationship-visuals/SKILL.md").write_text("outdated")
        (work / ".claude/skills/relationship-visuals/templates/matrix.vl.json").write_text("outdated")
        launch()
        verify()
        print("PASS: launcher installs and refreshes nested skill resources, preserves custom skills, handles spaces, and forwards Claude arguments")


if __name__ == "__main__":
    main()
