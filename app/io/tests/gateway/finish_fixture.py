"""Final conformance/lifecycle checks and removal of only the two synthetic runtimes."""
import json
import pathlib
import subprocess
import sys
import httpx
state=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); ids=json.loads((state/'workspaces.json').read_text())
checks={}
def call(user,method,path,**kw):
 return httpx.request(method,'http://127.0.0.1:8788'+path,headers={'Cf-Access-Jwt-Assertion':(state/(user+'.jwt')).read_text()},trust_env=False,timeout=90,**kw)
def run(*args):return subprocess.check_output(['docker',*args],text=True).strip()
def ok(key,value):checks[key]=bool(value);assert value,key
def name(user):return 'io-v1-'+ids[user].removeprefix('workspace_')
a,b=name('alice'),name('bob'); endpoint=json.loads(run('inspect',b))[0]['NetworkSettings']['Networks'][b+'-net']['IPAddress']
probe="import socket,sys; s=socket.socket();s.settimeout(2);print(s.connect_ex((sys.argv[1],8787)));s.close()"
ok('other_runtime_positive_control',run('exec',b,'python3','-c',probe,endpoint)=='0')
ok('other_runtime_network_denied',run('exec',a,'python3','-c',probe,endpoint)!='0')
# Real pinned Codex sandbox must not read its own controller's private state, including auth storage.
command=['docker','exec',a,'/opt/codex/bin/codex','sandbox','-p','io','-P','io','-C','/workspace','--','python3','-c',"from pathlib import Path; print(Path('/state/tenant-sentinel').read_text())"]
ok('controller_state_positive_control',run('exec',a,'cat','/state/tenant-sentinel')=='synthetic-a-only')
blocked=subprocess.run(command,capture_output=True,text=True)
ok('controller_state_denied_to_commands',blocked.returncode!=0 and any(error in blocked.stderr for error in ('PermissionError', 'FileNotFoundError')))
# Actual Codex JSONL wire shape, synthetic session metadata. This is not a model-turn claim.
first='11111111-1111-4111-8111-111111111111';second='22222222-2222-4222-8222-222222222222'
script="""import json,pathlib,sys
root=pathlib.Path('/state/codex/sessions/2026/09/27');root.mkdir(parents=True,exist_ok=True)
for value in sys.argv[1:]:
 (root/('rollout-2026-09-27T00-00-00-'+value+'.jsonl')).write_text(json.dumps({'type':'session_meta','timestamp':'2026-09-27T00:00:00Z','payload':{'id':value,'timestamp':'2026-09-27T00:00:00Z','cwd':'/workspace'}})+'\\n')
"""
run('exec',a,'python3','-c',script,first,second)
route='/workspaces/'+ids['alice']
listed=call('alice','GET',route+'/conversations').json()['conversations']
ok('two_saved_conversations',set(c['id'] for c in listed)=={first,second})
ok('conversation_delete',call('alice','POST',route+'/conversations/delete',json={'conversationId':first}).status_code==200)
ok('other_conversation_retained',[c['id'] for c in call('alice','GET',route+'/conversations').json()['conversations']]==[second])
ok('conversation_delete_preserves_files',call('alice','GET',route+'/file?name=sample.csv').status_code==200)
for user in ('alice','bob'):
 ok(user+'_delete_workspace',call(user,'POST','/workspaces/'+ids[user]+'/end').status_code==200)
 for suffix in ('','-net','-state','-files'):
  kind=['volume','inspect'] if suffix in ('-state','-files') else ['inspect']
  result=subprocess.run(['docker',*kind,name(user)+suffix],capture_output=True)
  ok(user+'_removed'+suffix,result.returncode!=0)
 if user=='alice':ok('other_workspace_survives_delete',call('bob','GET','/workspaces/'+ids['bob']+'/status').status_code==200)
(out/'lifecycle.json').write_text(json.dumps({'checks':checks,'passed':sum(checks.values()),'conversationFixtures':'synthetic JSONL; no authorized model turns'},indent=2));print(json.dumps({'passed':sum(checks.values())}))
