#!/usr/bin/env python3
"""Trusted operator provisioning, NOT a public API. One connection file per user/session."""
import argparse
import json
import os
import pathlib
import secrets
import subprocess
import sys
import time
import socket
import urllib.request
import urllib.parse
import tempfile

p = argparse.ArgumentParser()
p.add_argument('action', choices=['create', 'restore', 'destroy'])
p.add_argument('--connection', required=True, type=pathlib.Path)
p.add_argument('--image', default='io-remote-codex:experiment')
p.add_argument('--port', type=int, default=0)
p.add_argument('--apparmor', default='io-remote-experiment')
p.add_argument('--ttl', type=int, default=14400)
a = p.parse_args()
def docker(*args, **kw):
    return subprocess.check_output(['docker', *args], text=True, **kw).strip()
if a.action == 'destroy':
    data = json.loads(a.connection.read_text())
    subprocess.run(['docker', 'rm', '-f', data['container']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['docker', 'network', 'rm', data['network']], check=True)
    a.connection.unlink()
    sys.exit()
previous = None
if a.action == 'restore':
    previous = json.loads(a.connection.read_text())
    if subprocess.run(['docker', 'inspect', previous['container']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        p.error('The previous container still exists; restore never replaces a live or stopped workspace')
    url = urllib.parse.urlsplit(previous['url'])
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or len(previous.get('token', '')) < 40:
        p.error('Restore requires the original server-side connection file')
    a.port = url.port
elif a.connection.exists():
    p.error('Connection file already exists; do not replace a live session')
if not 0 <= a.port <= 65535 or not 60 <= a.ttl <= 86400:
    p.error('Invalid port or TTL')
if a.port == 0:
    # Pin the chosen port explicitly: Docker's dynamic publication can change on restart.
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        a.port = reserve.getsockname()[1]
name = 'io-remote-' + secrets.token_hex(8)
token = previous['token'] if previous else secrets.token_urlsafe(48)
network = name + '-net'
docker('network', 'create', network)
try:
    env = dict(os.environ, IO_REMOTE_TOKEN=token)
    docker('run', '-d', '--rm', '--name', name, '--hostname', 'io-session',
           '--network', network, '--read-only', '--cap-drop', 'ALL',
           '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined',
           '--security-opt', 'apparmor=' + a.apparmor, '--pids-limit', '256',
           '--memory', '2g', '--cpus', '2', '--user', '1000:1000',
           '--tmpfs', '/state:rw,nosuid,nodev,mode=0700,uid=1000,gid=1000,size=256m',
           '--tmpfs', '/workspace:rw,nosuid,nodev,mode=0700,uid=1000,gid=1000,size=512m',
           '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777,size=256m',
           '-p', '127.0.0.1:%s:8787' % a.port, '-e', 'IO_REMOTE_TOKEN',
           '-e', 'IO_REMOTE_TTL=' + str(a.ttl), a.image, env=env)
    port = docker('port', name, '8787/tcp').rsplit(':', 1)[1]
    endpoint = 'http://127.0.0.1:' + port
    ready = False
    for _ in range(120):
        try:
            req = urllib.request.Request(endpoint + '/status', headers={'Authorization':'Bearer '+token})
            with urllib.request.urlopen(req, timeout=2) as response:
                ready = json.load(response).get('sandbox') is True
            if ready:
                break
        except Exception:
            pass
        if subprocess.run(['docker','inspect',name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            raise RuntimeError('Worker exited before readiness; verify nested sandbox provisioning and internet positive control')
        time.sleep(.5)
    if not ready:
        raise RuntimeError('Worker did not establish sandbox readiness')
    a.connection.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = dict(url='http://127.0.0.1:' + port, token=token, container=name, network=network)
    if previous:
        fd, staged = tempfile.mkstemp(prefix='.connection-', dir=a.connection.parent)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(metadata, f)
            os.replace(staged, a.connection)
        finally:
            if os.path.exists(staged): os.unlink(staged)
        subprocess.run(['docker', 'network', 'rm', previous['network']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        fd = os.open(a.connection, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(metadata, f)
    print(json.dumps(dict(connection=str(a.connection), endpoint='http://127.0.0.1:' + port,
                          expiresIn=a.ttl)))
except Exception:
    subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['docker', 'network', 'rm', network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raise
