"""Run the existing parent/child probe inside this container, with positive controls."""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile


def check():
    work = Path(tempfile.mkdtemp(prefix='.io-probe-', dir='/workspace'))
    outside = Path(tempfile.mkdtemp(prefix='probe-', dir='/state'))
    token = secrets.token_hex(12)
    try:
        shutil.copy('/opt/remote/probe.py', work/'probe.py')
        for p in [work/'read', outside/'read', outside/'write']:
            p.write_text(token)
        (work/'link').symlink_to(outside, target_is_directory=True)
        # Resolve before sandbox, then use raw numeric TCP, not curl/proxies/DNS failure.
        ip = socket.gethostbyname('chatgpt.com')
        manifest = dict(token=token, workspace_read=str(work/'read'), workspace_write=str(work/'write'),
                        outside_read=str(outside/'read'), outside_write=str(outside/'write'),
                        link_read=str(work/'link/read'), link_write=str(work/'link/write'),
                        endpoints=[dict(name='internet', host=ip, port=443, ack=False)])
        (work/'manifest.json').write_text(json.dumps(manifest))
        probe = ['python3', str(work/'probe.py'), str(work/'manifest.json')]
        def run(command):
            p = subprocess.run(command, cwd='/workspace', capture_output=True, text=True, timeout=60)
            if p.returncode:
                raise RuntimeError('Probe interpreter failed: '+p.stderr[-800:])
            lines = [l for l in p.stdout.splitlines() if l.startswith('IO_SANDBOX_PROBE=')]
            if len(lines) != 1:
                raise RuntimeError('Missing probe result')
            return json.loads(lines[0].split('=',1)[1])
        control = run(probe + ['control'])
        for name, value in control['checks'].items():
            if value['outcome'] != 'allowed':
                raise RuntimeError('Positive control failed: '+name)
        sandbox = run(['/opt/codex/bin/codex', 'sandbox', '-p','io','-P','io','-C','/workspace','--'] + probe + ['sandbox'])
        for name, value in sandbox['checks'].items():
            expected = 'allowed' if name in ('workspace_read','workspace_write','child_execution') else 'denied'
            if value['outcome'] != expected:
                raise RuntimeError('Sandbox contract failed: '+name+' '+str(value))
        after = run(probe + ['control-after'])
        for name, value in after['checks'].items():
            if value['outcome'] != 'allowed':
                raise RuntimeError('Post-probe positive control failed: '+name)
        return dict(ok=True, control=control, sandbox=sandbox, controlAfter=after)
    finally:
        shutil.rmtree(work)
        shutil.rmtree(outside)

if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
