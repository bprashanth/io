// Credential-free transport contract. A fixture is not ChatGPT or sandbox evidence.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {EventEmitter} = require('node:events');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {install, validateConnection} = require('../../remote/client');
const token='a'.repeat(64);
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<150;i++){if(fn())return;await delay(20);}throw Error('condition timed out');}

test('capability transport only permits TLS or literal loopback',()=>{
 for(const url of ['http://example.com','http://localhost','http://127.0.0.1.evil.test','file:///tmp/x','https://user:pass@example.com','https://example.com/#secret'])
  assert.ok(validateConnection({url,token}).error,url);
 for(const url of ['http://127.0.0.1:1234','http://[::1]:1234','https://private.example.test'])
  assert.ok(!validateConnection({url,token}).error,url);
 assert.ok(validateConnection({url:'https://example.com',token:'weak'}).error);
});

test('stream replay/gap, ordered input, transfers, redirect refusal and end', async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'io-remote-client-'));
 const source=path.join(dir,'input.csv'),dest=path.join(dir,'download.csv');fs.writeFileSync(source,'n\n3\n');
 const received=[],calls=[],keys=[],sent=[],handlers=new Map();let stream,resumeAfter,connections=0,redirect=false,downloadName,instance='first';
 const server=http.createServer(async(req,res)=>{
  try{
   assert.equal(req.headers.authorization,`Bearer ${token}`);
   calls.push(req.url);
   let chunks=[];for await(const c of req)chunks.push(c);const body=Buffer.concat(chunks);
   if(req.url.startsWith('/events')){
    connections++;resumeAfter=new URL(req.url,'http://x').searchParams.get('after');
    res.writeHead(200,{'Content-Type':'text/event-stream'});stream=res;
    res.write(': keepalive\n\n');
    res.write('id: 999\n: id-only heartbeat\n\n');
    if(connections===1){res.write('id: 1\ndata: {"kind":"data","data":"hello"}\n\n');}
    else{res.write('data: {"kind":"gap","data":"older output unavailable"}\n\n');
     res.write('id: 1\ndata: {"kind":"data","data":"duplicate"}\n\n');
     const bytes=Buffer.from('id: 2\ndata: {"kind":"data","data":"नमस्ते"}\n\n');
     for(const byte of bytes)res.write(Buffer.from([byte]));}
    return;
   }
   if(req.url==='/status')return res.end(JSON.stringify({instance,loggedIn:true,running:true,version:'fixture',policy:'offline'}));
   if(req.url==='/input'){keys.push(JSON.parse(body).data);if(keys.length===1)await delay(40);return res.end('{}');}
   if(req.url.startsWith('/files?')){assert.equal(body.toString(),'n\n3\n');received.push(body);return res.end('{"name":"input.csv"}');}
   if(req.url.startsWith('/file?')){downloadName=req.url;return res.end('total\n3\n');}
   if(req.url==='/files'&&redirect){res.writeHead(302,{Location:'http://127.0.0.1:1/stolen'});return res.end();}
   res.end('{"ok":true}');
  }catch(e){res.statusCode=500;res.end(JSON.stringify({error:e.message}));}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const app=new EventEmitter();app.isPackaged=false;
 class Window extends EventEmitter{
  constructor(){super();this.webContents=new EventEmitter();this.webContents.send=(c,p)=>sent.push([c,p]);this.webContents.setWindowOpenHandler=()=>{};}
  isDestroyed(){return false;}setMenuBarVisibility(){}loadFile(){return Promise.resolve();}show(){}
 }
 const ipcMain={handle:(n,f)=>handlers.set(n,f),on:(n,f)=>handlers.set(n,f)};
 const dialog={showOpenDialog:async()=>({filePaths:[source]}),showSaveDialog:async()=>({filePath:dest})};
 const external=[];
 try{
  await install({app,BrowserWindow:Window,ipcMain,dialog,shell:{openExternal:async x=>external.push(x)}},{url:`http://127.0.0.1:${server.address().port}`,token});
  await until(()=>sent.some(([c,p])=>c==='remote-event'&&p.data==='hello'));
  stream.end();
  await until(()=>sent.some(([c,p])=>c==='remote-event'&&p.data==='नमस्ते'));
  assert.equal(resumeAfter,'1');assert.equal(connections,2);
  assert.equal(sent.filter(([c,p])=>c==='remote-event'&&p.data==='duplicate').length,0);
  assert.ok(sent.some(([c,p])=>c==='remote-event'&&p.kind==='gap'));
  handlers.get('remote-input')(null,'a');handlers.get('remote-input')(null,'b');handlers.get('remote-input')(null,'c');
  await until(()=>keys.length===3);assert.deepEqual(keys,['a','b','c']);
  assert.equal((await handlers.get('remote-attach')()).ok,true);
  assert.equal(received.length,1);
  assert.ok(!sent.some(([c,p])=>c==='remote-error'&&/malformed/i.test(p)), 'valid heartbeats must not be parsed as JSON');
  stream.write('id: 3\ndata: {not json}\n\n');
  await until(()=>sent.some(([c,p])=>c==='remote-error'&&/malformed/i.test(p)));
  assert.equal((await handlers.get('remote-logout')()).ok,true);
  assert.ok(calls.includes('/logout'));
  assert.equal(fs.readFileSync(source,'utf8'),'n\n3\n');
  assert.equal((await handlers.get('remote-download')(null,'nested/result.csv')).ok,true);
  assert.match(downloadName,/nested%2Fresult.csv/);assert.equal(fs.readFileSync(dest,'utf8'),'total\n3\n');
  assert.ok((await handlers.get('remote-open-external')(null,'https://evil.test')).error);
  assert.equal((await handlers.get('remote-open-external')(null,'https://auth.openai.com/codex/device')).ok,true);
  assert.deepEqual(external,['https://auth.openai.com/codex/device']);
  instance='restarted';
  await handlers.get('remote-status')();
  await until(()=>sent.some(([c,p])=>c==='remote-event'&&p.kind==='reset'));
  await until(()=>connections===3);
  assert.equal(resumeAfter,'0');
  redirect=true;assert.match((await handlers.get('remote-files')()).error,/redirect/);
  assert.equal((await handlers.get('remote-end')()).ok,true);
  assert.equal((await handlers.get('remote-status')()).ended,true);
  assert.ok(!JSON.stringify(sent).includes(token),'capability must not enter renderer');
 }finally{app.emit('before-quit');server.closeAllConnections();await new Promise(r=>server.close(r));fs.rmSync(dir,{recursive:true,force:true});}
});
