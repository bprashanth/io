# Ways to scout for data (web search and known sources)

Noted 2026-11-15. Lookup (the masked Claude asking Idli to search for a place) uses Google News RSS and Wikipedia.
We want broader search: for lookups, and for a Mini that searches, reads the pages it finds, fills a sheet and
drafts an email.

## What was tried
- **SearXNG** (the DGX container `odysseus-searxng-1`, used by the Odysseus research loop): on 2026-11-15
  Brave was rate limited, DuckDuckGo and Startpage showed CAPTCHAs, Qwant denied access, Google, Wikipedia and
  Mojeek returned nothing, and Bing returned 10 unrelated adult sites for "Satpur Nashik flood". It also runs on
  our server, so a lookup through it would show our server the real value.
- **DuckDuckGo HTML** from a script: HTTP 202 bot challenge.
- **Headless Chromium to google.com** from the DGX: redirected to google.com/sorry (blocked).
- **Works:** the Paseo browser on the laptop (signed in, home connection), opened with `window.__idliOpenTab` and
  read over DevTools (the tab is a `webview` target). 11 Google searches (6 of them 3 s apart), Bing,
  DuckDuckGo and DuckDuckGo HTML all returned 7 to 10 relevant results with no CAPTCHA. Opening a result and
  reading its text worked. Google's terms do not allow automated queries, so this is for the PoC only.

## Lesson from idlisseus
`idlisseus/dss/HISTORY.md`: search was the wall for every harness and model; the fix was connectors to known
sources plus a cache, not better search. `dss/loop/scout.py` calls GBIF, Zenodo and CKAN directly.
`totalrecall/.../connectors/litscout.py` walks OpenAlex author graphs to find datasets.

## Candidates
- Indian places: Local Government Directory and Census village and ward lists; OpenStreetMap place search.
- Catalogues: data.gov.in (CKAN, so `ckan_search` works), Zenodo, OpenAlex, GBIF for species.
- A search API with a key and a free tier, if general web search is still needed.
- The person's own browser opening a search page they can see, read by Idli, as a PoC only.

## Rules for any of these
- A search that carries a real value runs from the person's computer, never our server.
- Results reach Claude masked.
- A Mini may draft an email or fill a sheet. It never sends.
