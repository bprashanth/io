# 2026-09-15, 15:10 IST — three settings for the folder, and giving the wall a toolbox

Follows `2026-09-15T1159-laptop-restoration-and-session-handle.md`. Screenshots in
`benchmarks/runs/2026-09-15-laptop/` (59 onwards). Synthetic corpus only.

## Why

Two things came out of using the app rather than reading it.

The first was asked in an ordinary chat with no folder open: "what is the capital of france".
The answer was "I don't have enough information to identify france." The proxy dump shows
what actually left: `what is the capital of PLACE_003`. The scanner ran on the typed
question, the model could not identify a code, and the reply was faithfully restored to
"france" on the way back, so the person reads their own word in a nonsense sentence. In a
conversation with no folder the vault is empty and the person typed the word themselves;
there is nothing to protect and the substitution is pure cost. That one is not fixed here
and is listed at the end.

The second: `import pandas` failed inside the wall. `sys.path` listed the right directories
and `sys.executable` was `/usr/bin/python3`, but the only pandas, numpy and openpyxl on this
laptop were a per-user install under `$HOME`, which the wall correctly refuses. So Codex
took spreadsheets apart by unzipping the xlsx and walking the XML by hand, failed on
`xl/sharedStrings.xml`, and retried four times before giving a partial answer. The wall's
privacy value is that it blocks other people's files; what it blocked in practice was the
toolbox.

## Three settings, chosen before anything is read

A new screen sits between picking a folder and scanning it, modelled on Antigravity's
introductory screen: a quiet title, a muted explainer, three cards, one marked Suggested,
one primary action. They are defined once in `codex.js` as `WALLS`:

| | commands reach the internet | io opens a page it wrote |
|---|---|---|
| Stays offline | no | no |
| io's tools only *(suggested)* | no | yes |
| Open | yes | yes |

The folder boundary does not move between them. Commands may write the sheltered folder and
temp, read what the platform needs plus io's own runtime, and nothing else, in all three.
A test asserts that, and asserts that an unknown or missing name falls back to the suggested
setting and never to the open one.

The lede says the thing that is easy to get wrong: this is about the **tools** the assistant
uses, not about the conversation. What you ask and anything it reads from your files is
turned into codes before it leaves and travels encrypted in all three.

"Stays offline" also declines to open a page. That is not decoration. A page Codex writes is
the one route out of the wall that io itself operates, it carries whatever data Codex chose
to embed, and it has full network the moment it opens. Demonstrated against a localhost
listener: a page of the kind Codex writes sent real names, phone numbers and GPS out of the
browser, with the proxy and the wall both uninvolved. Chrome does block a `file://` page from
reading a sibling CSV, which does not help, because the data is inlined when the page is
written — which is exactly what a genuine chart page does anyway.

The choice is remembered per folder and preselected next time.

## Giving the wall a toolbox

io ships a python that has pandas, numpy and openpyxl. Two changes make it reachable:

- the profile grants read on io's runtime directory (io owns it, it holds nobody's data);
- the runtime's `bin` goes first on Codex's PATH, so `python3` *means* io's python.

The grant alone was not enough and that was the trap: reading a venv does not put it on
`sys.path`. AGENTS.md now says the packages are there and to stop hand-parsing spreadsheets.

Verified in the app under "io's tools only", with network off:
`python3 -c "import pandas,openpyxl,numpy"` prints `2.3.3 3.1.5 2.2.6`.

## Can network be scoped to just io's own tools?

Not from the profile io writes. `[permissions.<name>.network]` has exactly one field,
`enabled`. The struct has no `deny_unknown_fields`, so an `allowed_domains` key there is
accepted and silently discarded — worth knowing, because it would look like it worked.
`-p <profile>` fixes the profile for the whole process; there is no per-command switch on
the interactive or `exec` surfaces.

Three real mechanisms exist, none of them reachable from where io sits today:

- `/etc/codex/requirements.toml` (`experimental_network`) does support `domains`,
  `denied_domains`, `proxy_url` and `managed_allowed_domains_only`. It is an admin-managed
  file under `/etc`, so it fits an organisation rollout and not a USB stick.
- `codex sandbox <cmd>` takes `-P/--permission-profile` per invocation, so the engine can
  run one command under a different profile.
- A runtime permission request exists (`RequestPermissionProfile`, `NetworkPolicyAmendment`)
  where the agent asks and the person approves network for one call. This is the prompt seen
  on 2026-09-15 when Codex asked to run `xdg-open` locally.

The unit of scoping in all three is a destination or a moment, never "this script is ours".
For "only io's tools go online" the enforcement has to be that those tools are io-side
processes outside Codex's sandbox, invoked through a narrow broker. That is why the middle
card says what it does today rather than promising tools that do not exist yet.

## Still open

- **Tokenising a conversation with no folder.** The france case above. The scanner should
  not run on typed text when no folder is sheltered, or the person has to be able to see
  which of their words were replaced. Right now the only feedback is a rising code count and
  a green "Protected by io", both of which read as good news.
- **The broker** for io's own online tools, per the section above.
- **A contained viewer.** Opening Codex's pages in an io-owned window with a strict CSP
  would let bundled Leaflet work, make a tile host an explicit allowlist entry rather than
  something a written URL does to you, block the beacon demonstrated here, and give io a way
  to screenshot a rendered page back to Codex without Codex touching the network.
- **matplotlib** is on no python on this machine. Charts are hand-written HTML today.

## Tests

`app/io/.venv/bin/python app/io/tests/test_codex_proxy.py` — 29 pass.
`node app/io/tests/test_codex_launcher.js` — 11 pass (two added: the three walls, and the
runtime grant).
