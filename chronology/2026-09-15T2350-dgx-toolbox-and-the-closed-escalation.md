# 2026-09-15, 23:50 IST — DGX: the toolbox, and closing the escalation hole with it

Follows `2026-09-15T2330-dgx-mode-switcher.md`. Real sandbox throughout. Evidence:
`benchmarks/runs/2026-09-15-dgx/toolbox-exec/` (three `codex exec` transcripts) and
`benchmarks/runs/2026-09-14-io-codex/drive-render/` (seven screenshots, `results.json`,
the coded picture itself under `data/renders/`, which is not committed; a copy of what it
showed is in screenshot 05).

## The hole, and why it closes now

The laptop entry of 16:40 found that Codex's approval prompt is one switch for two things:
"run this command outside the sandbox" and "let this MCP tool run". `-a never` closed the
first and made the second impossible, so T4GC tools had to keep escalation open to have
tools at all, and the card had to admit that a "yes" there hands a command the whole
machine. The handoff listed intercepting the prompt from the PTY as the way out.

There is a cleaner one in Codex 0.154 itself. A server in `[mcp_servers.<name>]` takes
`default_tools_approval_mode`; the value `"approve"` is checked *before* the approval
policy (`codex-mcp/src/mcp/mod.rs`, `mcp_permission_prompt_is_auto_approved`: the first
line returns true for `Approve`; only then does `AskForApproval::Never` matter). So a
server io registers that way runs with no prompt under `-a never`, and every shell
escalation is still refused. Measured, `codex exec` with the fake toolbox
(`codex-fake4.txt`):

    approval: never
    mcp: io/render_page started
    mcp: io/render_page (completed)

Every setting now launches `-a never` **and** writes `approval_policy = "never"` into the
profile (so `codex exec` is covered too; it rejects `-a`). `WALLS.escalate` is gone;
`WALLS.tools` says whether the toolbox is registered. Offline has none, by construction.

## Two things that hid the tool

1. **Where the table goes.** A `[mcp_servers.io]` table in `io.config.toml` is honoured
   (`codex mcp list -p io` shows it, and the server is started at session init), so io
   keeps owning one file and `config.toml` stays Codex's.
2. **Deferred exposure.** With the server running and its `tools/list` answered, the
   model still said "render_page is not available" (`codex-tools.txt`, `codex-fake.txt`).
   The request through the proxy showed why: the tool list carried a `tool_search` tool
   and no `render_page`. Codex 0.154 puts MCP tools behind a BM25 search step when the
   model supports it (`ToolExposure::Deferred`), and a low-effort model never searches.
   `[features.code_mode] direct_only_tool_namespaces = ["mcp__io", "io"]` makes the
   namespace direct; the request then carries a `namespace` tool `mcp__io` with
   `render_page` inside it, and the call happens. (The namespace is the server name with
   Codex's `mcp__` prefix when prefixing is on; both spellings are listed.)

Also seen on the way: the provider's hosted `web_search` is in the tool list too. It is
provider-side traffic from coded context, but "does not go to a website by itself" should
mean it; `web_search = "disabled"` unless the setting is Open. And Codex reads
`$HOME/.agents/skills` from outside `CODEX_HOME` (an ERROR about a skill file on this
box). Skills are instructions, not data, so it is a note and not a hole.

## The renderer

`tools/mcp.js`: a stdio MCP server, run as io's own binary under `ELECTRON_RUN_AS_NODE`
with only the environment written into the profile (Codex passes a fixed set plus the
configured `env`, `rmcp-client/src/utils.rs`). It calls io's main process over loopback
with a token only the profile carries; commands inside the wall cannot read the profile.
`main.js` does the work: the page must be an `.html` inside the working folder; its text
goes to the service's new `/api/code-text`, which codes it exactly as a request is coded
(known values, then the validators; no scanner); the coded copy is written under io's own
`renders/`, loaded in a hidden window on a partition that refuses every URL except files
in that directory, screenshotted, and the copy deleted. The picture goes back as MCP
`image` content and crosses the proxy as an `input_image` data URL.

The proxy needed one change for that: `walk_strings` passes a `data:` URL through
untouched. Before, a validator would have read a digit run in the base64 as a phone number
and rewritten the picture into garbage (test:
`test_a_data_url_is_passed_through_untouched`). This is the point the proposal made: the
proxy cannot see into a picture, so what a picture shows is decided where it is made.

## The drive

`drive.js --render`, T4GC tools, real sandbox: "Make a page called visits.html with a
table of name, village and visits from visits.csv, then use the render_page tool to check
how it looks and tell me what you saw."

| | |
|---|---|
| page written | `visits.html` in the folder, real names in it (Codex works on real files) |
| tool called | `Called io.render_page({"file":"visits.html"})`, no prompt of any kind (`approvalPromptSeen: false`) |
| what Codex saw | screenshot 05 and `data/renders/*.png`: `NAME_003 / PLACE_002 / 7`, `NAME_001 / PLACE_001 / 4` ... |
| what the person sees | screenshot 06, the viewer: `Ravi Test / Hillcrest / 7`, `Alice Example / SecretVillage / 4` ... |
| through the proxy | one request carried a `data:image/png` and it arrived intact (`imageRequests: 1`) |
| Codex's answer | described the layout (title, search box, "4 of 4", visits 7/4/2/1) and did not remark on the codes |

The numbers are not coded (they are not private values) and the model read them off the
picture; that is the residual the proposal named, and it is the same residual every text
request has.

**Toolbox in the UI.** The T4GC card links to "What's in the toolbox" (screenshot 02):
one entry, what it does, what it sees, what it reaches ("nothing"). The same window opens
from a **toolbox** button beside the Setting control and, after a render, shows the exact
picture the assistant was shown with a "show me the real page" button (05, 06). A footer
note says a picture was shown (`noteShown: true`, screenshot 04); a line written into the
terminal was tried first and the TUI repaints over it, and the first two runs of the drive
found the event exposed under the wrong name in the preload, which is the kind of thing
only running the app finds.

## Left open

- The Open card still says "install extra software": inside the wall with network that
  means into temp, not into the home directory. Wording, not behaviour.
- `verified_access` pass-through: unchanged, still refused nine times a session.
- The switch control could disable itself while a turn is running (2330 entry).

## Tests

31 proxy (one added: the data URL), 15 launcher (two added: the toolbox registration and
exposure, and the MCP server over stdio; the wall test now asserts no profile may escalate).
