# 2026-11-07, 16:15 IST — Laptop: T3 / Paseo / AionUi UX on Muse, and a Gmail/Drive co-work prototype

The owner installed Paseo 0.15.2, T3 Code 0.1.7 and AionUi on the Pop!_OS laptop and pointed them at
T4GC Muse through the providers in [laptop/](../benchmarks/runs/2026-11-06-oss-desktop-independent/laptop/).
I ran the same small "dashboard from visits.csv" request in each without telling the agent how to do
it, then built a co-work prototype on Paseo.
[Evidence and screenshots](../benchmarks/runs/2026-11-06-oss-desktop-independent/laptop/shots/),
[co-work code and results](../benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/README.md).

## Dashboard request, all three apps on Muse

| App | Result |
|---|---|
| **T3** | Best. The reply links the HTML file; clicking it opens a rendered side panel, and CDN charts load. |
| **AionUi** | Works through Files → Preview/Download. |
| **Paseo** | Has a built-in HTML preview (Files → file → Preview), but only finds it if you know to look. |

AionUi has more problems:
- It requires an aionui.com account.
- The CODEX_HOME override was saved but not applied, so the Codex chat silently went to OpenAI.
- Sentry breadcrumbs record the override bodies.
- Agents default to full access.

AionUi is dropped.

Paseo's preview has two gaps:
- Its iframe is `sandbox="allow-scripts"`, so external `<script src>` such as a Chart.js CDN does not load. The charts render empty unless the libraries are inlined.
- Agent replies print paths as code, not as links, so users never find the preview.

## Paseo browser tools and co-work

- **Browser tools.** Paseo has built-in agent browser tools (`daemon.browserTools.enabled`) that drive tabs in the desktop app's
  workspace browser, with the user's own sign-ins. Each workspace has its own tabs, but they share one cookie store
  (`persist:paseo-browser`).
- **Raw tools on Muse failed.** Muse with only these raw tools overflowed its 65k context:
  - Gmail snapshots are 8–11k tokens each.
  - Muse also searched the home directory in bypass mode and read browser and Gmail-connector files. That is a privacy failure.
- **Fix: "UI as API".** `cowork/gcowork_mcp.py` is a stdio MCP server that calls Paseo's `/mcp/agents` browser
  tools, parses the snapshots and returns compact JSON.
  - It has no send tool and no edit tool.
  - It runs under a shell-less provider `t4gc-cowork`, which has no Bash, file or web tools.
- **Results on Muse:**
  - Finding the AWS unpaid-invoice email: correct, 142 s, peak ~37k tokens (before: overflow).
  - Grammar on the Wildfires doc: good, 102 s, with one wrong correction.
  - A LinkedIn reply: drafted and left unsent in 72 s.
- **Gotchas:**
  - Gmail and Docs block `browser_evaluate` (Trusted Types), so these pages are read from snapshots. Drive allows it.
  - Docs read cleanly via `/mobilebasic`.
  - Gmail row refs appear only after render, so the tools poll.
  - The agent MCP endpoint has no authentication when the daemon has no password.

## Next

The owner proposed two modes:
- **DIY:** Claude Code builds site plugins against *test* accounts.
- **Co-work:** shell-less Muse uses those plugins on *real* accounts.

For the POC we agreed on these shortcuts:
- Claude Code's sandbox plus written instructions instead of hard isolation.
- Skills.
- Tests that fail when the test login is missing.
- Users scrub PII from error text by hand.

Single samples throughout.
