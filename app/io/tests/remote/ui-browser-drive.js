// Actual Electron + real remote Codex browser-login startup. No account authorization.
const {_electron:electron}=require('../../../../installation/smoke/node_modules/playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../../../..');
const out=path.resolve(process.env.IO_REMOTE_EVIDENCE || 'benchmarks/runs/2026-09-27-browser-oauth');
const config=process.env.IO_REMOTE_CONNECTION;if(!config)throw Error('Dedicated QA connection required');
const c=JSON.parse(fs.readFileSync(config));
async function callback(state){return new Promise((resolve,reject)=>{http.get('http://127.0.0.1:1455/auth/callback?code=synthetic&state='+state,res=>{res.resume();resolve(res.statusCode)}).on('error',reject)});}
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const app=await electron.launch({executablePath:path.join(root,'app/io/node_modules/electron/dist/electron'),args:['--no-sandbox',path.join(root,'app/io')],env:{...process.env,IO_REMOTE_CONNECTION:config,IO_SMOKE:'1'}});
 const errors=[];
 try{
  const page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
  await page.waitForFunction(()=>document.querySelector('#pill-version')?.textContent.includes('0.154.0'));
  await app.evaluate(({shell})=>{globalThis.opened=[];shell.openExternal=async url=>{globalThis.opened.push(url)}});
  await page.click('#sign-in');await page.locator('#login-link').waitFor({state:'visible',timeout:25000});
  const first=await app.evaluate(()=>globalThis.opened[0]);const parsed=new URL(first);
  assert.equal(parsed.origin,'https://auth.openai.com');assert.equal(parsed.pathname,'/oauth/authorize');
  assert.equal(parsed.searchParams.get('redirect_uri'),'http://localhost:1455/auth/callback');
  assert.equal(await page.locator('#login-code').isVisible(),false);
  assert.ok(!(await page.locator('body').innerText()).includes(parsed.searchParams.get('state')));
  assert.equal(await callback('wrong-state'),403);
  await page.click('#login-link');assert.equal(await app.evaluate(()=>globalThis.opened.length),2);
  await page.screenshot({path:path.join(out,'browser-sign-in.png')});
  await page.click('#interrupt');
  await page.waitForFunction(()=>document.querySelector('#sign-in')?.disabled===false);
  await assert.rejects(callback('wrong-state'),/ECONNREFUSED/);
  await page.click('#sign-in');await page.locator('#login-link').waitFor({state:'visible',timeout:25000});
  const second=await app.evaluate(()=>globalThis.opened[2]);
  assert.notEqual(new URL(second).searchParams.get('state'),parsed.searchParams.get('state'));
  assert.equal(await callback(parsed.searchParams.get('state')),403);
  await page.click('#interrupt');await page.waitForFunction(()=>document.querySelector('#sign-in')?.disabled===false);
  await page.click('#login-device');
  await page.waitForFunction(()=>document.querySelector('#login-code')?.textContent.trim().length>=8,null,{timeout:25000});
  await page.screenshot({path:path.join(out,'device-fallback-redacted.png'),mask:[page.locator('#login-code'),page.locator('#login-log')]});
  await page.click('#interrupt');await page.waitForFunction(()=>document.querySelector('#sign-in')?.disabled===false);
  assert.deepEqual(errors,[]);
  const result={realElectron:true,realCodexBrowserLogin:true,deviceFallback:true,callbackWrongStateRejected:true,cancelClosesPort:true,retryNewState:true,oldStateRejected:true,urlHidden:true,liveAuthorization:false,errors};
  fs.writeFileSync(path.join(out,'ui-browser-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await app.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1});
