---
name: setup-team
description: Setting up a new Idli team with the person - read their setup answers, talk through the team's goal and main workflows, propose a plan in plain words, and build the first pieces. Use when the first message is a new team's setup answers.
---

# Setting up a team

The person just made a team on the Teams page. Idli asked them the fixed questions (name, goal, where the data is,
who uses it, private fields, the outside service) and sent you the answers. Those answers are the platform's
promises: you can't loosen them (for example, use the outside service when they said No).

## 1. Talk (short, one question at a time)

Start with one line that shows you read their answers, then ask about the work, not about technology:
- "What does a normal week of this work look like?" or "What is the one task you'd most like help with?"
- Then: "Walk me through the last time you did it." Listen for the steps, the files, the accounts and the people.
- For each step: what comes in (a file, an email, a voice note, a video), what they do with it, what comes out.
- Which steps are slow or boring? Which must stay private?

Two to five exchanges is enough. Use their words back to them. Don't ask about tools, models or code.

## 2. Plan

Write the plan as a short list the person can read, one line per step, saying for each:
- what Idli does, in their words;
- where it happens: "on this computer", "the private model on this computer", "Claude, with names as codes", or
  "needs a platform feature" (a login, sending, a new account action);
- anything new from the internet, by name, with its size if large. It comes only from Idli's vetted catalog
  (`catalog`), and only tools that fit this computer. If a step needs a tool the catalog doesn't have, or one this
  computer can't run, say so in the plan, offer what can be done now, and send a `catalog_request` (general words,
  no team data): "Our team will check a safe tool for this and add it to Idli's list."

Then ask: "Shall I set this up?" On yes, build. Keep a copy in `TEAM.md` (goal, workflows, the plan, what's built,
what's waiting for the platform): later Builders read it.

## 3. Build

Build the smallest version that does one real workflow end to end on fake samples, then stop and tell them how to
try it ("Pick a video with @ on the left and ask: cut the silences"). Build the rest when they ask. Everything you
build follows the `build-team` skill. Things that need the platform go to `platform_request`, one per need, and into
`TEAM.md` under "Waiting for the platform".
