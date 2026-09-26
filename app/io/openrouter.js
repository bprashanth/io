// Credentials stay in the main process and the service's private stdin channel.
const fs = require('fs');
const path = require('path');
const https = require('https');

function checkKey(key) {
  return new Promise(resolve => {
    const req = https.get('https://openrouter.ai/api/v1/key', {
      headers: { Authorization: `Bearer ${key}` }, timeout: 15000,
    }, res => {
      let body = '';
      res.on('data', c => { if (body.length < 100000) body += c; });
      res.on('end', () => {
        if (res.statusCode === 401 || res.statusCode === 403) return resolve({error: 'This key was not accepted. Check it and try again.'});
        if (res.statusCode !== 200) return resolve({error: 'OpenRouter could not check the key just now. Please try again.'});
        try {
          const data = JSON.parse(body).data;
          if (!data || typeof data !== 'object') throw new Error();
          resolve({ok: true, remaining: typeof data.limit_remaining === 'number' ? data.limit_remaining : null});
        } catch { resolve({error: 'OpenRouter returned an unreadable key check. Please try again.'}); }
      });
    });
    req.on('timeout', () => req.destroy());
    req.on('error', () => resolve({error: 'Could not reach OpenRouter to check this key. Please try again.'}));
  });
}
class KeyStore {
  constructor(dir, portable = false) {
    this.file = path.join(dir, 'openrouter-key.json');
    this.portable = portable;
    this.key = ''; this.remaining = null;
    if (!portable) {
      try { this.key = JSON.parse(fs.readFileSync(this.file, 'utf8')).api_key || ''; fs.chmodSync(this.file, 0o600); } catch {}
    }
  }
  status() { return {configured: !!this.key, suffix: this.key ? this.key.slice(-4) : '', remaining: this.remaining, persistent: !this.portable}; }
  async replace(value) {
    const key = String(value || '').trim();
    if (!key || key.length > 512 || /[\r\n\s]/.test(key)) return {error: 'Paste an OpenRouter key.'};
    const result = await checkKey(key);
    if (!result.ok) return result;
    if (!this.portable) {
      fs.mkdirSync(path.dirname(this.file), {recursive: true});
      const tmp = this.file + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify({api_key: key}), {mode: 0o600});
      fs.chmodSync(tmp, 0o600); fs.renameSync(tmp, this.file);
    }
    this.key = key; this.remaining = result.remaining;
    return {ok: true, ...this.status()};
  }
  remove() {
    if (!this.portable) fs.rmSync(this.file, {force: true});
    this.key = ''; this.remaining = null;
    return {ok: true, ...this.status()};
  }
}
module.exports = {KeyStore, checkKey};
