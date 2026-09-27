// Same command permissions as local io; this opt-in experiment uses direct ChatGPT OAuth.
const fs = require('fs');
const codex = require('/opt/io/codex');
for (const key of ['IO_CODEX_NO_WALL', 'IO_CODEX_NO_SANDBOX']) delete process.env[key];
codex.writeConfig('/state/codex', 1, {wall:'offline', trust:'/workspace', codexDir:'/opt/codex', libsDir:'/usr/local/lib'});
const p = '/state/codex/io.config.toml';
const config = fs.readFileSync(p,'utf8').split('\n').filter(l => !/^(openai_base_url|chatgpt_base_url) =/.test(l)).join('\n');
fs.writeFileSync(p, 'forced_login_method = "chatgpt"\ncli_auth_credentials_store = "file"\n'+config);
fs.writeFileSync('/state/codex/config.toml', 'forced_login_method = "chatgpt"\ncli_auth_credentials_store = "file"\n');
fs.writeFileSync('/state/codex/AGENTS.md', `You are helping an NGO user through io's remote Linux experiment.\nWork in /workspace. Uploaded files are copies; do not claim to edit the local original.\nCommands are offline, escalation is forbidden. Use Python for CSV work.\nThe person can attach a copy using the bottom-right button and download outputs using Results. The button copies files into /workspace. If they ask about an attached file, list/read workspace files before claiming it is missing. For images, use the image viewing tool on the workspace file.\nThis experiment does not mask model traffic. Never claim uploaded data stays on the person's device.\n`);
