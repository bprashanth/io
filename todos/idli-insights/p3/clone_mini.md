# Clone a Mini (the workflow without the file)

**Share** (shipped 2026-11-13) hands on one Mini: the dashboard for one Google Drive file. The receiver opens that
same file with their own Google account, so it only works if they have access to it.

**Clone** would hand on the workflow alone (form, checks, charts, spelling fixes), with no file. The receiver uses it
on their own file of the same kind: the same register template, survey form or export, matched by tabs and column
headers. It needs its own code, so nobody mistakes a clone for a share.

Already built, and parked from the UI (see [proposals/idli-sharing.md](../../../proposals/idli-sharing.md)):
`share.pack_bytes(id)` without `with_file` makes exactly this bundle (`kind: "file-skill"`), and install,
inspect and the code server all accept it.

To do:
- A code that says which it is: `IDLI-…` for share and, for example, `CLONE-…` for clone, or one prefix and the
  card says "a workflow for your own files".
- A Clone button next to Share (or Share with a choice). Keep the Minis page minimal.
- After adding: Idli recognises the receiver's file when they open it from Drive in an Idli chat. Today that already
  works (`file_open` matches by headers). The Mini row becomes clickable once they've opened one.
- Versions: same question as share (see the proposal's sync section).
- Multiple files: a Mini over several files (a register plus its payments sheet). Later. Several tabs in one file
  already work.
