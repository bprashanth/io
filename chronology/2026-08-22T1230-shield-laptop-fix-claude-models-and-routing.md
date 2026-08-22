# Laptop bring-up: the crash was three bugs, none of them the redactor

Diagnosed the user's laptop (Pop!_OS 22.04) where 0.2.0 showed "Antigravity
server crashed unexpectedly". Full evidence in `debug/20260822T1040-…/report.md`
(gitignored, local); code on branch `shield-laptop-fix`, extension 0.2.1.

1. The laptop ran Antigravity 1.104.0 (apt, 8 months old): its chat was dead
   without the shield too (`neither PlanModel nor RequestedModel` on every
   Gemini entry) and the "crashed" banner is a 1.104 display bug (stale exit
   event of the previous language server). Updated to 1.107.0 — the build the
   extension was developed on — via user-local extract; fresh sign-in needed
   (the token does not survive the 1.104→1.107 migration, and unified state
   persists only on graceful quit).

2. Routing rule revised for 1.107.0 (supersedes the DGX note): the agent's
   language server takes `jetski.cloudCodeUrl` as a launch flag, or from a push
   that fires when the app's own loadCodeAssist completes ~3 s after launch;
   `CLOUD_CODE_URL` in the environment is ignored. 0.2.0 wrote the setting at
   activation (~9 s) — always after the push — so Enable/Relaunch produced an
   unshielded agent under an "active" status bar. 0.2.1 writes the setting
   before the relaunch and preserves it across that one quit; both language
   servers then spawn on the proxy endpoint and the first message is shielded.
   A dead daemon at launch no longer stalls 1.107 (transient loginError that
   heals when the daemon comes up), so keeping the setting is safe.

3. Claude-family models 400'd (`text.text: Field required`) on daemon output
   that Gemini tolerated: empty text parts left by stripping our own footer
   from replayed history, the annotate footer sent as an extra event after
   finishReason, and the rehydrator's 24-char tail hold truncating tool-call
   arguments that arrive whole. Fixed: tidy_parts() on requests (drop empty
   text parts, re-attach orphaned thoughtSignature), note folded into the
   finish event, arg tail held only for strict prefixes of vault tokens, and
   PseudonymMap.token() never re-mints a vault token (summaries echo tokens
   back at user role; that had produced NAME_006→"NAME_001" chains).

Verified end to end on 1.107.0 with Claude Sonnet 4.6: review prompt → ok →
answer with real values rehydrated, status bar `🛡️ 4 calls · 685 ms · vault 35`,
0 wire-view hits for every name/phone/email/PAN/village; Disable/Enable via the
extension's own relaunch both ways. Gemini entries in this client are rejected
server-side ("no valid model") — client/server drift, not ours. install.sh
re-run end to end; CPU-only torch kept.
