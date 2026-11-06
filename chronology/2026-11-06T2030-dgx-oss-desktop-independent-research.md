# 2026-11-06, 20:30 IST — DGX: OSS desktop research and agent-to-Muse probes (independent)

Separate from the evaluation another agent is running on `io_silo_untested` at the same time.
Work is on branch `oss-desktop-independent` in its own worktree, with its own evidence under
`benchmarks/runs/2026-11-06-oss-desktop-independent/`. That agent's files, branch, ports and
`/tmp/io-t3-*`, `/tmp/io-paseo-*` directories were not touched. The owner confirmed the
existing hostname for Private is `io.idli.cc`; no route was changed and nothing public was tested.

## What was done

1. Six candidates cloned read-only at pinned commits and read in source: T3 Code, Paseo,
   Happy (with happy-desktop and happy-agent), AionUi, Nimbalyst, plus a metadata check of
   five more. Nothing installed or launched.
2. Muse probed on the three wire protocols agent CLIs use.
3. IO's pinned Codex (0.154.0) and the installed Claude Code (2.1.319) each ran one CSV task
   against Muse with an isolated config home, with every outbound connection traced.

Full table and caveats: [comparison.md](../benchmarks/runs/2026-11-06-oss-desktop-independent/comparison.md).

## Findings

- Muse (llama.cpp b10524) serves Chat Completions, Responses and Anthropic Messages, each
  streaming a valid tool call. So Codex and Claude Code can both use it natively; no adapter.
- Both agents computed the right per-village totals and wrote `result.csv`. Codex took 74 s,
  Claude Code 43 s. Every connection went to Muse on loopback: no DNS, no other host.
- With Muse's port closed, neither fell back to another model. Claude Code fails fast; Codex
  retries indefinitely, which a desktop has to time out and explain.
- Claude Code assumes 200k context for an unknown model; Muse has 65k. Codex uses fallback
  model metadata. Both need tuning before long sessions.
- T3 and Paseo both run the real `codex app-server` and the Claude Agent SDK, honour the
  CLIs' own logins, and support a per-instance model endpoint. Both are single-user per
  server, so architecture B means one server per identity in a container.
- T3's "Muse Code" provider is Meta's product, not our Muse. T3 telemetry is on by default and
  sends hashed OpenAI and Claude account ids; `T3CODE_TELEMETRY_ENABLED=false` turns it off for
  the server and desktop only.
- Happy's default agent reads Claude Code's OAuth access token and calls the model itself, which
  the brief rules out for Open. AionUi is the best fit for non-developers but its remote mode is
  a browser in front of a headless Electron.
- Open question for B: getting a desktop client through Cloudflare Access to a per-user server.
  T3's client source has no custom-header or Access login support (grep); Paseo not yet checked.

## Not done

Desktop apps, screenshots, remote environments, two-user isolation, egress of the apps
themselves, Windows and macOS. Single sample per agent run.
