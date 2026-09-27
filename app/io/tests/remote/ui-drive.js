const {_electron:electron}=require('../../../../installation/smoke/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{execFileSync}=require('child_process');
const root=path.resolve(__dirname,'../../../..'), out=path.resolve(process.env.IO_REMOTE_EVIDENCE || path.join(root,'benchmarks/runs/2026-09-27-remote-codex'));
fs.mkdirSync(out,{recursive:true});
const connectionFile=process.env.IO_REMOTE_CONNECTION;
if(!connectionFile) throw Error('Set IO_REMOTE_CONNECTION to a dedicated test session');
const c=JSON.parse(fs.readFileSync(connectionFile));
const temp=fs.mkdtempSync(path.join(require('os').tmpdir(),'io-remote-ui-'));
const inputName='synthetic-'+crypto.randomBytes(5).toString('hex')+'.csv';
const csv=path.join(temp,inputName), download=path.join(temp,'result.csv');
fs.writeFileSync(csv,'district,participants\nNorth,12\nSouth,8\n');
const before=fs.readFileSync(csv);
(async()=>{
 const app=await electron.launch({executablePath:path.join(root,'app/io/node_modules/electron/dist/electron'),args:['--no-sandbox',path.join(root,'app/io')],env:{...process.env,IO_REMOTE_CONNECTION:connectionFile,IO_SMOKE:'1'}});
 const errors=[];try{
 const page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
 await page.waitForFunction(()=>document.querySelector('#pill-version')?.textContent.includes('0.154.0'));
 await app.evaluate(({dialog,shell},paths)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[paths.csv]});dialog.showSaveDialog=async()=>({canceled:false,filePath:paths.download});shell.openExternal=async()=>{};},{csv,download});
 await page.click('#attach'); await page.screenshot({path:path.join(out,'upload-confirmation.png')}); await page.click('#attach-go');
 await page.waitForFunction(()=>document.querySelector('#notice')?.textContent.includes('Uploaded'));
 // Real pinned Codex sandbox, operator-issued deterministic command, NOT a model response.
 execFileSync('docker',['exec',c.container,'codex','sandbox','-p','io','-P','io','-C','/workspace','--','python3','-c',"import csv; rows=list(csv.DictReader(open('"+inputName+"'))); open('summary.csv','w').write('total\\n'+str(sum(int(r['participants']) for r in rows))+'\\n')"]);
 await page.click('#results');await page.getByText('summary.csv',{exact:true}).waitFor();
 await page.screenshot({path:path.join(out,'remote-results.png')});
 await page.locator('.fileitem').filter({hasText:'summary.csv'}).getByRole('button',{name:/save|download/i}).click();
 if(!fs.readFileSync(csv).equals(before))throw Error('Local original modified');
 if(fs.readFileSync(download,'utf8')!=='total\n20\n')throw Error('Bad downloaded result');
 await page.click('#results-close'); await page.click('#login-device');
 await page.waitForFunction(()=>document.querySelector('#login-code')?.textContent.trim().length>=8,null,{timeout:20000});
 await page.screenshot({path:path.join(out,'device-login-redacted.png'),mask:[page.locator('#login-code'),page.locator('#login-log')]});
 await page.click('#interrupt');
 await page.waitForFunction(()=>document.querySelector('#pill-run')?.textContent==='idle',null,{timeout:20000});
 console.log(JSON.stringify({ui:true,upload:true,realCodexSandboxPython:true,download:true,originalUnchanged:true,deviceFlow:true,interrupt:true,errors}));
 fs.writeFileSync(path.join(out,'ui-results.json'),JSON.stringify({ui:true,upload:true,realCodexSandboxPython:true,download:true,originalUnchanged:true,deviceFlow:true,interrupt:true,liveModel:false,errors},null,2));
 if(errors.length)throw Error(errors.join(';'));
 }finally{await app.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
