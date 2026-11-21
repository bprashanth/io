# One window: Idli on the left, Claude on the right, a highlight on whoever has control

Owner, 2026-11-12: switches between Idli and Claude should only move the focus, prominently (a border on the panel
in control), instead of jumping between workspaces.

Checked on the DGX with Paseo 0.15.2 (the io-oss-paseo image; scripts in this session's scratchpad, recreated
easily):
- Split panes are per workspace (`layoutByWorkspace`, `splitSizesByWorkspace`; tabs point at agents). Plugins
  can't arrange panes (the plugin API only has openAgent / openWorkspace / openBrowser).
- A chat's folder is its workspace's: `paseo run --workspace <priv> --cwd /tmp/fake` ran in /tmp/priv. So
  Claude can't just join the Idli workspace: it would run in the private-data folder.
- A provider whose command is a wrapper (`cd <cowork> && exec claude "$@"`) works: Paseo started it in the
  workspace folder, Claude ran in the fake-data folder (logged by the wrapper).

Plan:
1. Provider `diy-claude` command = a wrapper that runs Claude Code in the cowork folder; teach_send starts the
   Teach chat in the Idli workspace (not the Claude one) and opens it in a right-hand split.
2. Check: Claude Code's session resume (sessions are stored by its own folder), permissions and the sandbox all
   follow the wrapper's folder; Paseo's file explorer still shows the Idli folder (the Claude panel never
   lists it).
3. The focus border: a small Paseo patch (Paseo already tracks the focused pane); switches call the existing
   uiswitch deep link, which focuses the pane holding that chat.

## Built (2026-11-12)
Paseo patches P13 (agent link `~right`/`~left`) and P14 (focus ring), see `paseo_patches.md`; provider `idli-teach`
(`cowork/desktop/claude-teach.sh`, no `mcp__paseo` browser tools); `teach_send` starts Claude's chat in Idli's
workspace and opens it on the right when `config/ui.json` has `"split": true`. Website teaching (test accounts in
the browser) stays in the Claude workspace. Tested on the DGX in Paseo's web UI; laptop install needs one sudo step.
