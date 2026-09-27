"""Real two-container evidence against serve_fixture.py; no model/account needed."""
import concurrent.futures
import json
import pathlib
import subprocess
import sys
import time
import httpx

state = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
base = 'http://127.0.0.1:8788'
checks = {}

def call(user, method, route, **kwargs):
    return httpx.request(method, base+route, headers={'Cf-Access-Jwt-Assertion': (state/(user+'.jwt')).read_text()}, timeout=100, trust_env=False, **kwargs)

def docker(*args):
    return subprocess.check_output(['docker',*args],text=True).strip()

def ok(name, condition):
    checks[name] = bool(condition)
    assert condition, name

def name(w): return 'io-v1-'+w.removeprefix('workspace_')

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    requests = list(executor.map(lambda _: call('alice','POST','/workspace'), range(2)))
    ok('concurrent_creation_ready',all(r.status_code==200 for r in requests))
    a=requests[0].json()['workspaceId']
    ok('concurrent_same_workspace',all(r.json()['workspaceId']==a for r in requests))
bresponse=call('bob','POST','/workspace');ok('second_user_ready',bresponse.status_code==200)
b=bresponse.json()['workspaceId'];ok('distinct_workspaces',a!=b)
(state/'workspaces.json').write_text(json.dumps({'alice':a,'bob':b}))
for method, route in [('GET','status'),('GET','events'),('GET','files'),('GET','file?name=sample.csv'),('POST','input'),('POST','files?name=other.csv'),('POST','end'),('GET','ports/8080')]:
    ok('ownership_'+method+'_'+route.split('?')[0],call('bob',method,f'/workspaces/{a}/{route}').status_code==404)
for user,w in [('alice',a),('bob',b)]:
    data=json.loads(docker('inspect',name(w)))[0]
    ok(user+'_no_published_ports',not data['HostConfig']['PortBindings'])
    ok(user+'_read_only_unprivileged',data['HostConfig']['ReadonlyRootfs'] and not data['HostConfig']['Privileged'] and data['Config']['User']=='1000:1000')
    ok(user+'_no_host_bind_mounts',all(m['Type']=='volume' for m in data['Mounts']))
    status=call(user,'GET',f'/workspaces/{w}/status').json()
    ok(user+'_sandbox_and_persistent',status['sandbox'] and status['persistent'])
    ok(user+'_no_inherited_auth',not status['loggedIn'])
route=f'/workspaces/{a}'
content=b'name,value\nalpha,2\nbeta,3\n'
ok('upload',call('alice','POST',route+'/files?name=sample.csv',content=content).status_code==201)
ok('identical_retry',call('alice','POST',route+'/files?name=sample.csv',content=content).json().get('reused'))
ok('conflict_rejected',call('alice','POST',route+'/files?name=sample.csv',content=b'other').status_code==400)
ok('download_exact',call('alice','GET',route+'/file?name=sample.csv').content==content)
for filename in ('../state/codex/auth.json','/state/codex/auth.json','../sample.csv'):
    ok('traversal_'+filename,call('alice','GET',route+'/file',params={'name':filename}).status_code==400)
# Outer boundary positive control: an A-only sentinel exists in A, not in B.
docker('exec',name(a),'python3','-c',"from pathlib import Path; Path('/state/tenant-sentinel').write_text('synthetic-a-only')")
ok('outer_other_user_state_absent',docker('exec',name(b),'python3','-c',"from pathlib import Path; print(Path('/state/tenant-sentinel').exists())")=='False')
# Synthetic service is operator-started; it is not a claim about Offline model-started listeners.
docker('exec',name(a),'python3','-c',"from pathlib import Path; Path('/workspace/index.html').write_text('<h1>IO gateway live service proof</h1>')")
docker('exec','-d',name(a),'python3','-m','http.server','8080','--bind','0.0.0.0','--directory','/workspace')
time.sleep(.5)
live=call('alice','GET',route+'/ports/8080')
ok('live_service_via_gateway',live.status_code==200 and b'IO gateway live service proof' in live.content)
ok('live_html_attachment',live.headers.get('content-disposition','').startswith('attachment'))
ok('other_port_rejected',call('alice','GET',route+'/ports/8787').status_code==404)
before=call('alice','GET',route+'/status').json()['instance']
docker('restart',name(a))
restart=call('alice','POST','/workspace')
ok('restart_same_workspace',restart.status_code==200 and restart.json()['workspaceId']==a)
ok('restart_new_runtime_instance',call('alice','GET',route+'/status').json()['instance']!=before)
ok('restart_file_persistence',call('alice','GET',route+'/file?name=sample.csv').content==content)
ok('restart_state_persistence',docker('exec',name(a),'cat','/state/tenant-sentinel')=='synthetic-a-only')
# Recreate the container from persistent volumes, preserving the opaque ID.
docker('rm','-f',name(a))
ok('recreate_ready',call('alice','POST','/workspace').status_code==200)
ok('recreate_file_persistence',call('alice','GET',route+'/file?name=sample.csv').content==content)
# Restore service for the subsequent UI test.
docker('exec','-d',name(a),'python3','-m','http.server','8080','--bind','0.0.0.0','--directory','/workspace')
(out/'integration.json').write_text(json.dumps({'checks':checks,'passed':sum(checks.values()),'realDocker':True,'realCloudflare':False,'modelTurns':False},indent=2))
print(json.dumps({'passed':sum(checks.values()),'failed':sum(not v for v in checks.values())}))
