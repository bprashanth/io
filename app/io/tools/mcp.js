// io's toolbox, as Codex sees it: a local MCP server over stdio (newline-delimited
// JSON-RPC). Codex launches this as its own child, outside the wall, with only the
// environment io wrote into the profile (IO_TOOLS_PORT, IO_TOOLS_TOKEN). Every tool here
// is a thin call to io's main process, which does the work and decides what may leave.
//
// One tool so far: render_page. io re-applies real-to-code over the page's text, renders
// that copy in a window with no network, and returns the picture. The real page is never
// screenshotted; a PNG chart is refused (its labels are pixels the vault cannot code).
//
// IO_TOOLS_FAKE=1 answers with a tiny built-in PNG instead of calling io, so the channel
// (config, approval mode, image content through the proxy) can be tested with `codex exec`
// on a machine that is not running the app.
'use strict';
const http = require('http');
const readline = require('readline');

const PORT = process.env.IO_TOOLS_PORT;
const TOKEN = process.env.IO_TOOLS_TOKEN;
const FAKE = process.env.IO_TOOLS_FAKE === '1';
// 1x1 PNG; the fake answer for the exec-level test
const FAKE_PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

const TOOLS = [{
  name: 'render_page',
  title: 'Show me a picture of a page I wrote',
  description: 'Renders an HTML page from the working folder and returns a picture of it, so you can check '
    + 'that a page or report you wrote looks right. The picture is made from a copy in which names, '
    + 'places, phone numbers and the like are replaced by codes such as NAME_001; that is expected and not a problem to fix. '
    + 'Only .html files in the working folder can be rendered; a PNG chart cannot.',
  inputSchema: { type: 'object', properties: { file: { type: 'string', description: 'file name of the page, as saved in the working folder' } }, required: ['file'] },
  annotations: { title: 'Show me a picture of a page I wrote', readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
}];

function callIo(route, body) {
  return new Promise((resolve, reject) => {
    if (FAKE) return resolve({ ok: true, png: FAKE_PNG, width: 1, height: 1, file: body.file, coded: 0 });
    if (!PORT || !TOKEN) return reject(new Error('io is not running, so the toolbox is closed'));
    const data = JSON.stringify(body || {});
    const req = http.request({ host: '127.0.0.1', port: Number(PORT), path: route, method: 'POST', timeout: 110000,
      headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data), 'x-io-token': TOKEN } }, res => {
      let b = ''; res.on('data', d => b += d); res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { reject(new Error('io answered badly')); } });
    });
    req.on('timeout', () => { req.destroy(new Error('io took too long to render')); });
    req.on('error', reject);
    req.end(data);
  });
}

async function callTool(name, args) {
  if (name !== 'render_page') return { content: [{ type: 'text', text: `no such tool: ${name}` }], isError: true };
  const file = String((args && args.file) || '').trim();
  if (!file) return { content: [{ type: 'text', text: 'say which file to render' }], isError: true };
  let r;
  try { r = await callIo('/render', { file }); } catch (e) { return { content: [{ type: 'text', text: `could not render: ${e.message}` }], isError: true }; }
  if (!r || !r.ok) return { content: [{ type: 'text', text: `could not render: ${(r && r.error) || 'unknown error'}` }], isError: true };
  return { content: [
    { type: 'text', text: `Picture of ${r.file} (${r.width}x${r.height}). Names, places and phone numbers show as codes in it; that is expected.` },
    { type: 'image', data: r.png, mimeType: 'image/png' },
  ] };
}

const out = msg => process.stdout.write(JSON.stringify(msg) + '\n');
async function handle(msg) {
  const { id, method, params } = msg;
  if (id === undefined || id === null) return;      // a notification: nothing to answer
  const reply = result => out({ jsonrpc: '2.0', id, result });
  const fail = (code, message) => out({ jsonrpc: '2.0', id, error: { code, message } });
  try {
    if (method === 'initialize') {
      reply({ protocolVersion: (params && params.protocolVersion) || '2025-06-18', capabilities: { tools: {} }, serverInfo: { name: 'io', version: '1' } });
    } else if (method === 'ping') reply({});
    else if (method === 'tools/list') reply({ tools: TOOLS });
    else if (method === 'tools/call') reply(await callTool(params && params.name, params && params.arguments));
    else fail(-32601, `method not found: ${method}`);
  } catch (e) { fail(-32603, e.message); }
}
// requests are answered one at a time, in the order they came (a render takes seconds)
let chain = Promise.resolve();
const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on('line', line => {
  line = line.trim();
  if (!line) return;
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  chain = chain.then(() => handle(msg));
});
rl.on('close', () => { chain.then(() => process.exit(0)); });
