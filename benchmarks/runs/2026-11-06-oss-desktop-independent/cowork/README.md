# Co-work prototype: Gmail and Drive as tools for Muse (laptop, 2026-11-07)

`gcowork_mcp.py` is a dependency-free stdio MCP server. It drives the user's signed-in tabs in the Paseo
desktop browser through the daemon's agent endpoint
(`http://127.0.0.1:6767/mcp/agents?callerAgentId=$PASEO_AGENT_ID`). It turns page snapshots into
small JSON, so a 65k-context model can use Gmail and Drive.

| Tool | Returns |
|---|---|
| `gmail_search(query)` | Sender, subject, date and snippet for each row (~1k chars, versus a 32k-char page) |
| `gmail_open(n)`, `gmail_read_open_email` | Subject and message text (~2.6k chars) |
| `gmail_draft_reply(text)` | Types into the reply box. **No send tool exists.** |
| `drive_search(query)` | File names and IDs |
| `doc_read(doc_id)` | Text from `/mobilebasic`. **No edit tool exists.** |

## Wiring (`~/.paseo/config.json`)

- `daemon.browserTools.enabled: true`.
- Provider `t4gc-cowork`:
  - `extends: "claude"`.
  - `command` adds `--mcp-config gcowork.mcp.json`.
  - `env` sets `ENABLE_TOOL_SEARCH=false`, which stops Claude Code from hiding MCP tools behind ToolSearch.
  - `disallowedTools` removes Bash, the file tools, the web tools, Task, Skill and `mcp__paseo`.

## Results, Muse (muse-glimmer-30b), one run each

| Task | Raw Paseo browser tools | gcowork |
|---|---|---|
| Find the AWS "payment not received" email | Overflowed context after ~10 min, after first searching the home dir | Correct invoice and amount, 142 s, 11 tool calls, peak ~37k tokens |
| Correct the grammar of the Wildfires doc | Could not open the doc, then overflowed | Good, 102 s, 2 tool calls. One wrong fix: "wideacale" → "widespread" instead of "widescale" |
| Draft a reply to a LinkedIn survey email | — | Drafted and left unsent, 72 s. The draft contradicts itself slightly |

Snapshots of real mail used while developing the parsers are not in git.
