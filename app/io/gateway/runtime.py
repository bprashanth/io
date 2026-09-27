"""Trusted Docker adapter. No client-supplied Docker names, commands, mounts or image."""
import json
import os
import secrets
import subprocess
import time
import urllib.request


class DockerRuntime:
    def __init__(self, image='io-remote-codex:v1', apparmor='io-remote-experiment'):
        self.image, self.apparmor = image, apparmor

    def docker(self, *args, **kwargs):
        result = subprocess.run(['docker', *args], capture_output=True, text=True,
                                timeout=120, **kwargs)
        if result.returncode:
            raise RuntimeError('Docker operation failed: ' + args[0])
        return result.stdout.strip()

    @staticmethod
    def names(workspace):
        name = 'io-v1-' + workspace['id'].removeprefix('workspace_')
        return name, name + '-net', name + '-state', name + '-files'

    def inspect(self, name):
        result = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=20)
        if result.returncode:
            return None
        return json.loads(result.stdout)[0]

    def ensure(self, workspace):
        name, network, state, files = self.names(workspace)
        runtime = self.inspect(name)
        if runtime is None:
            for volume in (state, files):
                self.docker('volume', 'create', '--label', 'io.v1.workspace=' + workspace['id'], volume)
            if self.inspect(network) is None:
                # network inspect is separate: Docker inspect resolves named networks too.
                self.docker('network', 'create', '--label', 'io.v1.workspace=' + workspace['id'], network)
            env = dict(os.environ, IO_REMOTE_TOKEN=workspace['token'])
            self.docker('create', '--name', name, '--hostname', 'io-workspace',
                        '--label', 'io.v1.workspace=' + workspace['id'], '--network', network,
                        '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                        '--security-opt', 'seccomp=unconfined', '--security-opt', 'apparmor=' + self.apparmor,
                        '--pids-limit', '256', '--memory', '2g', '--cpus', '2', '--user', '1000:1000',
                        '--mount', 'type=volume,src=' + state + ',dst=/state',
                        '--mount', 'type=volume,src=' + files + ',dst=/workspace',
                        '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777,size=256m',
                        '-e', 'IO_REMOTE_TOKEN', '-e', 'IO_REMOTE_PERSISTENT=1', self.image, env=env)
            runtime = self.inspect(name)
        if not runtime['State']['Running']:
            self.docker('start', name)
        endpoint = self.endpoint(workspace)
        for _ in range(120):
            try:
                req = urllib.request.Request(endpoint + '/status', headers={'Authorization': 'Bearer ' + workspace['token']})
                with urllib.request.urlopen(req, timeout=2) as response:
                    status = json.load(response)
                if status.get('sandbox') and status.get('persistent'):
                    return endpoint
            except Exception:
                pass
            time.sleep(.5)
        raise RuntimeError('Runtime did not establish sandbox readiness')

    def endpoint(self, workspace):
        name, network, _, _ = self.names(workspace)
        runtime = self.inspect(name)
        if not runtime or not runtime['State']['Running']:
            raise RuntimeError('Runtime is stopped; reconnect to restart it')
        address = runtime['NetworkSettings']['Networks'][network]['IPAddress']
        if not address:
            raise RuntimeError('Runtime has no private address')
        return 'http://' + address + ':8787'

    def delete(self, workspace):
        name, network, state, files = self.names(workspace)
        if self.inspect(name):
            self.docker('rm', '-f', name)
        if self.inspect(network):
            self.docker('network', 'rm', network)
        for volume in (state, files):
            result = subprocess.run(['docker', 'volume', 'inspect', volume], capture_output=True, timeout=20)
            if result.returncode == 0:
                self.docker('volume', 'rm', volume)
