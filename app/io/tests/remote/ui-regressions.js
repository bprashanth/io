// Actual Electron controls against a scripted HTTP worker: no model/account is used.
const {_electron:electron}=require('../../../../installation/smoke/node_modules/playwright');
const fs=require('fs'),path=require('path'),os=require('os'),http=require('http'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../../../..');
const out=path.resolve(process.env.IO_REMOTE_EVIDENCE || 'benchmarks/runs/2026-09-27-remote-laptop-fixes');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'io-ui-regression-'));
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB9kAAAAASUVORK5CYII=','base64');
const filename='Synthetic photo ü.png', file=path.join(tmp,filename);fs.writeFileSync(file,png);
const cap='t'.repeat(64),config=path.join(tmp,'fixture.remote-connection.json');
const inputs=[],requests=[],errors=[],streams=new Set();let uploaded=false,loggedIn=true,running=true,app;
const server=http.createServer(async(req,res)=>{
 try{
  assert.equal(req.headers.authorization,'Bearer '+cap);requests.push(req.url);
  const parts=[];for await(const p of req)parts.push(p);const raw=Buffer.concat(parts);
  if(req.url.startsWith('/events')){
   res.writeHead(200,{'Content-Type':'text/event-stream'});streams.add(res);
   res.write('data: '+JSON.stringify({kind:'data',data:'\x1b[?2004hUI FIXTURE — no model or real account\r\n> '})+'\n\n');
   const timer=setInterval(()=>res.write(': keepalive\n\n'),100);
   res.on('close',()=>{clearInterval(timer);streams.delete(res)});return;
  }
  if(req.url==='/status')return res.end(JSON.stringify({loggedIn,running,mode:running?'data':null,instance:'fixture',policy:'offline',version:'codex-cli 0.154.0 (fixture)'}));
  if(req.url==='/input'){inputs.push(JSON.parse(raw).data);return res.end('{"ok":true}');}
  if(req.url.startsWith('/files?')){
   assert.equal(new URL(req.url,'http://fixture').searchParams.get('name'),filename);assert.deepEqual(raw,png);
   const reused=uploaded;uploaded=true;return res.end(JSON.stringify({name:filename,size:png.length,reused}));
  }
  if(req.url==='/logout'){loggedIn=running=false;return res.end('{"ok":true}');}
  return res.end('{"ok":true}');
 }catch(e){errors.push(e.message);res.statusCode=500;res.end('{"error":"fixture failed"}');}
});
async function launch(){return electron.launch({executablePath:path.join(root,'app/io/node_modules/electron/dist/electron'),args:['--no-sandbox',path.join(root,'app/io')],env:{...process.env,IO_REMOTE_CONNECTION:config,IO_SMOKE:'1'}});}
(async()=>{
 fs.mkdirSync(out,{recursive:true});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 fs.writeFileSync(config,JSON.stringify({url:`http://127.0.0.1:${server.address().port}`,token:cap}),{mode:0o600});
 try{
  app=await launch();const page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
  await page.locator('#sign-out').waitFor({state:'visible'});
  await app.evaluate(({dialog},file)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[file]});},file);
  assert.equal(await page.locator('#login-log').isVisible(),false);
  await page.click('#attach');await page.click('#attach-go');
  await page.waitForFunction(()=>document.querySelector('#notice')?.textContent.includes('Press Enter'));
  await page.waitForTimeout(400); // Multiple heartbeat blocks while the draft is staged.
  assert.equal(inputs.length,1);assert.ok(inputs[0].startsWith('\x1b[200~'));assert.ok(inputs[0].endsWith('\x1b[201~'));
  assert.ok(inputs[0].includes(JSON.stringify('/workspace/'+filename)));assert.ok(inputs[0].includes('image viewing tool'));
  assert.ok(!/[\r\n]/.test(inputs[0]),'must not auto-submit');
  assert.ok(!/malformed/i.test(await page.locator('#notice').innerText()));
  await page.click('#attach');await page.click('#attach-go');
  await page.waitForFunction(()=>document.querySelector('#attach-status')?.textContent.includes('reused'));
  assert.deepEqual(fs.readFileSync(file),png);
  await page.screenshot({path:path.join(out,'signed-in-attachment-fixture.png')});
  await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(820,640));
  await page.waitForTimeout(200);
  const geometry=await page.evaluate(()=>({overflow:document.body.scrollWidth>innerWidth,bottom:document.querySelector('#bottom').getBoundingClientRect().bottom,height:innerHeight,term:document.querySelector('#term').getBoundingClientRect().height}));
  console.log('small-window geometry',JSON.stringify(geometry));
  await page.screenshot({path:path.join(out,'small-window.png')});
  assert.equal(geometry.overflow,false);assert.ok(geometry.bottom<=geometry.height+1);assert.ok(geometry.term>200);
  await page.click('#sign-out');assert.match(await page.locator('#logout-modal').innerText(),/saved chat is cleared/i);
  await page.click('#logout-go');await page.waitForFunction(()=>document.querySelector('#sign-in')?.disabled===false);
  assert.ok(requests.includes('/logout'));assert.ok(!requests.includes('/end'));
  await page.click('#end');assert.match(await page.locator('#end-modal').innerText(),/endpoint/);
  await page.screenshot({path:path.join(out,'delete-workspace-warning.png')});await page.click('#end-cancel');
  await app.close();app=null;
  server.closeAllConnections();await new Promise(r=>server.close(r));
  app=await launch();const offline=await app.firstWindow();offline.on('pageerror',e=>errors.push(e.message));
  await offline.waitForFunction(()=>document.querySelector('#notice')?.textContent.includes('Remote workspace is unreachable'));
  await offline.screenshot({path:path.join(out,'unreachable-workspace.png')});
  assert.ok(!/ECONNRESET|ECONNREFUSED/.test(await offline.locator('#notice').innerText()));
  assert.deepEqual(errors,[]);
  const result={fixture:true,realElectron:true,heartbeatNoWarning:true,compactLogin:true,imageUploadAndRepeat:true,attachmentDraftNoSubmit:true,signoutKeepsEndpoint:true,deleteWarning:true,readableDisconnect:true,geometry,errors};
  fs.writeFileSync(path.join(out,'ui-regressions.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{if(app)await app.close();for(const s of streams)s.destroy();server.closeAllConnections();server.close();fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
