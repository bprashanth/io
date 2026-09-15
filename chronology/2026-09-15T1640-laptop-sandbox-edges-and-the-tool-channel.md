# 2026-09-15, 16:40 IST — the sandbox edges, and how a tool would reach io

Third laptop entry today. Follows `2026-09-15T1501-laptop-three-walls-and-the-toolbox.md`.
Everything here needed bwrap actually working, which is why it was done on the laptop and
not the DGX. Screenshots 76-82 in `benchmarks/runs/2026-09-15-laptop/`.

## Renames

"Stays offline" is now **Offline**. "io's tools only" is now **T4GC tools**: io is the
distribution channel, T4GC is who vets what lands in it. The card says so.

## The hole under the label

io set no approval policy, so Codex's default (`on-request`) applied: the model may ask the
person to run a command *outside* the sandbox. That is the "Environment: local" prompt seen
earlier today when it wanted `xdg-open`. Someone who says yes gets a command with the whole
machine and the whole network, whichever setting they picked. "Offline" would have been a
label rather than a fact.

`-a never` closes it: execution failures go back to the model instead of becoming a question
for the person. Offline now launches `codex -p io -a never`, verified from the process table.

## What that broke, and what it revealed

With `-a never`, an MCP tool call returns

    Error: MCP tool call requires approval, but approval policy is never

So the escalation lock and the tool channel are the same switch. That is the central
finding of this session and it shapes the design: **Offline cannot have tools, by
construction.** Which is right, and worth saying out loud on the card rather than treating
as a limitation.

## How a tool reaches io: answered, and it needs no broker

The open question was how Codex could ask io to run something. A local MCP server is the
channel, and it is already allowed: the `apps`/`plugins` flags io switches off are the
OpenAI-*hosted* catalogues that the proxy also refuses. `codex mcp add` is a different
mechanism and it survives io's config rewrite, because io owns `io.config.toml` while
`codex mcp add` writes `config.toml`.

The experiment, in T4GC mode with `[permissions.io.network] enabled = false`:

| | result |
|---|---|
| shell: `curl http://127.0.0.1:8878/` run by Codex | `EXIT=7`, connection refused, listener saw nothing |
| MCP tool `net_check` on a server io registered | `MCP SERVER REACHED THE NETWORK: ok`, listener logged the hit |

A loopback listener stood in for the internet so nothing external was touched. The contrast
is the proof: **commands Codex runs are inside the wall and have no network; an MCP server
io registers runs outside it and does.** That is exactly the boundary "only T4GC tools go
online" needs, and it exists today. No broker to build.

Codex's own approval prompt for a tool call is already the app-store gesture:

    Allow the t4gc-probe MCP server to run tool "net_check"?
      1. Allow                    2. Allow for this session
      3. Always allow             4. Cancel

"Always allow" is per-tool and persistent. An installed, trusted tool is one click.

The probe server and its registration were removed afterwards; `codex mcp list` is empty
again and `config.toml` is back to empty.

## Where that leaves the three settings

| | commands online | io opens a page | may escalate / call tools |
|---|---|---|---|
| Offline | no | no | no |
| T4GC tools | no | yes | yes |
| Open | yes | yes | yes |

The residual risk, and it should be written on the card before this ships: in T4GC mode the
same approval prompt that lets a vetted tool run also lets the model ask to run an ordinary
shell command outside the sandbox. Per-tool approval is Codex's, not io's, so io cannot
currently allow tool calls while refusing command escalation. Options are to teach io to
intercept the approval (it owns the PTY, so it sees the prompt), or to accept it and make
the prompt text say plainly which of the two is being asked for.

## Not done here, deliberately

The mode switcher is designed but not built. `codex resume <id>` and `--last` exist, so a
switch is a Codex relaunch under a different profile with the thread continued, and the
service, proxy and vault are untouched. `spawnSession` now takes a `resume` id and the wall,
so the plumbing is in place; the UI is not, and it is not sandbox-dependent, so it belongs
on the other machine.

## Tests

29 proxy, 11 launcher. The launcher suite now asserts that Offline can never escalate and
that an unknown setting inherits the suggested one's escalation rather than the open one's.
