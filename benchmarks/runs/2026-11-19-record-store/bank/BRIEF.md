# Brief for the task writer

You are writing realistic requests that staff at a small NGO would type into a private assistant ("Idli") that can
read their own Google account and, later, other sites. Read goal.md (the product's goal) first.

## What is in the test account (as a person would know it)

"Me" (an NGO programme person) has a Google account with:
- **Gmail:** about 190 emails in the last two months. Some are replies from leads (people the NGO contacted about a
  reading programme visit) offering or picking meeting times; calendar invitations, acceptances and declines;
  LinkedIn and other notifications; a few newsletters.
- **A leads sheet** in Google Sheets: names and emails of about five people the NGO is following up with.
- **Google Calendar:** about ten meetings in Oct-Dec, some with leads, some declined.
- **Google Drive:** about 190 files.
  - **"NDSA fixity study":** a 2021 survey report (PDF) with its data (CSV), and the 2025 edition.
  - **"Strategy Classics":** 18 PDFs of classic management/strategy papers. A shared copy, "[Public] Strategy
    Classics", has subfolders by reader.
  - Folders of study notes and papers: Development, Econometrics, Power, Caste, Strategy Process, Strategy
    Content, GRE, Blog, SI, Misc, epw.
  - About 14 spreadsheets (some Google Sheets, some Excel), 33 Google Docs, a couple of forms and slides.
  - About 19 photos (jpeg/png) and 4 short videos.
- A second account ("a lead") exchanges emails with "me" for testing.

They also use, or would like to use: WhatsApp (funders, field staff groups), Slack or Mattermost, Canva, LinkedIn.

## What to write

Write 80 requests in people's own words. Vary the persona (programme lead, office coordinator, finance head,
field researcher, communications person) and the phrasing (short, vague, typos, follow-ups that point at an
earlier answer such as "no, the one from Ravi" or "the second one").

Cover three kinds, roughly evenly, as in goal.md:
1. **other_site:** WhatsApp, Slack/Mattermost, Canva, LinkedIn, Amazon, a funder portal (about 15).
2. **own_definition** on Google: their own idea of a category ("conservation-related", "urgent", "a funder",
   "photos with people in them", "papers about power"), about 30.
3. **own_workflow** on Google: multi-step jobs ("every Monday, list leads who haven't replied and draft a nudge"),
   about 20.

Also about 15 **trust** questions a new user asks before relying on it ("is my Gmail connected?", "how many files
are in the fixity folder?", "what columns does the leads sheet have?", "show me yesterday's meetings").

Some requests should be sessions: 2-5 turns, where later turns build on or correct earlier ones.

Do not invent facts about specific emails or files beyond the brief. For each request, write what a correct
answer would need to contain, at the level a careful assistant could check (e.g. "the count of PDFs in the fixity
folder", "a list of threads, each with sender and date, that are about conservation; empty is acceptable if none").
Mark whether it only reads, or would change something (draft, send, book, move, post).

## Output

Write two JSON files in this folder, each a list of objects:
`{"id": "T01", "kind": "trust|own_definition|own_workflow|other_site", "persona": "...", "turns": ["...", "..."],
"expect": "...", "changes_things": false, "site": "gmail|calendar|sheets|drive|whatsapp|slack|..."}`

- `tasks_dev.json`: two thirds of them.
- `tasks_heldout.json`: the other third, a fair mix of every kind.

Pick the split yourself, at random. Write nothing else.
