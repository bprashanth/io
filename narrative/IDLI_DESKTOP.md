# Idli Desktop: owning the journey from "I want this" to "my whole org uses it"

2026-11-13. A strategy brief to brainstorm from. It mixes things that are built and tested with ideas that are not.
Each claim is marked **[built]**, **[tested]**, **[idea]** or **[untested]**. Design detail is in
[docs/idli-design.md](../docs/idli-design.md), and sharing as built is in
[proposals/idli-sharing.md](../proposals/idli-sharing.md).

---

## 1. The one-paragraph version

Non-technical people at NGOs (and small orgs generally) can now get real work done with AI agents: Claude Code,
Codex, Cursor, MCP tools. But they drop off along the way, and for a few predictable reasons: switching between
tools, privacy, results they can't trust, and fear the agent will break something. Idli Desktop is a single app
that takes a person from "I have a task" to "my whole org runs this", and removes each of those drop-off reasons.
What it produces is a **Mini**: a small, shareable unit of learned work (an analysis, a dashboard, a cross-app
workflow, a branded template). A smart frontier model writes a Mini using test or fake data. A small private model,
or plain code, runs it on real data, as the person, in their own browser, and asks for approval before acting.
Minis spread through an org by a share code.

---

## 2. Where people drop off, and what Idli does about each

| Drop-off reason | What it looks like | Idli's answer | Status |
|---|---|---|---|
| **Switching between tools** | "I did it in Claude, then had to open a terminal, then a different app for Drive, then copy results into a sheet." Every handoff loses people. | **Paseo as the aggregator.** One desktop app hosts many agent CLIs (Claude Code, Codex, cursor-agent, a local model) plus a browser with the person's logins, behind one chat. The person never picks a tool or sees a shell. | [built] in dev; shells hidden from the user |
| **Privacy** | "I can't paste beneficiary data into ChatGPT." Many orgs stop right here, or keep going in secret. | **The student/teacher pattern.** The frontier "teacher" sees only fake stand-in data with the same shape and the same mess. It writes the scaffolding: a form, checks, charts, code. A private "worker" model (a local 9B, or Muse 30B on our hardware) runs it on the real file, which never leaves the machine. | [built], [tested] on synthetic fixtures and the owner's test Drive |
| **Correctness** | "The AI said 412 households, and I can't tell if that's right." Without a way to check, one wrong answer ends trust. | **The form in every Mini.** Each Mini has explicit measures and checks: what counts as a household, which rows were dropped and why, which values look wrong. Every answer can be traced to rows and rules a person can read, not to the model's word. | [built] |
| **Safe editing** | "What if it deletes my sheet?" People are rightly scared of agents with write access. | **Never overwrite, never delete.** Idli works on checked copies, writes through the Google tools people already use (a new tab, a new file), and asks before acting. The original stays untouched. | [built] for Drive files |
| **"Can I do X too?"** (scope) | The person outgrows one app and leaves for a general tool. | **The baseline: everything Claude and Codex can do still works.** Idli doesn't fence people in. Canva through MCP on their own Claude subscription, any CLI task: it all still runs inside Paseo. Minis are extra, not a cage. | [built] (the CLIs run as-is) |

**The core claim to test:** switching tools is the biggest drop-off, and an aggregator fixes it. But an aggregator
alone is a thin moat, since anyone can wrap CLIs. So **why go beyond aggregation?** Because the other three drop-offs
(privacy, correctness, safe editing) are what actually stop an NGO from using AI on its *real* work, and fixing them
needs an opinion about how work is learned, checked and run. That opinion is the Mini.

---

## 3. What a Mini is

A Mini is a **learned, reusable, shareable piece of an org's work**. It has:

- **What was learned:** code, form definitions, checks, chart specs, prompts, branding assets, step scripts.
- **What it acts on (optional):** one specific Google Drive file, an app reached through the browser, or nothing.
- **Who runs it:** a small private model, plain code, or the person's own Claude/Codex subscription.
- **How it spreads:** a share code (`IDLI-XXXX-XXXX`). Whoever receives it says Yes, and it appears in their Minis
  list. **[built]**

Sharing is not data sharing. A Mini carries the workflow, never the data rows. A shared Mini that points at a Drive
file only works if the receiver's own Google account can open that file. **[tested]** on the owner's laptop with
real Drive (fetch on open in 1.0 to 1.5 s); not yet tested across two different Google accounts.

### The kinds of Mini, in increasing ambition

**A. The Drive analysis Mini** **[built, the current focus]**
A dashboard and Q&A for one spreadsheet (a household survey, a field programme tracker). It learns on a fake copy
and fetches the real file from Drive every time it opens, so the numbers are always current. Shared means "the same
dashboard on the same file". Cloning the workflow onto a different file of the same kind is parked (P3).

**B. The org kit Mini** (for example "our Canva Mini") **[idea]**
No Google login, possibly no local model at all. It is a bundle of what an org learns about doing a recurring task
its way: brand colours and fonts, logo files, code snippets, prompt templates, "how we make the monthly
newsletter in Canva through MCP". It is deployed without any web UI, just as a Mini; the person's own Claude
subscription does the work.
- **Revenue:** none. No hosting, no model calls on our side.
- **Why do it:** it **owns the pipe**. The org's know-how lives in Idli and spreads through Idli. Every new member's
  first experience of the org's AI practice goes through our app.

**C. The "UI as API" Mini** (for example a funder reporting dashboard) **[idea, partially derived from A]**
Many funders and partner systems have a web portal and no API. The pattern:
1. **Teach:** the smart model works against a **test account** (fake grantee, fake numbers), explores the portal's
   pages, and writes code that fills the forms, pulls the figures and builds the report.
2. **Run:** on the person's own Idli, the small model reads the real data, drives that code in the app's browser
   using **the person's own logged-in session**, and **stops for approval** before anything is submitted.
3. **Extend:** more skills get added to the same Mini over time (quarterly report, budget variance, beneficiary
   counts).

The browser is the login. Idli never holds passwords, and every action is taken as the person, visible to them.

**D. The cross-app Mini** **[idea, untested]**
Log in to *n* services in the app's browser, then run one workflow across all of them. Same split: the smart model
writes the code against test accounts; the small model reads the situation and decides which code to run on the
real accounts. Example (untested): mirror WhatsApp Web messages tagged `#field` from five field-team groups into
one coordination group, or into a sheet.

---

## 4. The general idea underneath

> **If you can log in to it in a browser, there are DOM elements, and a model can operate them as you.**
> **If privacy matters, a smart model teaches a small model to do that one job, through code, on fake data.**
> **Once it works for you, ship it to your org as a Mini.**

Three moves, in order:
1. **Masquerade.** The browser session already proves who you are. Acting through it needs no API keys, no OAuth
   apps, no integrations team. It works for the long tail of portals NGOs live in: funder portals, government
   MIS systems, WhatsApp Web, Google Workspace, Kobo, CommCare web UIs.
2. **Distil.** The expensive, capable model is used once, to learn, on stand-ins. What it leaves behind is code plus
   small decisions a 9B model can make. Cheap to run, private, repeatable.
3. **Distribute.** The Mini is the unit of org knowledge. Share code, Yes/No, done.

---

## 5. Business shape (to brainstorm)

| Mini kind | Who pays for compute | Our revenue | What we get |
|---|---|---|---|
| Baseline (any CLI task) | The person's Claude/Codex subscription | None | Daily use; the habit |
| Org kit (B) | The person's subscription | None | Owning the pipe; org lock-in through accumulated Minis |
| Drive analysis (A) | Local 9B (free) or hosted private model | Hosted private model (Muse), if not local | Trust through privacy and correctness |
| UI as API / cross-app (C, D) | Teacher: frontier (theirs or ours). Worker: local or hosted | Teaching runs, hosted worker, maybe per-Mini | The highest value: replaces manual reporting hours |

Questions this raises:
- Is "own the pipe, monetise later" credible, and what is the later?
- Do we charge orgs (seats, an org Mini library) rather than per model call?
- Is there a marketplace: Minis for common funder portals, shared across NGOs (with clone, not share)?

---

## 6. Risks and open questions

- **Platform terms.** Automating WhatsApp Web, funder portals and Google through the browser may break their terms
  of service, or trip bot detection. Which targets are safe, which need the official API, and is "the person is
  watching and approves" enough?
- **Brittleness.** DOM-driven code breaks when a site changes. Who repairs it? (Idea: the worker detects the
  failure, and the teacher re-learns against the test account.)
- **Test accounts.** Pattern C/D needs a sandbox or test account per target. Many funder portals don't have one.
  Is a recorded session with the data faked enough?
- **Trust in a shared Mini.** Anyone with a code can add it, and nothing shows who made it. A Mini that acts in a
  browser is far more dangerous than a dashboard. Signing, an org allowlist, and approval on every write action
  become necessary.
- **Shipping the cookie read.** Fetching Drive as the person currently reads the app browser's session through
  DevTools (on in dev builds). Shipping needs a small Paseo change, and a clear story about why that is safe.
- **Sync.** A shared code is a frozen copy today. The proposal (one code per Mini for life, an update card, forks
  never merged) is not built.
- **Is the aggregator the product, or the wedge?** If the CLIs add their own desktop apps and connectors, what is
  left? The hypothesis: privacy, correctness, safe editing and org distribution, which a single vendor's app won't
  prioritise for NGOs.

---

## 7. What exists today (so the brainstorm stays grounded)

- **Paseo desktop app:** Claude Code, Codex and a local model in one chat, with a built-in browser where the person
  signs in to Google once. **[built]**
- **Drive Minis:** teach on a fake copy; a form with measures and checks; charts; a Minis page; share by code; the
  real file fetched as the person on every open. **[tested]** on the owner's laptop, real Drive, test account.
- **Private worker:** Muse 30B on our DGX, or a local 9B; evals on synthetic planted-mess fixtures. **[built]**
- **Not built:** org kit Minis, UI-as-API Minis, cross-app Minis, sync, clone, signing.

The current engineering focus remains the Drive Mini; the rest of this document is direction, not a plan.
