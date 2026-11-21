// Minimal equivalent of upstream packages/web-host/src/static-server.ts (AionUi e108b6b):
// serve the renderer SPA and reverse-proxy /api/*, /login, /logout and WebSocket upgrades
// (/ws, /api/stt/stream) to aioncore. No auth logic here: aioncore (identity-mode webui) owns it.
// Usage: node webhost.mjs <rendererDir> <backendPort> <listenPort>
import http from 'node:http'; import net from 'node:net'; import fs from 'node:fs'; import path from 'node:path';
const [dir, backendPort, port] = [process.argv[2], +process.argv[3], +process.argv[4]];
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2', '.wasm': 'application/wasm', '.ico': 'image/x-icon' };
const isBackend = u => u.startsWith('/api/') || u.startsWith('/api?') || u === '/login' || u === '/logout';
http.createServer((req, res) => {
  if (isBackend(req.url)) {
    const up = http.request({ host: '127.0.0.1', port: backendPort, method: req.method, path: req.url, headers: req.headers }, r => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
    up.on('error', () => { res.writeHead(502); res.end(); }); req.pipe(up); return;
  }
  let p = path.join(dir, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(dir) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) p = path.join(dir, 'index.html');
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
}).on('upgrade', (req, sock, head) => {
  const up = net.connect(backendPort, '127.0.0.1', () => {
    up.write(`${req.method} ${req.url} HTTP/1.1\r\n` + Object.entries(req.headers).map(([k, v]) => `${k}: ${v}`).join('\r\n') + '\r\n\r\n'); up.write(head); sock.pipe(up).pipe(sock);
  }); up.on('error', () => sock.destroy()); sock.on('error', () => up.destroy());
}).listen(port, '0.0.0.0', () => console.log('webhost on', port, '->', backendPort));
