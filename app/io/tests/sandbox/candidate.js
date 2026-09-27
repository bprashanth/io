// Experiment-only bundle. Never replaces io's shipped pins or codex-bin target.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {execFileSync}=require('child_process');
const pins=require('./candidate-pins.json');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function candidate(version){
 const pin=pins[version];if(!pin || process.platform!=='win32' || process.arch!=='x64')throw Error('Unknown candidate or non-Windows-x64 host');
 const dir=path.resolve(__dirname,'../../codex-bin/candidates',version,'win32-x64');
 return {pin,dir,path:path.join(dir,'bin/codex.exe'),archive:path.join(dir,pin.asset)};
}
async function fetchCandidate(version){
 const c=candidate(version);fs.mkdirSync(c.dir,{recursive:true});
 const url=`https://github.com/openai/codex/releases/download/${c.pin.tag}/${c.pin.asset}`;
 const response=await fetch(url);if(!response.ok)throw Error(`Package HTTP ${response.status}`);
 fs.writeFileSync(c.archive,Buffer.from(await response.arrayBuffer()));
 if(hash(c.archive)!==c.pin.sha256)throw Error('Candidate archive hash mismatch');
 execFileSync(path.join(process.env.SystemRoot,'System32/tar.exe'),['-xzf',c.pin.asset],{cwd:c.dir,stdio:'inherit'});
 for(const name of ['codex.exe','codex-code-mode-host.exe'])if(!fs.existsSync(path.join(c.dir,'bin',name)))throw Error('Incomplete candidate bundle');
 fs.writeFileSync(path.join(c.dir,'VERSION.json'),JSON.stringify({...c.pin,binary_sha256:hash(c.path)},null,2));
 console.log(`Fetched experiment candidate ${version}; product pin unchanged`);
}
if(require.main===module)fetchCandidate(process.argv[2]).catch(e=>{console.error(e.message);process.exitCode=1});
module.exports={candidate};
