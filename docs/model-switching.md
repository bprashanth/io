# Model switching: carrying on when ChatGPT runs out

Part of [ARCHITECTURE.md](ARCHITECTURE.md).

**Status, 2026-09-26: proof of concept implemented and driven on Linux arm64.**
ChatGPT is the default. The model control offers **OpenRouter · GPT-5 mini** once a
key has been entered in settings. Choosing it explicitly relaunches the bundled
Codex with the same folder and saved conversation. Model traffic still passes
through the same coding and leak checks in io's proxy.

## Allowance and switching

Before the first message, io uses the bundled Codex's supported
`account/rateLimits/read` app-server method. Codex owns the OAuth token; io does not
read it. Its `/backend-api/wham/usage` request passes through the proxy even before
there is an approved folder. Only the existing account/model metadata GET routes
have that exception; unapproved content requests remain refused.

The proxy observes `rate_limit.allowed`, `limit_reached`, and each window's
`used_percent` and `reset_at`. An exhausted allowance is shown on the opening
screen, with the fallback preselected if a key exists. No model starts until the
person sends a message. During a conversation, an `usage_limit_reached` error
(in JSON or a streamed `response.failed` event) produces a reset-time notice and a
**Switch and resend** button. An ordinary HTTP 429 is not assumed to mean quota.

Retry takes the last user message from the **saved thread**, not the latest proxy
request: Codex also sends background requests to generate conversation titles.
A live fixture drive caught the wrong title instruction being resent; the saved
thread fixes that ambiguity and prevents retries leaking across folders.

The field shapes are backed by Codex's source and exercised with a local upstream
fixture. **A real ChatGPT account's quota exhaustion was not tested on the DGX.**
The fixture drive does finish with a real OpenRouter answer. See
[the evidence](../benchmarks/runs/2026-09-26-dgx/quota-results.json) and
[the official account API](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt).

## Conversation continuity

1. Resume the latest saved thread for this exact folder. The proxy removes
   reasoning items and the previous-provider response reference on the OpenRouter
   route. Visible history still goes through the normal coding pass.
2. If the provider rejects the history or context size, offer **Continue with a
   catch-up**. This starts a fresh thread with up to 24,000 characters of recent
   visible messages and tool results in `AGENTS.md`. No model is needed to create
   it; hidden reasoning and system/developer messages are omitted.
3. If that also fails, offer **Start fresh**, without the catch-up. Say plainly
   that the smaller model could not carry over the thread; the files remain.

Measured with the bundled Codex 0.154.0: a resumed thread remembers its project and
coordinator after a synthetic foreign encrypted reasoning item is removed.
**Codex re-reads `AGENTS.md` on resume**: a new marker added between turns reaches
the model and its answer. A fresh handover also recovered the project name. The
smaller model executed Python inside the wall and wrote the expected CSV total.
[Resume evidence](../benchmarks/runs/2026-09-26-dgx/resume-results.json).

## Keys and provider restrictions

The top-right settings button is available during a conversation. **OpenRouter
key…** opens a separate local window with its own restricted preload. The main
page receives only whether a key exists and its last four characters. Entry is a
password field, cleared immediately on submission. OpenRouter validates the key
through `GET /api/v1/key`; an invalid key does not replace a working one. Remaining
key allowance is shown when `limit_remaining` is reported. An unlimited key does
not imply an unlimited account balance, so io does not invent a credit figure.

Normal mode saves `<io data>/openrouter-key.json` with mode 0600, by atomic rename.
Unlike the old general API-key field, this persists because organisers hand out a
key for repeated visits. Portable mode keeps it **in memory only**, so it does not
travel with a USB stick. Replace/remove takes effect on the next request, without
restarting Codex or automatically changing the provider.

The key goes from Electron's main process to the Python service over its private
stdin pipe. The proxy inserts Authorization only on the OpenRouter route. Codex's
profile has no `env_key`; provider keys are stripped from its environment. Logs,
dumps and provider errors are scrubbed defensively, including previously used keys
for replies still in flight. Routing requires both `provider.zdr = true` and
`provider.data_collection = "deny"`; there is no unrestricted fallback. See
[OpenRouter's routing controls](https://openrouter.ai/docs/guides/routing/provider-selection).

## Limits of this proof of concept

- GPT-5 mini works through OpenRouter's Responses API, but Codex lacks a catalogue
  entry for it and prints a metadata warning. io has not invented capabilities to
  suppress that warning.
- Real quota exhaustion, macOS and Windows drives remain unverified.
- The live history test uses synthetic foreign ciphertext; it does not claim a
  measured migration from a real ChatGPT account's encrypted history.
- Codes protect known private values. Values outside the vault still reach the
  selected provider, as described in [tokenization.md](tokenization.md).
- OpenRouter bills per token. Long histories are resent and cost more; a local or
  room server is still a later proposal.
