# Drivey's Claude: masked copies and the sandbox

How the person's own Claude Code (the right pane in Drivey) is kept away from their real data. This is the Claude
Code setup. The older Codex setup (io) is in [sandboxing.md](sandboxing.md). Current as of 2026-11-15.

## Three layers

| Layer | What it stops | Where |
|---|---|---|
| Masked copies | Claude's commands and scripts only ever see codes | `lib/maskcopy.py` |
| Sandbox and permission rules | Claude reading the real files, the vault or Idli's settings | `lib/launchsettings.py` |
| Masking proxy | Real values in anything sent to Anthropic | `lib/ccproxy.py` |

Plus Idli's own tools (MCP, `lib/idli_mcp.py`), which run outside the sandbox and are the only way from Claude to
real values: `unmask` and `lookup` need the person's yes twice (Claude Code's ask prompt and Idli's consent page).

## The launch

`desktop/claude-masked.sh` (Paseo provider `idli-claude`) does this every time, in order, and starts nothing if a
step fails:
1. Removes an old `drive` link to the real downloads, if one is there.
2. Writes the masked copies with `maskcopy.build`. If this fails: "Idli couldn't prepare the masked copies; not
   starting Claude (nothing was sent)."
3. Starts the proxy. If it fails: "Idli's privacy proxy didn't start; not starting Claude (nothing was sent)."
4. Writes `.claude/settings.json` with `launchsettings.merge(work, data_dir)` and the MCP config (0600).
5. Starts `claude` with `ANTHROPIC_BASE_URL` pointing at the proxy. API keys from the environment are removed, so
   the person's own subscription login is used.

## Folders

| Folder | What it is | Claude's shell |
|---|---|---|
| `~/idli-insights/claude-masked/` | Claude's work folder | read and write |
| `~/idli-insights/claude-masked/drive/` | masked copies of the reviewed files | read |
| `~/idli-insights/cowork-real/` (`IDLI_DATA`) | real downloads, vault, privacy choices | blocked |
| other folders in `~/idli-insights/` | other workspaces, config | blocked |
| `~/.cache/idli`, `~/.paseo`, `~/.config/Paseo`, `~/.config/paseo`, `~/.config/idlisseus` | Idli caches, Paseo and browser sign-ins, the query service key | blocked |
| `~/.claude/projects/` | Claude Code's transcripts, which hold real values (Claude's replies with codes put back) | blocked for the shell only; Claude Code itself reads them |

## The settings Idli writes

In `~/idli-insights/claude-masked/.claude/settings.json`, merged into whatever is there:

```json
{
  "permissions": {
    "ask": ["mcp__idli__unmask", "mcp__idli__lookup"],
    "deny": ["Read(//<each blocked folder>/**)", "Edit(//<each blocked folder>/**)"]
  },
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false,
    "filesystem": { "denyRead": ["<each blocked folder>", "~/.claude/projects"] }
  }
}
```

- `permissions.deny` covers Claude Code's own Read, Edit and search tools.
- `sandbox` covers every shell command (bubblewrap on Linux, Seatbelt on macOS). `autoAllowBashIfSandboxed` means
  the person isn't asked about each command, which is fine because the command can't reach anything private.
  `allowUnsandboxedCommands: false` removes Claude's way to retry a command outside the sandbox.
- Linux needs `bwrap` and `socat` installed and user namespaces allowed. The laptop and the DGX have them.
- Network from shell commands is left at Claude Code's default. Idli adds no domains. Not yet tested on its own (see
  open items).

## The masked copies

`maskcopy.build(data_dir, work)`:
- Copies only files the person reviewed (privacy mode "mask"). Unreviewed files are not copied at all, and a copy
  is removed when its file stops being reviewed.
- Keeps layout and types cell by cell (openpyxl): same sheets, rows, columns, number and date cells. Only cells in
  hidden columns, and known private values anywhere else, change.
- A cell in a hidden column becomes its code. A repeated header inside the sheet stays as it is. A revealed value
  is written as the real value.
- Comments, hyperlinks, defined names and document properties are dropped.
- Rebuilt on every launch, after every reveal and after a reveal is hidden again (`/api/reveals/hide`).

## Numbers

Rule from 2026-11-15 (`privacy.matched_in_text`):
- A cell in a column the person hid is always coded, whatever it holds.
- In free text (Claude's messages, scripts, script output, other cells), numbers of up to three digits and short
  decimals (6, 52, 4.5) are not matched against hidden values. Masking them turned counts and totals into codes and
  Claude couldn't read its own results.
- Numbers with four or more digits (amounts, phones, Aadhaar, PIN codes) and decimals with four or more places
  (GPS) are still matched.
- Column suggestions: a column of small numbers is suggested visible (counts and measures) unless its heading looks
  like an identifier (id, phone, number, Aadhaar, PAN, account, card and similar).
- The scanner never tags a bare number.

## What Claude is told

`idli/CLAUDE-masked.md` (copied in as `CLAUDE.md`) and the `masked-data` skill say: the files are masked copies; use
codes exactly as they appear; the real files aren't reachable and Claude must not look for them; never guess what a
code stands for or ask the person to type real values. When a place, species, programme or category matters, ask
with `unmask` (one value, or a whole column of up to 80 values for one reveal). To search the web about one, unmask
it first and then use WebSearch. `lookup` only when the person wants the search without showing Claude the value.
People's names, phones, IDs and exact locations are never revealed.

## How the person sees real values

- Claude's text replies: the proxy puts real values back in place of codes.
- Charts (`idli_show`) and Mini drafts (`idli_draft_mini`): Idli puts real values back in titles, data and scripts.
  Mini scripts get real values only inside string literals, so a saved Mini runs on the real file.
- Commands and raw script output in the Claude pane show codes, because that is what Claude ran and saw.

## Tested

- DGX, shola fixture, real Claude Code CLI on the owner's Pro login (2026-11-15): given the real path, Claude used
  its copy and declined to read the private folder. `cat` and Read were refused by the permission rules; a Python
  script got "No such file" in the sandbox. Wire audit of 52 requests: no names or sites, no species before its
  reveal.
- Tests: `tests/test_maskcopy.py` (copies, rehydrated Mini scripts, reveals, settings, numbers),
  `lib/test_home.py` (launcher writes the sandbox block).

## Open items

- Network from sandboxed commands: confirm that a script can't post the copies anywhere (they hold codes only, so
  the harm is small, but check).
- Inference: Claude can still work out a code's meaning from structure (which species grows where). The masked
  copies stop guessing against real values; they don't stop reasoning. Accepted for contextual values.
- The proxy masks Claude's own history. If Claude writes a guess that exactly matches a hidden value, the next
  request shows it as a code, which confirms the guess. Possible fix: don't mask text Claude itself wrote.
- Running a script on the real file through Idli: [todos/idli-insights/p1/run_on_real.md](../todos/idli-insights/p1/run_on_real.md).
