// Use Codex's supported account endpoint so io never reads its OAuth token.
const {spawn} = require('child_process');
const codex = require('./codex');
function readQuota(bin, home, proxyPort) {
  return new Promise(resolve => {
    const child = spawn(bin, ['app-server', '-c', `chatgpt_base_url="http://127.0.0.1:${proxyPort}/backend-api/"`], {env: codex.baseEnv(home), stdio: ['pipe','pipe','ignore']});
    let buffer = '', finished = false;
    const finish = result => { if (finished) return; finished = true; clearTimeout(timer); child.kill(); resolve(result); };
    const timer = setTimeout(() => finish(null), 12000);
    const send = obj => { if (child.stdin.writable) child.stdin.write(JSON.stringify(obj) + '\n'); };
    child.stdin.on('error', () => finish(null));
    child.on('error', () => finish(null)); child.on('exit', () => finish(null));
    child.stdout.on('data', chunk => {
      buffer += chunk;
      let i;
      while ((i = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0,i); buffer = buffer.slice(i+1);
        let msg; try { msg = JSON.parse(line); } catch { continue; }
        if (msg.id === 1) {
          if (msg.error) return finish(null);
          send({method:'initialized', params:{}});
          send({method:'account/rateLimits/read', id:2});
        }
        if (msg.id === 2) return finish(msg.result || null);
      }
    });
    send({method:'initialize',id:1,params:{clientInfo:{name:'io',version:'0.2.0'}}});
  });
}
module.exports = {readQuota};
