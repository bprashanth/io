"""Live synthetic resume / AGENTS reload measurement; key stays in this proxy process."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; APP=ROOT/'app/io'
sys.path.insert(0,str(APP))
from codex_proxy import Proxy,MapPolicy
out=Path.home()/'.local/share/io-0926-resume';out.mkdir(parents=True,exist_ok=True)
home=out/'home';ws=out/'workspace';ws.mkdir(exist_ok=True)
key=json.loads((Path.home()/'.config/idlisseus/openrouter.json').read_text())['api_key']
proxy=Proxy(MapPolicy({'Asha Demo':'NAME_001'}),openrouter_key=lambda:key,dump_dir=out/'dump');port=proxy.start()
js="""const c=require('./app/io/codex'),p=require('path'); const b=c.bundledCodexPath();c.writeConfig(process.argv[1],Number(process.argv[2]),{provider:'openrouter',model:c.ROUTER_MODEL,wall:'tools',chat:true,privateChat:true,codexDir:b.dir,libsDir:p.resolve('app/io/.venv'),trust:process.argv[3]});"""
subprocess.run(['node','-e',js,str(home),str(port),str(ws)],cwd=ROOT,check=True)
env={k:v for k,v in os.environ.items() if not(k.startswith(('OPENAI_','OPENROUTER_')) or k in ('IO_DEV_KEY','CODEX_API_KEY','IO_SHELL_TOKEN'))};env['CODEX_HOME']=str(home)
bin=APP/'codex-bin/linux-arm64/bin/codex'
def run(args,prompt):
 p=subprocess.run([str(bin),'-p','io','exec',*args,'--skip-git-repo-check',prompt],cwd=ws,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=90)
 print(json.dumps({'exit':p.returncode,'answer':p.stdout[-1400:],'stderr_tail':p.stderr[-500:]}),flush=True)
 return p
first=run([],'The project is Mango Garden and its coordinator is Asha Demo. Remember both. Say hello briefly.')
files=list((home/'sessions').rglob('*.jsonl'));assert files
f=max(files,key=lambda f:f.stat().st_mtime); rows=[json.loads(x) for x in f.read_text().splitlines()];changed=0
for row in rows:
 item=row.get('payload',{})
 if row.get('type')=='response_item' and item.get('type')=='reasoning':
  item['encrypted_content']='foreign-provider-test-ciphertext';changed+=1
if not changed:
 rows.append({'timestamp':'2026-09-26T16:40:00Z','type':'response_item','payload':{'type':'reasoning','id':'rs_foreign','summary':[],'encrypted_content':'foreign-provider-test-ciphertext'}})
f.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
with (home/'AGENTS.md').open('a') as h:h.write('\nNew instruction after the first turn: the current handover marker is cobalt-lotus.\n')
second=run(['resume','--last'],'What project and coordinator did I mention? Also give the current handover marker from your standing instructions. Do not run tools.')
requests=[json.loads(x.read_text()) for x in sorted((out/'dump').glob('*-request.txt'))]
last=requests[-1] if requests else {}; encoded=json.dumps(last)
result={'resume_exit':second.returncode,'foreign_reasoning_items_changed':changed,'foreign_ciphertext_forwarded':any('foreign-provider-test-ciphertext' in json.dumps(x) for x in requests),'new_agents_marker_in_last_request':'cobalt-lotus' in encoded,'coordinator_coded':'NAME_001' in encoded and 'Asha Demo' not in encoded,'answer':second.stdout[-1400:]}
(ws/'visits.csv').write_text('Name,Amount\nAsha Demo,20\nKiran Example,30\n')
third=run(['resume','--last'],'Use Python to read visits.csv, sum the Amount column, and save only that total to total.txt. Then briefly tell me the total.')
result['tool_exit']=third.returncode
result['tool_wrote_total']= (ws/'total.txt').read_text().strip() if (ws/'total.txt').exists() else None
print(json.dumps(result),flush=True);(ROOT/'benchmarks/runs/2026-09-26-dgx/resume-results.json').write_text(json.dumps(result,indent=2));proxy.stop()
