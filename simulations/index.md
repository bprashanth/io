# simulations/: independent testing packets

Instructions: 
1. Setup antigravity, extension, io app -  you need to get antigravity version `1.107.0`, see instructions below
2. Pick a packet and download it - this is the data you'll use, and the user you will simulate. Take a minute to understand the org so you can ask questions like them. 


You can regenerate packets 1-3 via `gen.py` and `dialogs.json`.

One packet per team member. Each folder has `data/` (or pointers to data already in the
repo) and a `PROMPTS.md` with the exact questions we ran, what we measured, and what to
verify. All data is synthetic, modelled on the real intake survey (io.xlsx orgs); nothing
here needs special handling. `gen.py` + `dialogs.json` regenerate packets 1-3 exactly.

## Setup (details offline; pointers only)

1. Install Antigravity: repo `README.md`, Quick start A (pinned 1.107.0).
2. Install the shield: `extension/privacy-shield-0.3.1.vsix`, then
   `extension/privacy-shield/TROUBLESHOOTING.md` when anything looks off.
3. Install io: `app/io/README.md` (install.sh once, then run.sh).

## The comparison every packet follows

1. **Antigravity, shield off.** Open your packet's `data/` folder as the workspace. Ask
   question 1. Understand: everything in those files just left the laptop.
2. **Antigravity, shield on.** Enable, accept the one relaunch, wait out the centre-screen
   "reading your files" modal. Ask the same question. Then audit like you don't trust us:
   shield menu -> status page (`calls`, `vault_entries`, `tokens_est_out`); -> vault (what
   was hidden); -> last request, and **ctrl+F a real name and a real phone from the data**.
   Zero hits = the shield did its job. The dashboard on disk still has real values.
3. **io.** Add the same folder as a sheltered dir, read the highlighted review (click a
   highlight to keep/unhide), press Preview to see the exact bytes that would leave, Looks
   right, then the same questions. Check the meta line under each answer ("N rows sent as
   codes, model, seconds"). Build a page, press "share on your network", open it on your
   phone.
4. Note anything confusing, slow, wrongly hidden or wrongly revealed. That's the point.

## Packets

| packet | org/theme (io.xlsx) | file types | the hook |
|---|---|---|---|
| [1 y-ultimate](packet-1-y-ultimate/PROMPTS.md) | sports for development | csv + xlsx + GPS | site-health dashboard, coach support, Pune map |
| [2 foundation-without](packet-2-foundation-without/PROMPTS.md) | urban graduation model | csv with free-text notes | vulnerability ranking, phones hidden inside prose |
| [3 lila-scholarships](packet-3-lila-scholarships/PROMPTS.md) | scholarships | two xlsx + csv | duplicate applicants across years, found on codes alone |
| [4 chats-and-documents](packet-4-chats-and-documents/PROMPTS.md) | Ekibeki (crafts) | WhatsApp, Telegram, txt, pdf | pattern extraction from a chat the model never really read |
| [5 open-data](packet-5-open-data/PROMPTS.md) | any org, public data | csv + txt | the shield must NOT cry wolf; overhead comparison |

## Where the original runs live (for comparing your results to ours)

- io desktop bench: `benchmarks/runs/2026-08-26-io-electron-bench/` (screenshots + results.json)
- Antigravity + shield bench: `benchmarks/runs/2026-08-26-shield-robustness/`
- Document scanner + Ekibeki extraction: `benchmarks/runs/2026-08-25-io-docs-v1/`
- Recall against planted PII (498/498): `measure_recall.py` in that folder
- The story in order: `chronology/2026-08-26T0400-robustness-campaign.md`
