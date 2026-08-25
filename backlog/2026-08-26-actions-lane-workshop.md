# Can io start apps the way Antigravity does? The workshop lane

The question (2026-08-25): "with ag I can ask it to set up an ODK server and design forms
directly in chat - is such a thing possible in io? can we use the antigravity harness pointed
at the api key, or the hermes/codex/deepseek harness? how to let the user take actions on
their laptop without massive cost or latency."

## The measured probe (this run)

Workspace: a tokenised copy of gram-sudhar's visit log (NAME_xxx / PLACE_xxx via the stage-3
engine; leak-checked clean). Task given to codex CLI (gpt-5.6-sol, one `codex exec`):
"build a stdlib-only dashboard web app on 127.0.0.1:8850 from ./data, start it, verify with
curl". Result: **working app in 2m38s, 37k tokens (a few cents), zero real values in the
workspace or the served page** (29 distinct codes, 0 names). Screenshot:
`benchmarks/runs/2026-08-26-io-fixes-v1/07-workshop-codex-dashboard.png`.

Two operational lessons:
1. **io must own process lifetime.** The server codex started died with codex's session. The
   harness should BUILD and verify; io starts/stops the result (same pattern as io's share
   listener) and hands out the LAN link.
2. Nested sandboxes fight: codex's bwrap failed inside a sandboxed shell
   (`bwrap: loopback: Failed RTM_NEWADDR`). In production io IS the parent, so io provides the
   isolation: a throwaway workspace directory containing ONLY tokenised copies, and a port
   range. The harness then runs with plain permissions inside it.

## Answers to the specific options

- **Antigravity harness pointed at our key**: not packageable - AG is an IDE, its agent is not
  invokable headlessly as a component, and its loop assumes its own UI for review. Rejected.
- **Hermes**: already measured (2026-08-24): right shape (gateways, skills) but 83 s/answer
  with the 9B and discipline loss; as a T1/T2 shell it stays the fallback packaging.
- **codex/cursor CLI + frontier over a tokenised workspace**: this probe. Works, cheap,
  latency tolerable ("some latency is tolerable" - 2-4 min per build). The stage-3 measurement
  (27B via io.py: 22/22, 0 raw reads) plus this probe make it the recommended engine.

## Proposed shape (not built yet)

A fourth explicit lane in io: **workshop**. User asks for an app/tool, io:
1. materialises `workspace/<n>/data/` = tokenised copies (vault, same as chat payloads),
2. runs the harness once with a contract (stdlib-or-declared-deps, build in ./app, do not
   start servers - print a RUN line instead),
3. leak-gates every file the harness wrote (known_regex over outputs),
4. starts the app itself on a shield-owned port, shows "running - share on your network",
   with stop/restart in the UI; pages the app serves stay tokenised unless the user shares
   rehydrated data on purpose (window.data injection, same as chat pages).
Costs: one frontier harness run per build; nothing resident. ODK-class asks ("set up a form
server") fit if the contract allows declared dependencies installed into the workspace venv.

Deferred with it: whether the workshop harness may read the interaction log to reuse skills.
