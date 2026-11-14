# Claude Code through a local proxy, on a subscription login (2026-11-14)

**Question:** can Claude Code, signed in with a Claude subscription (OAuth, not an API key), run through a local
proxy? A masking proxy needs that, the same way io masked Codex.

**Test (DGX, Claude Code 2.1.323, the DGX's own subscription login):**
```sh
python3 passthru.py 8871 result.jsonl &        # forwards to api.anthropic.com; logs path, status, login type only
ANTHROPIC_BASE_URL=http://127.0.0.1:8871 claude -p "Reply with exactly: proxied hello" --model haiku
```

**Result** (`result.jsonl`): `HEAD /api/hello` 200, then `POST /v1/messages` 200, carrying
`Authorization: Bearer sk-ant-oat…` (the subscription OAuth token) plus the `oauth` beta header. Claude answered
"proxied hello". **A subscription login works through a base-URL proxy**, and the proxy sees and can rewrite the
whole request and response.

**Carrying the login to another machine** (from Claude Code's own help and binary):
- `claude setup-token` makes a long-lived token on a subscription. The CLI reads it from `CLAUDE_CODE_OAUTH_TOKEN`
  (or `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR`), so Claude Code can run in a container on the DGX with the person's
  token.
- `claude auth login` has a paste-the-code flow (`platform.claude.com/oauth/code/callback`). Someone signing in from
  inside a remote terminal opens the URL on their laptop and pastes the code back. Unlike Codex's localhost:1455
  callback, no relay is needed.

**Not checked:** whether Anthropic's subscription terms allow routing through a proxy that rewrites prompts.
