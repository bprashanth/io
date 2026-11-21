# A separate browser for agent work (brainstormed 2026-11-18, parked)

Context:
- Google blocks sign-in in Paseo's embedded browser.
- Google workflows now use the APIs, so they need a browser only for the one-time "allow Idli" sign-in.
- A browser the agent controls matters for sites with no API (portals, CRMs).
- The test-account Chrome profiles work (`lib/chromeprofiles.py`): the person signs in with the agent off, and the
  agent takes over afterwards.

What we'd want: kept apart from the person's everyday Chrome (no sync, no extensions), pinned to one version,
shipped or installed by Idli, controllable by the agent.

| Option | Notes |
|---|---|
| **Chrome for Testing** (first choice) | Google's versioned automation build, about 150 MB, fetched on first need with a sha256. Our CDP code works unchanged. It has no sync and shows a "for testing" banner. Google sign-in with the agent off is untested |
| Playwright's Chromium | The same idea with less Google branding. We already use it in DGX tests |
| Firefox (unmodified official builds) | Google sign-in works. It needs a WebDriver BiDi client next to our CDP one. A fallback if a site blocks Chromium-based automation |
| Edge | Windows only, and not pinned |
| Camoufox and other anti-detect browsers | No: built to evade bot checks |
| Agentic browsers (Comet, Atlas, BrowserOS, Dia) | No: can't be packaged, and the agent would be theirs, outside our privacy rules |
| System web views (WebView2, WKWebView) | No: Google forbids sign-in in embedded browsers |

**The test, before choosing (about 20 minutes, the person signs in twice):**
1. Download Chrome for Testing and Playwright's Chromium into separate folders.
2. Open each with the agent off. The person signs in to the 87 test account.
3. The agent takes over: read Gmail, add a Calendar event, and do the "allow Idli" OAuth sign-in in it.
4. Note what Google accepts, and whether a banner or warning gets in the way.
