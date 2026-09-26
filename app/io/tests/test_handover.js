// Handover tests: exact cwd matching, wrapper parsing, and visible-only output.
// Run: node tests/test_handover.js

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { latestThread } = require('../handover');

let passed = 0;
const test = (name, fn) => {
  fn();
  passed += 1;
  console.log('ok -', name);
};

function writeJsonl(file, rows) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, rows.map(row => JSON.stringify(row)).join('\n') + '\n');
}

function meta(id, cwd, timestamp) {
  return {
    timestamp,
    type: 'session_meta',
    payload: {
      id,
      session_id: id,
      cwd,
      timestamp,
      base_instructions: { text: 'base instructions' },
    },
  };
}

function message(role, content, timestamp) {
  return {
    timestamp,
    type: 'response_item',
    payload: { type: 'message', role, content },
  };
}

test('latestThread reads actual Codex wrappers and ignores hidden noise', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'io-handover-'));
  const home = path.join(root, 'home');
  const sessions = path.join(home, 'sessions');
  const cwdReal = path.join(root, 'project-real');
  const cwdLink = path.join(root, 'project-link');
  const linked = path.join(root, 'linked-session.jsonl');

  fs.mkdirSync(cwdReal, { recursive: true });
  fs.symlinkSync(cwdReal, cwdLink, 'dir');

  const oldFile = path.join(sessions, '2026', '09', '26', 'rollout-old.jsonl');
  const newFile = path.join(sessions, '2026', '09', '26', 'rollout-new.jsonl');
  const linkedFile = path.join(sessions, '2026', '09', '26', 'rollout-linked.jsonl');

  writeJsonl(oldFile, [
    meta('old', cwdLink, '2026-09-26T16:00:00.000Z'),
    message('user', [{ type: 'input_text', text: 'old thread should not win' }], '2026-09-26T16:00:01.000Z'),
  ]);

  writeJsonl(newFile, [
    meta('new', cwdLink, '2026-09-26T17:00:00.000Z'),
    message('system', [{ type: 'input_text', text: 'system prompt' }], '2026-09-26T17:00:01.000Z'),
    message('developer', [{ type: 'input_text', text: 'developer prompt' }], '2026-09-26T17:00:02.000Z'),
    message('user', [{ type: 'input_text', text: [
      '# AGENTS.md instructions\n',
      '\n',
      '<INSTRUCTIONS>\n',
      '# Who you are talking to\n',
      '\n',
      'You are running inside io, a small desktop app.\n',
      '\n',
      '## How to talk\n',
      '\n',
      '- Plain words.\n',
      '- Short answers.\n',
      '\n',
      '</INSTRUCTIONS>\n',
      '\n',
      'Please catch me up on this thread.',
    ].join('') }], '2026-09-26T17:00:03.000Z'),
    message('assistant', [
      { type: 'output_text', text: 'I can do that.' },
      { type: 'reasoning', summary: [{ type: 'summary_text', text: 'hidden reasoning' }] },
    ], '2026-09-26T17:00:04.000Z'),
    {
      timestamp: '2026-09-26T17:00:05.000Z',
      type: 'response_item',
      payload: { type: 'function_call', name: 'exec_command', call_id: 'c1', arguments: { cmd: 'pwd' } },
    },
    {
      timestamp: '2026-09-26T17:00:06.000Z',
      type: 'response_item',
      payload: { type: 'function_call_output', call_id: 'c1', output: cwdReal },
    },
    message('assistant', [{ type: 'output_text', text: 'Done.' }], '2026-09-26T17:00:07.000Z'),
    {
      timestamp: '2026-09-26T17:00:08.000Z',
      type: 'response_item',
      payload: { type: 'reasoning', summary: [{ type: 'summary_text', text: 'hidden' }], encrypted_content: 'secret' },
    },
  ]);

  writeJsonl(linked, [
    meta('linked', cwdReal, '2026-09-26T18:00:00.000Z'),
    message('assistant', [{ type: 'output_text', text: 'linked should not win' }], '2026-09-26T18:00:01.000Z'),
  ]);
  fs.symlinkSync(linked, linkedFile);

  const result = latestThread(home, cwdReal);
  assert.strictEqual(result.id, 'new');
  assert.strictEqual(result.file, newFile);
  assert.strictEqual(result.lastUser, 'Please catch me up on this thread.');
  assert.ok(result.text.length <= 24000, 'handover text must stay bounded');
  assert.ok(result.text.includes('Session handover'));
  assert.ok(result.text.includes('User: Please catch me up on this thread.'));
  assert.ok(result.text.includes('Assistant: I can do that.'));
  assert.ok(result.text.includes('Tool call [exec_command] (c1): {"cmd":"pwd"}'));
  assert.ok(result.text.includes(`Tool output (c1): ${cwdReal}`));
  assert.ok(result.text.includes('Assistant: Done.'));
  assert.ok(!result.text.includes('old thread should not win'));
  assert.ok(!result.text.includes('linked should not win'));
  assert.ok(!result.text.includes('system prompt'));
  assert.ok(!result.text.includes('developer prompt'));
  assert.ok(!result.text.includes('hidden reasoning'));
  assert.ok(!result.text.includes('AGENTS.md instructions'));

  fs.rmSync(root, { recursive: true, force: true });
});

test('latestThread truncates large actual-format sessions', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'io-handover-'));
  const home = path.join(root, 'home');
  const sessions = path.join(home, 'sessions');
  const cwd = path.join(root, 'truncate-real');
  fs.mkdirSync(cwd, { recursive: true });

  const longText = Array.from({ length: 3000 }, (_, i) => `line ${String(i).padStart(4, '0')}: ${'x'.repeat(20)}`).join('\n');
  const file = path.join(sessions, '2026', '09', '26', 'rollout-long.jsonl');
  writeJsonl(file, [
    meta('long', cwd, '2026-09-26T19:00:00.000Z'),
    message('user', [{ type: 'input_text', text: 'make this long' }], '2026-09-26T19:00:01.000Z'),
    message('assistant', [{ type: 'output_text', text: longText }], '2026-09-26T19:00:02.000Z'),
  ]);

  const result = latestThread(home, cwd);
  assert.strictEqual(result.id, 'long');
  assert.ok(result.text.length <= 24000, 'handover text must stay bounded');
  assert.ok(result.text.includes('[older turns omitted to stay within 24000 chars]'));
  assert.ok(result.text.includes('line 2999'));

  fs.rmSync(root, { recursive: true, force: true });
});

console.log(`\n${passed} handover tests passed`);
