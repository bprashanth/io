# Prompt for the laptop agent: test and fix io's Codex mode on the real machine

Paste this to the agent on the laptop (the one with the display, the ChatGPT login and
bubblewrap). The DGX where the code is written cannot run Codex's sandbox or the OAuth,
so the laptop is where these things are proven.

---

You are on the laptop that io is tested on. The repo is `~/src/github.com/bprashanth/io`,
branch `io_codex`, already fast-forwarded from the DGX. io's Codex is already signed in
(its state is in `~/.local/share/io/codex/home`; never touch `~/.codex`, which is a
different Codex belonging to me). The design and the exact privacy claim are in
`docs/io-codex.md`; the trail of what was built and why is in
`chronology/2026-09-14T*.md` and `chronology/2026-09-15T*.md`. Read `docs/io-codex.md`
first.

Run the app from the checkout: `cd app/io && ./run.sh` (it installs what is missing and
starts Electron). Use it like a person would, with the synthetic data in
`benchmarks/pii/corpus` (never real beneficiary data). Keep the proxy log open in another
terminal: `tail -f ~/.local/share/io/io.log | grep proxy`. Start with
`IO_PROXY_DUMP=/tmp/io-dump ./run.sh` when you need to see what left (the dump holds only
codes, never real values).

Check, in this order, and fix what fails:

1. Sheltered folder: Sign in -> shelter `benchmarks/pii/corpus` -> the confirm dialog
   lists spreadsheets as scanned, documents as "coming soon", other files as ignored ->
   review sheet -> Preview -> Looks right -> the terminal opens. Ask "what files do you
   see?": it must answer with no approval prompt (the sandbox runs `ls`). Ask "plot on a
   map the main locations in household_survey.csv": a page must be written and open in the
   browser, and the script it writes must use the real column names (`village`,
   `gps_lat`), not codes. In the proxy log every request should be 200 and `restored`
   should be non-zero on answers.
2. The wall: in a conversation (type into the chat box on the landing page, no folder),
   ask it to list the files in your home folder. The sandbox must refuse or show nothing;
   it must not read `~`. Then `attach a file` (a csv from the corpus) -> review -> Looks
   right -> back in the same conversation -> ask about the file.
3. The terminal: Shift+drag selects, Ctrl+C copies the selection, Ctrl+V pastes, the
   "copy text" button copies the screen, a link in the output opens the browser, a page
   Codex wrote under the folder opens on click. Resize the window: the terminal follows.
4. Restart io: it comes back signed in, and `codex login status` in a normal terminal
   still shows my own account (`~/.codex` unchanged).
5. Every refusal in the proxy log (`note` field) is a bug unless it is the fail-closed
   case you caused on purpose. `leaks: [{"code": ..., "keys": [...]}]` tells you which
   code and which JSON key; find why the transform missed it.

Rules: change code in `app/io/` and tests in `app/io/tests/` only; run
`app/io/.venv/bin/python app/io/tests/test_codex_proxy.py` and
`node app/io/tests/test_codex_launcher.js` before every commit; write what you found and
changed in a new `chronology/2026-09-15T<HHMM>-laptop-<topic>.md` (timestamp, what you
saw, screenshot path under `benchmarks/runs/2026-09-15-laptop/`, the change, the
re-test). Use synthetic data in screenshots. Commit on `io_codex` with a message that says
what changed and why, then `git push origin io_codex`. Do not touch `main`. If something
needs a decision (a design change, a new dependency, anything outside `app/io`), stop and
write it down instead of doing it.
