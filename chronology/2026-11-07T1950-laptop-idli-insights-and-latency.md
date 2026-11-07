# 2026-11-07, 19:50 IST — Laptop: everything outside the repo moves to ~/idli-insights; Muse latency explained

The owner asked for one home for the co-work POC's state, and to treat this as Paseo-only from now on
(T3 can be redone later). The owner had already moved `cowork-real` and `cowork-real-9b` into `~/idli-insights`.

## Moved

| From | To |
|---|---|
| `~/oss-test` | `~/idli-insights/oss-test` |
| `/tmp/oss-test` | `~/idli-insights/oss-test-paseo` |
| `~/.claude-t4gc` | `~/idli-insights/config/claude-t4gc` |
| `~/.codex-t4gc` | `~/idli-insights/config/codex-t4gc` |
| `~/.claude-or-9b` | `~/idli-insights/config/claude-or-9b` |
| `cowork/accounts.local.json` | `~/idli-insights/config/accounts.json` (mode 600) |

## Updated to match

- `~/.paseo/config.json` provider paths (backed up first, then `paseo reload`). All providers still show available.
- `lib/accounts.py`, which falls back to the old path; `setup-laptop.py`; `check-from-dgx.sh`.
- The DIY sandbox deny list: the private folders and the OpenRouter config. DIY may read only `config/accounts.json`.
- The docs. [driving-desktop.md](../docs/driving-desktop.md#idli-insights) has the layout and the bootstrap
  steps for both the laptop and the DGX.
- [docs/cowork-poc.md](../docs/cowork-poc.md) now opens with a "What changed" list, as the update channel to the DGX agent.

The laptop side was checked: sheets tests 5/5, and the account lookup finds the new file.

## Latency (owner's question)

"Are you there" took about 10 s on Claude but 41 s on T4GC Muse. Muse's log for that request shows:
- **The cause:** a 33,752-token prompt (Claude Code's system prompt and tool definitions) re-read at about 880 tokens/s,
  taking 38.2 s, then 64 tokens written in 2.2 s. The prompt cache had evicted its oldest entry.
- **Co-work provider, same question:** 16,438 tokens, 19.2 s to read, 22 s total.

The model is not slow at answering. It re-reads Claude Code's preamble. Untried ways to cut this: a larger
llama.cpp `--cache-ram` on the DGX (Muse is shared, so the owner decides), fewer slots, or a trimmed co-work
system prompt.
