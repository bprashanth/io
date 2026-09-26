const fs = require('fs');
const path = require('path');
const LIMIT = 24000;
const NOTE = '[older turns omitted to stay within 24000 chars]';
const WRAPPERS = new Set(['environment_context', 'user_instructions', 'permissions instructions', 'permissions', 'turn_aborted']);
const BOILERPLATE = [
  /^# AGENTS\.md instructions$/i,
  /^<INSTRUCTIONS>$/i,
  /^<\/INSTRUCTIONS>$/i,
  /^# Who you are talking to$/i,
  /^You are running inside io\b/i,
  /^## How to talk$/i,
  /^## Show, do not describe$/i,
  /^## Their data$/i,
  /^## Be careful with their time and their plan$/i,
  /^- Plain words\./i,
  /^- Never ask a technical question back/i,
  /^- Short answers\./i,
  /^- When you have done something/i,
  /^- When asked for a chart/i,
  /^- A chart:/i,
  /^- A dashboard or report:/i,
  /^- `python3` here already has/i,
  /^- Prefer a page in the browser/i,
  /^- The files in the working folder are theirs\./i,
  /^- Names, phone numbers and places may appear as codes/i,
  /^- Do not upload their files anywhere/i,
  /^- Work inside the current working folder\./i,
  /^- This conversation has no sheltered folder\./i,
  /^- Keep steps few\./i,
];
function latestThread(home, cwd) {
  const root = path.resolve(String(home || ''), 'sessions');
  const target = realPath(cwd);
  const matches = [];
  for (const file of walkJsonlFiles(root)) {
    const rows = readJsonl(file);
    for (let i = 0; i < rows.length; i++) {
      if (rows[i]?.type !== 'session_meta') continue;
      const meta = rows[i].payload || {};
      if (realPath(meta.cwd) !== target) continue;
      let end = rows.length;
      for (let j = i + 1; j < rows.length; j++) if (rows[j]?.type === 'session_meta') { end = j; break; }
      matches.push({ file, id: meta.id || meta.session_id || null, time: toMs(rows[i].timestamp || meta.timestamp || i), meta, records: rows.slice(i + 1, end) });
    }
  }
  if (!matches.length) return { id: null, file: null, text: '', lastUser: '' };
  matches.sort((a, b) => b.time - a.time || b.file.localeCompare(a.file));
  const best = matches[0], rendered = renderThread(best.records, best.meta, best.file, target);
  return { id: best.id, file: best.file, text: rendered.text, lastUser: rendered.lastUser };
}
function walkJsonlFiles(root) {
  const out = [], stack = [root];
  while (stack.length) {
    const dir = stack.pop();
    let entries; try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { continue; }
    for (const entry of entries) if (!entry.isSymbolicLink()) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (entry.isFile() && entry.name.toLowerCase().endsWith('.jsonl')) out.push(full);
    }
  }
  return out.sort();
}
function readJsonl(file) {
  try { return fs.readFileSync(file, 'utf8').split(/\r?\n/).flatMap(line => { const trimmed = line.trim(); if (!trimmed) return []; try { return [JSON.parse(trimmed)]; } catch { return []; } }); } catch { return []; }
}
function renderThread(records, meta, file, cwd) {
  const items = [], seen = new Set();
  let lastUser = '';
  for (const record of records) {
    if (record?.type !== 'response_item') continue;
    for (const item of visibleEntries(record.payload)) {
      const body = normalize(item.text); if (!body) continue;
      const sig = `${item.kind}|${item.label}|${body}`; if (seen.has(sig)) continue; seen.add(sig);
      if (item.kind === 'user') { const cleaned = cleanUserText(body); if (!cleaned) continue; lastUser = cleaned; items.push({ ...item, text: cleaned }); }
      else items.push({ ...item, text: body });
    }
  }
  const header = `Session handover\nid: ${meta.id || meta.session_id || '(unknown)'}\nfile: ${file}\ncwd: ${cwd}`;
  const body = fitBody(items.map(renderEntry), header);
  const parts = [header]; if (body.note) parts.push(body.note); if (body.text) parts.push(body.text);
  return { text: parts.join('\n\n').slice(0, LIMIT), lastUser };
}
function visibleEntries(payload) {
  if (!payload || typeof payload !== 'object') return [];
  if (payload.type === 'message') {
    if (payload.role === 'assistant' && payload.channel && payload.channel !== 'final') return [];
    const role = String(payload.role || '').toLowerCase();
    if (role !== 'user' && role !== 'assistant') return [];
    const body = text(payload.content);
    return body ? [{ kind: role, label: role === 'user' ? 'User:' : 'Assistant:', text: body }] : [];
  }
  if (payload.type === 'function_call') return toolEntry('Tool call', payload, payload.arguments ?? payload.input ?? payload.cmd ?? payload.params);
  if (payload.type === 'function_call_output') return toolEntry('Tool output', payload, payload.output ?? payload.result ?? payload.content ?? payload.text ?? payload.value);
  return [];
}
function toolEntry(prefix, payload, value) {
  const name = String(payload.name || payload.function?.name || payload.tool?.name || '').trim(), id = String(payload.call_id || payload.tool_call_id || payload.id || '').trim();
  const label = `${prefix}${name ? ` [${name}]` : ''}${id ? ` (${id})` : ''}:`, body = typeof value === 'string' ? value : json(value);
  return body ? [{ kind: prefix === 'Tool call' ? 'tool_call' : 'tool_output', label, text: body }] : [];
}
function text(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(text).filter(Boolean).join('\n');
  if (typeof value !== 'object') return '';
  const type = String(value.type || value.kind || value.event || '').toLowerCase();
  if (type.includes('reasoning') || type.includes('analysis') || type.includes('system') || type.includes('developer') || type === 'summary_text') return '';
  if (typeof value.text === 'string' && value.text.trim()) return value.text;
  if (typeof value.output === 'string' && value.output.trim()) return value.output;
  if (typeof value.content === 'string' && value.content.trim()) return value.content;
  if (Array.isArray(value.content)) return value.content.map(text).filter(Boolean).join('\n');
  if (Array.isArray(value.parts)) return value.parts.map(text).filter(Boolean).join('\n');
  if (value.message) return text(value.message);
  if (value.body) return text(value.body);
  if (value.result) return text(value.result);
  return '';
}
function cleanUserText(value) {
  if (/^# AGENTS\.md instructions for /i.test(value.trim())) return '';
  const lines = normalize(value).split('\n');
  const out = [];
  let started = false, wrapper = '';
  for (const raw of lines) {
    const line = raw.trimEnd(), trimmed = line.trim();
    if (!started && !trimmed) continue;
    if (!started) {
      const open = trimmed.match(/^<([a-z_][\w\s.-]*)>$/i);
      if (open && WRAPPERS.has(open[1].toLowerCase())) { wrapper = open[1].toLowerCase(); continue; }
      if (wrapper) { const close = trimmed.match(/^<\/([a-z_][\w\s.-]*)>$/i); if (close && close[1].toLowerCase() === wrapper) wrapper = ''; continue; }
      if (BOILERPLATE.some(rx => rx.test(trimmed))) continue;
      started = true;
    }
    if (started) out.push(line);
  }
  return out.join('\n').trim();
}
function normalize(value) { return String(value || '').replace(/\r\n?/g, '\n').replace(/\u0000/g, '').trim(); }
function renderEntry(entry) { const lines = entry.text.split('\n'); return lines.length === 1 ? `${entry.label} ${lines[0]}` : [ `${entry.label} ${lines[0]}`, ...lines.slice(1).map(line => `  ${line}`) ].join('\n'); }
function fitBody(blocks, header) { const available = Math.max(0, LIMIT - header.length - NOTE.length - 4); const kept = []; let used = 0, truncated = false; for (let i = blocks.length - 1; i >= 0; i--) { const block = blocks[i], sep = kept.length ? 2 : 0; if (used + sep + block.length > available) { truncated = true; if (!kept.length && available > 0) kept.unshift(truncate(block, available)); break; } kept.unshift(block); used += sep + block.length; } return { note: truncated ? NOTE : '', text: kept.join('\n\n') }; }
function truncate(block, max) { if (max <= 0) return ''; if (block.length <= max) return block; return max <= 1 ? '…' : `…${block.slice(-(max - 1))}`; }
function realPath(value) { if (typeof value !== 'string') return ''; const raw = value.trim(); if (!raw) return ''; try { return fs.realpathSync.native(raw); } catch {} try { return fs.realpathSync(raw); } catch { return path.resolve(raw); } }
function json(value) { if (value == null) return ''; if (typeof value === 'string') return value; if (typeof value === 'number' || typeof value === 'boolean') return String(value); try { return JSON.stringify(value); } catch { return ''; } }
function toMs(value) { if (typeof value === 'number' && Number.isFinite(value)) return value < 1e12 ? value * 1000 : value; if (typeof value === 'string' && value.trim()) { const num = Number(value); if (Number.isFinite(num)) return num < 1e12 ? num * 1000 : num; const parsed = Date.parse(value); if (Number.isFinite(parsed)) return parsed; } return 0; }
module.exports = { latestThread };
