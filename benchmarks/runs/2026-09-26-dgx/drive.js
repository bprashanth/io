// Real Electron + bundled Codex + live OpenRouter, synthetic files only.
// xvfb-run -a node benchmarks/runs/2026-09-26-dgx/drive.js
// Native file selection is stubbed; every app action uses the visible controls.
const {_electron} = require('../../../installation/smoke/node_modules/playwright');
const fs = require('fs'), path = require('path'), os = require('os'), assert = require('assert');
const {spawnSync} = require('child_process');
const ROOT = path.resolve(__dirname, '../../..');
const APP = path.join(ROOT,'app/io');
const DATA = path.join(os.homedir(),'.local/share/io-0926-e2e');
const OUT = __dirname;
const steps=[];const mark=(step,details={})=>{steps.push({step,...details});console.log(JSON.stringify(steps.at(-1)));};
fs.mkdirSync(DATA,{recursive:true});
const fixture=path.join(DATA,'synthetic-visits.csv');
fs.writeFileSync(fixture,'Name,Phone,Amount\nAsha Demo,9876543210,20\nKiran Example,9123456789,30\n');
function probe(st) {
 const c=require(path.join(APP,'codex'));const bin=c.bundledCodexPath();const alias=fs.mkdtempSync(path.join(os.tmpdir(),'io-drive-alias-'));
 fs.symlinkSync(bin.path,path.join(alias,'codex-linux-sandbox'));
 const env=c.baseEnv(st.home,path.join(APP,'.venv'));env.PATH=alias+path.delimiter+env.PATH;
 const r=spawnSync(bin.path,['sandbox','-p','io','-P','io','-C',st.folder,'--','sh','-c','curl --max-time 10 -s -o /dev/null -w "%{http_code}" https://example.com'],{env,encoding:'utf8',timeout:20000});
 fs.rmSync(alias,{recursive:true,force:true});return {status:r.status,http:r.stdout,stderr:r.stderr.slice(0,120)};
}
let app;
(async()=>{
 app=await _electron.launch({executablePath:path.join(APP,'node_modules/electron/dist/electron'),args:[APP,'--no-sandbox','--disable-gpu'],env:{...process.env,IO_DATA_DIR:DATA,IO_HOME:path.join(DATA,'config'),IO_PORT_BASE:'8916',IO_SMOKE:'1',IO_SCANNER:'server',IO_PROXY_DUMP:path.join(DATA,'dump')},timeout:30000});
 let p;for(let i=0;i<150;i++){p=app.windows().find(w=>w.url().startsWith('http://127.0.0.1:'));if(p)break;await new Promise(r=>setTimeout(r,200));}if(!p)throw new Error('io window did not open: '+app.windows().map(w=>w.url()).join(','));await p.waitForLoadState();p.on('pageerror',e=>mark('page-error',{message:e.message}));
 const screen=async()=>p.locator('.screen.on').getAttribute('id');
 const shot=async name=>p.screenshot({path:path.join(OUT,name+'.png')});
 await p.locator('#gear').click();const kp=app.waitForEvent('window');await p.locator('#st-router').click();const k=await kp;await k.waitForLoadState();
 const key=JSON.parse(fs.readFileSync(path.join(os.homedir(),'.config/idlisseus/openrouter.json'),'utf8')).api_key;
 await k.locator('#key').fill(key);await k.locator('#save').click();await k.waitForFunction(()=>!document.querySelector('#save').disabled);assert.match(await k.locator('#status').innerText(),/Saved key ending/);await k.close();await p.locator('#st-x').click();
 mark('key saved, raw value cleared; main page never received it');
 await p.locator('#p-chatgpt').click();await p.locator('#home-model').selectOption('openrouter');await p.locator('#c-ok').click();await p.locator('#q').fill('Our project is called Mango Garden. Remember that name for later. Say hello briefly.');await p.locator('#q').press('Enter');await p.locator('#s-codex').waitFor({state:'visible'});
 await p.waitForFunction(()=>document.querySelector('#term').innerText.includes('Mango Garden') && document.querySelector('#cx-stats').innerText.match(/[1-9].*request/),{timeout:60000});await p.waitForTimeout(5000);
 let st=await p.evaluate(()=>window.io.codex.status());assert.equal(st.network,true);const online=probe(st);assert.equal(online.http,'200');mark('public conversation curl succeeds',online);await shot('05-public-conversation');
 const oldFolder=st.folder;
 await app.evaluate(({dialog},file)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[file]});},fixture);
 await p.locator('#cx-attach').click();await p.locator('#attach-public').click();await p.locator('#s-sheet').waitFor({state:'visible'});await p.locator('#sheet-ok').click();await p.waitForTimeout(10000);
 st=await p.evaluate(()=>window.io.codex.status());assert.equal(st.network,true);assert.equal(st.privateChat,false);const stillOnline=probe(st);assert.equal(stillOnline.http,'200');mark('No on attachment leaves commands online',stillOnline);
 await p.locator('#cx-attach').click();await p.locator('#attach-privacy').waitFor({state:'visible'});await shot('06-private-question');await p.locator('#attach-private').click();await p.locator('#s-sheet').waitFor({state:'visible',timeout:30000});await p.locator('#sheet-preview').click();await p.locator('#sheet-back').waitFor({state:'visible'});assert.match(await p.locator('#gridwrap').innerText(),/NAME_/);await shot('07-coded-review');await p.locator('#sheet-ok').click();
 await p.locator('#s-codex').waitFor({state:'visible'});await p.waitForTimeout(10000);st=await p.evaluate(()=>window.io.codex.status());assert.equal(st.folder,oldFolder);assert.equal(st.privateChat,true);assert.equal(st.network,false);const offline=probe(st);assert.notEqual(offline.status,0);assert.equal(offline.http,'000');mark('private attachment closes command network',offline);await shot('08-private-conversation');
 await p.waitForFunction(()=>document.querySelector('#term').innerText.includes('synthetic-visits.csv'),{timeout:30000});
 const readTerm=()=>p.locator('#term').innerText();mark('attachment terminal',{text:(await readTerm()).slice(-1800)});
 await p.evaluate(()=>window.io.codex.say('What is our project called? Reply with only its name.'));await p.waitForTimeout(10000);assert.match(await readTerm(),/Mango Garden/);mark('thread remembers project after attachment resume');
 const pidBefore=(await p.evaluate(()=>window.io.codex.status())).pid;assert.ok(pidBefore);assert.ok(!fs.readFileSync(`/proc/${pidBefore}/environ`).includes(Buffer.from(key)));
 await p.locator('#gear').click();const kp2=app.waitForEvent('window');await p.locator('#st-router').click();const k2=await kp2;await k2.waitForLoadState();await k2.locator('#remove').click();await k2.waitForFunction(()=>document.querySelector('#status').textContent.includes('No OpenRouter'));await k2.close();await p.locator('#st-x').click();await p.waitForTimeout(2500);assert.match(await p.locator('#cx-provider-text').innerText(),/key/);mark('key removal visible without relaunch');await shot('09-key-removed');
 await p.evaluate(()=>window.io.codex.say('Reply with key removal check.'));await p.waitForTimeout(4500);const denied=await p.evaluate(()=>window.io.codex.status());assert.equal(denied.service.stats.last.status,401);assert.ok(!denied.service.stats.last.forwarded);mark('missing key request refused locally');await p.evaluate(()=>window.io.codex.input('\x03'));
 await p.locator('#gear').click();const kp3=app.waitForEvent('window');await p.locator('#st-router').click();const k3=await kp3;await k3.waitForLoadState();await k3.locator('#key').fill(key);await k3.locator('#save').click();await k3.waitForFunction(()=>!document.querySelector('#save').disabled);await k3.close();await p.locator('#st-x').click();assert.equal((await p.evaluate(()=>window.io.codex.status())).pid,pidBefore);
 await p.evaluate(()=>window.io.codex.say('Reply with just ready.'));await p.waitForTimeout(10000);assert.match(await readTerm(),/ready/);mark('replacement key works on next turn without app relaunch');
 // Exercise relaunch and handover using the same explicit control implementation.
 const result=await p.evaluate(()=>window.io.codex.switch({provider:'openrouter',fresh:true,wall:'tools'}));assert.equal(result.ok,true);assert.equal(result.handover,true);await p.waitForTimeout(2000);await p.evaluate(()=>window.io.codex.say('Read your previous conversation reference and tell me the project name.'));await p.waitForTimeout(10000);assert.match((await readTerm()).slice(-900),/• Mango Garden/);mark('fresh handover terminal',{text:(await readTerm()).slice(-1600)});await shot('10-handover');
 const allFiles=[];function walk(d){if(!fs.existsSync(d))return;for(const e of fs.readdirSync(d,{withFileTypes:true})){const f=path.join(d,e.name);if(e.isDirectory())walk(f);else allFiles.push(f)}}walk(path.join(DATA,'dump'));allFiles.push(path.join(DATA,'io.log'));assert.ok(allFiles.every(f=>!fs.readFileSync(f).includes(Buffer.from(key))));
 const config=fs.readFileSync(path.join(st.home,'io.config.toml'),'utf8');assert.ok(!config.includes(key));assert.ok(!config.includes('env_key'));mark('no key in profile, log, or dumps',{files:allFiles.length});
 fs.writeFileSync(path.join(OUT,'drive-results.json'),JSON.stringify(steps,null,2));await app.close();
})().catch(async e=>{mark('FAILED',{message:e.message});fs.writeFileSync(path.join(OUT,'drive-results.json'),JSON.stringify(steps,null,2));if(app)await app.close();process.exit(1)});
