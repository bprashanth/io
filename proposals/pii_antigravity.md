# PII masking & rehydration proxy for Antigravity

Status: **built and working** — extension `privacy-shield-0.2.7.vsix`
(`extension/privacy-shield/`), verified end-to-end on Antigravity 1.107.0 on
the Linux x64 laptop (apt `1.23.2-1776332190`, 0.2.2, Claude Sonnet 4.6 and
Gemini 3.6 Flash) and on the DGX arm64 build (0.2.3, Gemini 3.6/3.7 Flash,
driven through the real IDE under Xvfb) on 2026-08-22. This document is the living design record: the original
proposal below was written before implementation; §"As built" onward records
what is actually true, measured on the real product. Where the two disagree,
"As built" wins.

## Objective

A zero-configuration local reverse proxy bundled inside an Antigravity
extension. The daemon intercepts the agent's model traffic on this laptop,
replaces personal data (names, phones, Aadhaar/PAN, accounts, emails, villages…)
with deterministic tokens **before anything leaves localhost**, and restores the
real values in the streamed answers and in files the agent writes. The user
sees real data; Google's servers see tokens.

## As built — architecture

```
Antigravity (IDE + app-level language server)
        │  plain HTTP, Cloud Code wire format
        ▼
127.0.0.1:8765  shield_proxy.py        ←— spawned detached by extension.js
   ├─ request pipeline: GLiNER (CPU) + regex validators + column classifier
   │  + in-chat review; vault {value → NAME_001…} persisted locally
   ├─ egress firewall: request blocked if any protected value survives
   └─ response pipeline: SSE event rehydration (+ on-disk backstop for
      files the agent writes)
        │  HTTPS
        ▼
daily-cloudcode-pa.googleapis.com  (Google's Cloud Code backend)
```

- Server: `extension/privacy-shield/server/` — plain `http.server` (not
  FastAPI), GLiNER `knowledgator/gliner-pii-edge-v1.0` on CPU-only torch,
  ~1.7 GB one-time install via `server/install.sh`.
- Extension: `extension/privacy-shield/extension.js` — spawns the daemon
  detached (it survives app quits), points Antigravity at it (see routing),
  status bar with verified/unverified state, click opens an Enable/Disable
  **picker** (no direct toggle: turning the shield off must be a deliberate
  second click, never a misclick).

## How Antigravity is actually routed (the part the original proposal got wrong)

Antigravity does **not** honour `http.proxy`, a public "API base URL" setting,
or `generativelanguage.googleapis.com`-style endpoints. All model traffic —
regardless of the model family picked in the UI — leaves through an app-level
**language server** (a Go binary) that talks to one backend, the Cloud Code
API (`/v1internal:streamGenerateContent`, `loadCodeAssist`,
`fetchAvailableModels`, …).

Measured on 1.107.0 (each of these cost a debugging session; see
`chronology/2026-08-22T*`):

1. The backend URL is resolved by the client as: the **internal, unregistered
   setting `jetski.cloudCodeUrl`** if set, else a built-in default
   (`daily-cloudcode-pa.googleapis.com`).
2. The language server learns that URL in exactly two ways:
   **(a)** as a `--cloud_code_endpoint` launch flag when it is spawned, and
   **(b)** via an RPC push that fires when the client's own `loadCodeAssist`
   completes — ~3 s after app launch, then occasionally on auth refreshes.
3. `CLOUD_CODE_URL` in the environment is **ignored** by this build (earlier
   CLI-era findings said otherwise; that mechanism is dead in the IDE).
4. There are *two* language servers (app-level serves the agent; an
   extension-host one serves completions). `antigravity.restartLanguageServer`
   restarts only the latter. Nothing restarts the app-level one on demand —
   only an app relaunch re-reads the setting deterministically.

Therefore the extension routes as follows:

- **Enable** writes `jetski.cloudCodeUrl` *before* relaunching Antigravity, and
  `deactivate()` keeps the setting across every quit while the shield is
  enabled — so any launch (our relaunch helper *or* the user reopening the app
  normally) spawns the language servers with the proxy as their launch flag.
  This is the only race-free path; writing the setting after launch loses to
  the push in (2b) and the agent silently talks to Google directly.
- **Disable** removes the setting, stops the daemon, and offers a relaunch.
- Non-relaunch paths (enable without relaunch, crash recovery) fall back to
  nudging the push: `antigravity.handleAuthRefresh` +
  `antigravity.restartLanguageServer`. This works but can take up to ~1 min —
  the deterministic path is the relaunch.
- If the daemon cannot be started at activation, the extension **fails open**:
  it clears the setting and re-pushes so the IDE keeps working unshielded. The
  status bar makes this visible (below). A dead proxy port at launch does not
  stall 1.107 — it causes a transient `loginError` that heals once the daemon
  is up (measured; this is why keeping the setting across quits is safe).

### Trust-but-verify (because the knob is internal)

`jetski.cloudCodeUrl` is an internal knob and its semantics already changed
once between 1.104 and 1.107. The failure mode to engineer against is *silent
bypass*: routing quietly reverting to direct while the UI claims protection.
Mitigation shipped in 0.2.2: the status bar shows **"Shield on · awaiting
first call"** until the daemon has actually seen a model call in this session,
and only then the active `🛡️ N calls · X ms · vault M` state. If the agent
answers while the bar still says "awaiting first call", traffic is bypassing
the shield. (This indicator caught a real bypass during testing.) Possible
future hardening: read the LS `/proc/<pid>/cmdline` on Linux/macOS and compare
`--cloud_code_endpoint` against the proxy.

## One wire format for all model families

Model choice (Gemini Flash/Pro, Claude Sonnet/Opus via Vertex, GPT-OSS) does
**not** change the protocol: everything flows through the same Gemini-style
JSON (`request.contents[].parts[]`, `functionCall`/`functionResponse`, SSE
`candidates` events). The model is a field; Google translates server-side (the
seam is visible in errors: Claude runs return `req_vrtx_…` errors phrased in
Anthropic's schema). **We do not implement per-provider protocols.**

The caveat: backends differ in *strictness* over the same format. Gemini
tolerates empty text parts, trailing events after `finishReason`, and split
tool-call arguments; the Anthropic translation rejects them with 400
`text: Field required`. The daemon therefore emits canonical JSON everywhere:

- no `{"text": ""}` parts in requests (footer-stripping and token-echo
  cleanup drop them; orphaned `thoughtSignature`s are re-attached to their
  thought part) or responses (empty parts dropped at event level);
- the `--annotate` footer is folded into the stream's own finish event, never
  appended as an extra event;
- tool-call argument tails are held back only when they are a strict prefix of
  an existing vault token (never truncating ordinary text).

These are model-agnostic hygiene, verified on both families.

## Redaction/rehydration design points (as built)

- **Vault**: `{normalised value → NAME_001/PHONE_002/…}`, persisted locally
  (`shield-vault-local-only.json`), never leaves the machine. Values already
  shaped like vault tokens are never re-minted — including quoted or
  lower-cased echoes from scripts (`'email_002'`) — or double-tokenisation
  chains poison rehydration.
- **Discovery/replacement split (0.2.7, matching the io app)**: the span model
  (GLiNER) *discovers* new values only in file/tool-derived content
  (functionResponse parts — file reads, script output) and in the human's own
  typed question (`<USER_REQUEST>`, scanned with the full engine). Everything
  machine-assembled around them — conversation summaries, user_information,
  metadata, model echoes — is **replacement-only**: known vault values are
  still hidden wherever they reappear, but nothing new is ever minted from
  our own echoes. This removed the vault-junk classes wholesale (footer
  fragments as "addresses", label words as "places") on top of the explicit
  mint guards (generic label words/phrases like "Village" or "Child name",
  token echoes, footer shapes are never mintable).
- **Review is off by default (0.2.7)**: tables are redacted silently with the
  default column classification; the status-bar counts and the vault/wire
  views are the after-the-fact review. Measured reasons: the chat review cost
  a round-trip per new table shape, made models re-issue tool calls, produced
  gibberish prompts on mangled headers, and was the most bug-dense code in
  the daemon. The full machinery remains behind `privacyShield.review:
  "chat"`; the *upfront, per-folder* review is io's differentiator. Known
  trade-off now documented: without review a hidden column cannot be "kept",
  so aggregations over hidden values (email-domain counts) stay token-based.
- **Tables** (CSV/TSV blocks in tool output): column classifier + per-column
  pseudonymisation; with `review: "chat"`, an **in-chat review**: "a table is
  about to leave your laptop, I will hide columns X, Y…". Replies understood:
  `ok` · `also hide <column>` · `also hide <any word/value>` (hidden
  everywhere from then on, e.g. a scheme name) · `don't hide <column>` — and
  clause mixes of all of these in one reply
  (`ok, don't hide scheme, also hide status and Ujjwala`). Decisions are keyed
  by header signature and persist. Reviews are skipped when nothing would be
  hidden and when the table already consists of vault tokens (our own output
  echoed back); a non-answer while a review is pending re-asks (fail-closed).
- **Kept columns still get hard validators**: email/PAN/Aadhaar/IFSC/UPI/
  phone/voter/vehicle regexes (checksummed where applicable) run over cells of
  columns the user kept. Rationale: nested XLSX tables arrive with mangled
  headers (`Unnamed: 2`), the review can misclassify them, and a "kept" column
  must never leak a checksummed identifier. (This exact leak was found in
  testing — two emails escaped through a kept column — and is now closed.)
- **Contact-line heuristic**: a capitalised name immediately before a bracket
  of already-tokenised identifiers (`Surveyor: Anita Kulkarni (EMAIL_004,
  PHONE_019)`) is hidden even when the span model misses it. (Also a real
  measured miss, now closed.)
- **Egress firewall**: after redaction, if any protected value still appears
  in the outgoing text the request is blocked entirely and the chat shows a
  shield message. Token-shaped vault values are exempt (a "leaked token" is
  not a leak — this false positive was hit in testing).
- **Files the agent writes** are rehydrated on disk (streaming rehydration
  usually suffices; an on-disk backstop covers split arguments), so
  `dashboard.html` on the user's machine contains real values while the wire
  never did.

## Smoke test, 2026-08-22 (dashboard use-cases)

Corpus: `beneficiaries.csv` (8 rows: names/phones/aadhaar/villages/schemes/
amounts), `field_notes.txt` (free text + Hinglish, emails, IFSC, ration card),
`inventory_q1.csv` (names under `Item`, phones under `Qty`, PAN inside a
`Notes` cell), `program_data.xlsx` (two nested tables per sheet, merged title
rows, second sheet), `survey_report.pdf` (table + prose contact lines).

| Scenario | Result |
|---|---|
| "Build a dashboard.html from these files" (Claude) | review prompt → `ok, don't hide scheme, also hide status and Ujjwala` honoured exactly → dashboard written, on disk with real values, wire 0 hits for every name/phone/email/PAN/aadhaar/ration number |
| Dashboard rendering | correct layout, correct totals, real names/phones; content-hidden value ("Ujjwala") appears as a redacted scheme — as instructed |
| Follow-up naming a real person (Claude & Gemini) | outbound question redacted (0 wire hits for the name), answer rehydrated and correct |
| Misleading headers (`Item`/`Qty`) | caught by content, review offered |
| Nested XLSX via python | review by content despite `Unnamed:` headers; kept-column email leak found → fixed → 0 hits |
| PDF via pdftotext | validators caught email/phone/aadhaar; prose name missed by GLiNER → contact-line heuristic added → 0 hits |
| Review grammar | all forms verified incl. mixed clauses and content values |
| Egress firewall | fired once (on a token echo — false positive, fixed); fail-closed behaviour confirmed |
| Model families | Claude Sonnet 4.6 and Gemini 3.6 Flash, both shielded, both rehydrate correctly |
| Enable/Disable via picker | two deliberate steps to disable; relaunch round-trips verified both ways |

## 0.2.3 changes (DGX verification, 2026-08-22 evening)

Re-verifying 0.2.2 in the real IDE on a second machine found eleven defects;
all are fixed in 0.2.3 and listed in
`chronology/2026-08-22T2130-shield-0.2.3-verification.md`. The ones that change
the design:

- **Daemon outside the process tree.** VS Code kills the extension host's
  children on quit, so the proxy died during the relaunch, the new instance's
  login check hit ECONNREFUSED and the IDE showed "Log in" for the session.
  The daemon is now spawned via `setsid`/`start`, and the relaunch helper
  waits for `/shield/status.json` before starting Antigravity.
- **No exception may leave the request handler.** A pandas parse error inside
  the review path had left the language server waiting ten minutes. Any
  internal error now returns a visible shield message (fail closed).
- **Credible headers only.** Command errors, tracebacks and tuple-printed rows
  are never "tables" (the review had once listed data values as columns).
- **Repair before refuse.** The egress guard applies the vault substitution
  over the final outgoing body, then blocks only if a value still survives.
- **Recall work in cells and prose**: uppercase/lowercase/initialled names,
  cue-word and contact-line rules, chat-sender rule and in-text propagation,
  GPS before a full stop, `dd/mm/yy` no longer mistaken for a shell path;
  place/address guesses are no longer minted from short cells (junk source).
- **Kept values persist** with the review decisions; a new table column made
  of kept values is kept; free-port selection; Disable stops the daemon.

Routing note for this build: the setting-before-relaunch rule from the laptop
holds on arm64 too; the env variable is kept as well. Both machines now run
the same recipe.

## Clean-install verification, 2026-08-25 (x86 laptop)

Re-ran the participant flow end-to-end on a from-scratch install: apt purge →
apt install `antigravity=1.23.2-1776332190` (→ `antigravity --version` =
1.107.0) + `apt-mark hold`, extension 0.2.5, Python env living in
globalStorage (survives extension updates — verified: two update cycles kept
the 1.7 GB env). Corpus: `tests/test_pii_data.csv` + `.xlsx` (adversarial
headers: emails under `Comm_Route`, phones under `Loc_Pin`, PANs under
`Tax_Code`). Dashboard built and rendered with real values locally; 0 wire
hits for every value; follow-ups on Gemini 3.6 Flash and Claude Sonnet 4.6
both clean, including the agent grepping the real-valued `dashboard.html` on
disk (known values re-tokenised on the way out: 0 hits).

Two more gaps found and fixed in 0.2.5:

- **Bare first names in typed questions** ("give me Priya's email") left
  unredacted: only full values were in the vault and the span model misses
  short possessives. The partial-name pass from the io app is now wired into
  the proxy: a capitalised fragment matching exactly one known NAME/PLACE
  value gets that token (model keeps the linkage); matching several, it gets
  its own token (privacy first — the model then asks for the full name rather
  than guessing a person).
- The partial pass only considers clean name-shaped vault values, so
  span-noise entries (`"Row 5: ['Priya Venkatesan'"`) can't poison it.

## Known limits & brittleness (honest list)

1. **Internal knob dependency.** Routing rests on `jetski.cloudCodeUrl` +
   launch-flag semantics; any Antigravity update can move it (it already did
   once). Mitigated by the verified/unverified status indicator, not
   eliminated. Re-run the smoke suite on every new build before an event.
2. **Upstream host is pinned** in the daemon (`daily-cloudcode-pa`). If a
   future client switches default hosts, redacted traffic goes to the wrong
   backend. Future: pass the client's own default to the daemon.
3. **Fail-open on daemon failure** at activation (IDE keeps working,
   unshielded, bar stays "awaiting first call"). Deliberate trade-off; a
   fail-closed mode would brick the agent when the daemon breaks.
4. **GLiNER recall on prose names** is imperfect (validators are
   deterministic; names are ML). One measured miss in the smoke test, patched
   by a heuristic; assume a small residual miss rate for unusual name shapes
   in noisy text. Over-redaction also occurs (scheme names, "Alias"/"Taluka"
   as villages) — recoverable via `don't hide` and cosmetically annoying, not
   privacy-relevant.
5. **Paraphrase gap**: if the model paraphrases instead of echoing a token
   ("[Scheme C]" for `CUSTOM_001`), rehydration cannot restore the original.
   Inherent to token-based rehydration.
6. **Review fatigue on script output**: every new output format is a new
   header signature → new review. Empty reviews and token-echo reviews are now
   suppressed, which removes most of the noise; some repetition remains when
   scripts keep changing their print format. Also, the review consumes a model
   turn, after which the model sometimes re-issues the tool call once.
7. **Latency**: first redaction of a large history costs seconds
   (~3–17 s measured worst-case after a daemon restart with cold cache);
   warm-cache steady state is ~10–300 ms per call.
8. **Cross-platform**: everything above is measured on Linux x64 only. The
   relaunch helper has macOS/Windows code paths that are untested; Windows has
   no `/proc` for future cmdline verification.
9. **Aggregations over hidden values are impossible by design**: "count by
   email domain" on a hidden email column comes back token-based — the model
   never sees domains. Demo scripting: keep such a column with `don't hide`,
   or accept the gap.
10. **The vault is global and accumulates across sessions/workspaces** (it
   lives in globalStorage). People from earlier datasets stay known — good
   for consistency, but bare-name fragments can become ambiguous across
   datasets. Between participants or demos, run "Privacy Shield: Forget this
   session's vault".
11. **Environmental, not shield**: this laptop's Antigravity intermittently
   fails `run_command` ("failed to check terminal shell support") with the
   shield off too; and its browser subagent could not download its playwright
   driver. Watch for these at the event venue — they look like shield bugs and
   are not.

## Version pinning for the Sep 2–4 event

- Pinned and tested: **Antigravity 1.107.0** = apt `1.23.2-1776332190`
  (currently the *latest* the Linux apt repo serves, i.e. what a participant
  who follows the download instructions gets today). The in-app "2.5.5" update
  toast refers to a channel apt does not serve yet.
- Participants download ~Sep 1: **re-run the smoke suite on whatever the repo
  serves that day** before sending instructions (routing knobs and model
  wire-strictness are the two things to re-check; both have changed before).
  If a newer build lands and breaks routing, the fallback is to distribute the
  tested 1.23.2 `.deb` alongside the extension.
- macOS/Windows participants (if any) are untested territory — either test on
  those OSes next week or scope the event to Linux machines.

## Deliverables (current)

- `extension/privacy-shield/` — extension + bundled server (source of truth).
- `extension/privacy-shield-0.2.2.vsix` — installable package.
- One-time env install: command palette → "Privacy Shield: Install Python
  environment" (runs `server/install.sh`, CPU-only torch pinned).
- Evidence: `debug/20260822T1040-antigravity-server-crash/` (local only,
  gitignored) — screenshots, wire-view hit counts, logs for every claim above;
  `benchmarks/runs/2026-08-22-antigravity-ide-shield/` (frozen DGX evidence).

---

## Original proposal (2026-08, pre-implementation — kept for history)

> Build a zero-configuration, local reverse proxy daemon bundled inside an
> Antigravity extension… *(superseded; notable deltas: the real product has no
> `antigravity.apiBaseUrl`/`http.proxy` — routing is via `jetski.cloudCodeUrl`
> + relaunch semantics; endpoints are Cloud Code `/v1internal:*`, not
> `generativelanguage`/`v1beta`; the server is stdlib `http.server` + GLiNER
> `gliner-pii-edge`, not FastAPI/ONNX `gliner_multi_pii`; tokens are
> `NAME_001`-style, not `[PERSON_1]`; and the daemon must outlive the app —
> `deactivate()` must NOT kill it.)*
