# 2026-11-14, 18:30 IST — The person's own Claude Code beside Idli, masked, end to end

The owner's plan: Drivey's right-hand panel is the person's own Claude Code (subscription), seeing codes, while the
person sees real values. It must work with a subscription login. If Claude couldn't, fall back to Codex as io did.

## Findings
- **Paseo can't do the masking itself.** It starts Claude Code but never sits between it and Anthropic; it only sees
  the terminal output or the event stream after the fact. The cut must be on the network path: `ANTHROPIC_BASE_URL`
  pointing at a local proxy. Paseo has no built-in model proxy. Its plugin servers run in the daemon with a
  lifecycle, so the shipped app can host the proxy as a plugin later.
- **A subscription login works through a proxy.** Tested on the DGX with Claude Code 2.1.323: the subscription
  OAuth token and the oauth beta header pass through, and Anthropic answers 200
  (benchmarks/runs/2026-11-14-claude-proxy-subscription).
- **Carrying the login to a DGX container** is simpler than Codex's port-1455 callback relay:
  - `claude setup-token` gives a long-lived token, read from `CLAUDE_CODE_OAUTH_TOKEN`;
  - `claude auth login` has a paste-the-code flow.
- **Not checked:** whether Anthropic's subscription terms allow a prompt-rewriting proxy.

## Built
- **`lib/ccproxy.py` (Codex, worktree io-idli-ccproxy; 22 tests with privacy):**
  - masks every string in requests (system, messages, tool results, tool inputs) with the vault (all mask-mode files,
    one session vault), close matches and regex;
  - GLiNER via privacy.idli.cc only on what the person typed;
  - unmasks JSON and streamed SSE replies (text and tool-input deltas; partial codes are held until complete);
  - signed thinking is left untouched;
  - a 403 if a known value would still leave;
  - a content-free log, and an optional wire log.
- **Mine:**
  - the `ensure` command;
  - the scanner User-Agent fix (Cloudflare had 403'd Python's default, so GLiNER silently fell back to regex);
  - provider `idli-claude` and its launcher `desktop/claude-masked.sh` (starts the proxy, runs the person's Claude
    Code in `~/idli-insights/claude-masked`, with `drive/` linked and its own CLAUDE.md about codes);
  - the `claude_open` tool, and "Work on it with Claude" on the Send card;
  - the router routes a question typed into another card's "Other" box like a typed question.

## Tested
- **DGX, synthetic file:** masked Claude Code answered with real names and the right numbers. 0 real values in 6
  wire captures.
- **Laptop, in the app, the owner's real households file, the laptop's Claude Pro subscription:**
  - In Drivey with Muse, the question went out as "why is PLACE_002 so vulnerable…".
  - "Work on it with Claude" opened Claude (Opus) beside Idli.
  - It ran pandas on the real file and found Yerawada is 2nd (5.3 vs Ramtekdi 6.3), driven by debt (Rs 81,667,
    7.4 months of income). It named the two households pulling the average up, with real names on screen.
  - A follow-up typed with real names ("Nandini Chavan", "Mohit Jadhav", "Kasewadi") got an answer in real names.
  - In what left the laptop, those names and every ward name appear 0 times; only codes (PLACE_002, VALUE_180…).
- The laptop's old per-file vaults were moved to `~/idli-insights/archive/vault-per-file-*` (the session vault
  replaces them).

## Open
- **Next pieces of the plan:**
  - Idli's search box with @ files;
  - `idli_show` (charts from Claude drawn in Idli's panel, clicks back to Claude);
  - "Make a Mini".
- The right pane is very narrow at the laptop's current window size.
- **Proxy limits:** it is text only, with no command sandbox, and unknown names in tool output are caught only by
  vault/regex.
- The laptop proxy is running with `--wire-log` (owner-only files in `cowork-real/ccproxy-wire/`) so the owner can
  check what left.
