# 2026-09-15, 23:20 IST — DGX: conversations stop coding words, pages open inside io, charts without a network

Follows `2026-09-15T1856-dgx-sandbox-boundary.md`. The wall runs on this box now, so every
drive below ran with the real sandbox (`IO_DRIVE_BYPASS` unset). Evidence under
`benchmarks/runs/2026-09-14-io-codex/drive-chat/` and `drive-chart/`.

## 1. A conversation with no folder no longer codes the person's words

`IoPolicy.outbound`: the scanner runs on typed text only when a sheltered folder is open.
In a conversation (`<IO_HOME>/chats/...`) the vault holds nothing and the person typed the
word themselves. Known values (an attached file's) and the validators still apply, so a
typed phone number is still coded. Probe: "what is the capital of france? my number is
9876543210 and Ramesh lives in Kandura" left as "...france? my number is PHONE_001 and
Ramesh lives in Kandura". Drive: the question arrived at the model intact
(`chatFranceLeftAsItself: true`, read from the proxy dump). Column names were already
excluded from coding yesterday; documents are deferred, so a PDF can no longer mint a code
for a spreadsheet's column title.

## 4 + 6. The contained viewer, and io opening pages for Codex

`ui/viewer.html` in an io-owned `BrowserWindow` (partition `io-viewer`): the session's
`webRequest` cancels every request that is not `file:`, `data:` or `blob:`, permissions are
refused, the page sits in a sandboxed iframe; images get an `<img>`. A bar says why
("this window has no internet, so nothing on the page can send your data anywhere") with
*reload* and *open in your browser*, the latter disabled under Offline so nobody is locked
in elsewhere. `open-external` for a local file now opens the viewer instead of the system
browser; clicking a filename in the terminal does the same.

Codex cannot open a page from inside the wall, so io watches the sheltered folder
(`fs.watch`, 1.5 s debounce, html/png/svg/jpg): a page or chart that appears or changes is
shown in the viewer, and a chip in the footer reopens it. AGENTS.md now says: save the
file, io shows it, do not run xdg-open.

## 7. Charts offline

matplotlib added to io's runtime (`pins.json`, `matplotlib==3.11.2`; +~40 MB per build).
AGENTS.md: a chart is a PNG drawn with matplotlib (Agg), labelled in plain words, numbers
on the bars; a dashboard is one self-contained HTML file with no external resources.

Drive, folder set to **Offline**, "Draw a bar chart of visits per village from
visits.csv": Codex read the CSV with pandas inside the wall, drew `visits_per_village.png`
with matplotlib, io's viewer opened it (`03-viewer-window.png`: title, axes in words,
numbers on the bars), the browser button is disabled, the chip reads
"visits_per_village.png - show again". No network was involved at any point.

## Tests

30 proxy, 12 launcher.
