// Source-shaped synthetic ChatGPT quota fixture, followed by live OpenRouter retry.
const {_electron}=require('../../../installation/smoke/node_modules/playwright');
const fs=require('fs'),os=require('os'),path=require('path'),http=require('http'),assert=require('assert');
const ROOT=path.resolve(__dirname,'../../..'),APP=path.join(ROOT,'app/io');
const DATA=path.join(os.homedir(),'.local/share/io-0926-quota');fs.mkdirSync(path.join(DATA,'codex/home'),{recursive:true});
const b64=x=>Buffer.from(JSON.stringify(x)).toString('base64url');const now=Math.floor(Date.now()/1000);
const claims={iss:'https://auth.openai.com',sub:'fixture',exp:now+3600,iat:now,email:'fixture@example.invalid','https://api.openai.com/auth':{chatgpt_account_id:'acct_fixture',chatgpt_user_id:'user_fixture',chatgpt_plan_type:'plus'}};
const jwt=`${b64({alg:'none',typ:'JWT'})}.${b64(claims)}.fixture-signature`;
fs.writeFileSync(path.join(DATA,'codex/home/auth.json'),JSON.stringify({auth_mode:'chatgpt',OPENAI_API_KEY:null,tokens:{id_token:jwt,access_token:jwt,refresh_token:'fixture',account_id:'acct_fixture'},last_refresh:new Date().toISOString()}),{mode:0o600});
const key=JSON.parse(fs.readFileSync(path.join(os.homedir(),'.config/idlisseus/openrouter.json'),'utf8')).api_key;
fs.writeFileSync(path.join(DATA,'openrouter-key.json'),JSON.stringify({api_key:key}),{mode:0o600});
let exhausted=true;const routes=[];const reset=now+3600;
const server=http.createServer((req,res)=>{routes.push({method:req.method,path:req.url});req.resume();res.setHeader('Content-Type','application/json');
 if(req.url.startsWith('/wham/usage'))return res.end(JSON.stringify({plan_type:'plus',rate_limit:{allowed:!exhausted,limit_reached:exhausted,primary_window:{used_percent:exhausted?100:20,limit_window_seconds:18000,reset_after_seconds:3600,reset_at:reset},secondary_window:null},credits:null}));
 if(req.method==='POST'&&req.url.includes('/responses')){res.statusCode=429;return res.end(JSON.stringify({error:{type:'usage_limit_reached',plan_type:'plus',resets_at:reset}}));}
 if(req.url.includes('/models'))return res.end(JSON.stringify({models:[]}));res.end('{}');});
let app;
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;
 app=await _electron.launch({executablePath:path.join(APP,'node_modules/electron/dist/electron'),args:[APP,'--no-sandbox','--disable-gpu'],env:{...process.env,IO_DATA_DIR:DATA,IO_HOME:path.join(DATA,'config'),IO_PORT_BASE:'8956',IO_SCANNER:'server',IO_CODEX_MODEL:'gpt-5.2',IO_PROXY_DEV_UPSTREAM:`/backend-api=http://127.0.0.1:${port}`,IO_PROXY_DUMP:path.join(DATA,'dump')}});
 let p;for(let i=0;i<100;i++){p=app.windows().find(w=>w.url().startsWith('http:'));if(p)break;await new Promise(r=>setTimeout(r,200));}assert.ok(p);
 await p.locator('#p-chatgpt').click();await p.locator('#c-ok').click();await p.waitForFunction(()=>document.querySelector('#opening-quota').textContent.includes('used up'));
 assert.equal(await p.locator('#home-model').inputValue(),'openrouter');let st=await p.evaluate(()=>window.io.codex.status());assert.equal(st.running,false);assert.equal(st.provider,'chatgpt');
 console.log('opening quota preselects fallback but starts no model',st.service.quota);await p.screenshot({path:path.join(__dirname,'12-opening-quota.png')});
 // Explicitly choose ChatGPT to test its refusal, despite the preflight warning.
 await p.locator('#home-model').selectOption('chatgpt');exhausted=false;
 await new Promise((resolve,reject)=>http.get(`http://127.0.0.1:${st.service.port}/backend-api/wham/usage`,r=>{r.resume();r.on('end',resolve)}).on('error',reject));
 await p.locator('#q').fill('Reply with exactly: quota fallback worked.');await p.locator('#q').press('Enter');for(let i=0;i<120&&!routes.some(r=>r.method==='POST'&&r.path.includes('/responses'));i++)await p.waitForTimeout(250);
 assert.ok(routes.some(r=>r.method==='POST'&&r.path.includes('/responses')),'ChatGPT request must really reach quota-refusal fixture');
 await p.locator('#cx-provider-notice').waitFor({state:'visible',timeout:40000});
 console.log('quota banner',await p.locator('#cx-provider-text').innerText());await p.screenshot({path:path.join(__dirname,'13-live-quota-fixture.png')});
 await p.locator('#cx-provider-action').click();await p.waitForTimeout(15000);st=await p.evaluate(()=>window.io.codex.status());assert.equal(st.provider,'openrouter');
 const text=await p.locator('#term').innerText();console.log(text.slice(-1300));assert.match(text,/• quota fallback worked\./i);await p.screenshot({path:path.join(__dirname,'14-quota-fallback.png')});
 const result={preflight:true,refusal:true,retry:true,routes};fs.writeFileSync(path.join(__dirname,'quota-results.json'),JSON.stringify(result,null,2));await app.close();server.close();
})().catch(async e=>{console.error(e.message);if(app)await app.close();server.close();process.exit(1)});
