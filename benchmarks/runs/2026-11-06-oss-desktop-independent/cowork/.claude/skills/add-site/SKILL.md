---
name: add-site
description: Add or repair a co-work site plugin (the tools the private T4GC model uses on a website or file type). Use when the user pastes a "CO-WORK GAP REPORT", asks to add a site/tool to co-work ("add wix", "co-work can't read attachments"), or when run_tests.py shows a site failing.
---

# Add or fix a co-work site plugin

You are in **DIY mode**: a capable model working on TEST accounts and mock data. The plugins you
write here are later used in **co-work mode** by the private T4GC model (no shell) on the user's
REAL accounts. You never see real data, so build tools that are robust and generic.

## Rules
- Work only in this folder. Use only the test account named in `accounts.local.json` for the site,
  signed in to this workspace's browser. Do not look for or use other accounts, browser profiles,
  cookies, `~/.paseo`, or other folders. If the test account isn't signed in, ask the user to sign in.
- Tools are read-only or draft-only. Never write a tool that sends, deletes, edits, submits, pays
  or publishes. Drafting into a form for the user to review is fine.
- If the user's pasted text contains personal details, don't repeat them; ask for generic terms.

## Steps
1. **Understand the gap.** Read the report: what was wanted, which site, which tools exist
   (`.venv/bin/python cowork_mcp.py --list`). Prefer extending an existing `sites/<site>/`.
2. **Easiest integration first.** If the site has an official MCP server or simple export URL,
   say so. An MCP server is the better choice for non-private data used directly in DIY mode;
   co-work plugins live here.
3. **Test data.** If the test account lacks what you need (an email with an attachment, a
   sample sheet), tell the user exactly what to create in the test account, then wait.
4. **Explore** with the Paseo browser tools (`browser_list_tabs`, `browser_navigate`,
   `browser_snapshot`, `browser_click`, `browser_evaluate`) in this workspace. Prefer stable
   URLs and accessible names over clicking around. Gmail and Docs block `browser_evaluate`
   (Trusted Types): parse `browser_snapshot` there; Drive allows it.
5. **Write the plugin** in `sites/<site>/tools.py`, following `sites/google/tools.py`:
   - `TOOLS = {name: (fn, description, json_schema_properties, required)}` and `whoami()`
     (returns the signed-in account, raises `lib.browser.NotSignedIn`).
   - Use `lib.browser` (paseo, tabs, tab_for, snapshot, evaluate) and
     `lib.accounts.account(site)` so tests use the test account and co-work the real one.
   - Return compact JSON (aim under 3,000 characters), never whole pages: the co-work model
     has a small context. Say in errors what the user can do.
   - Descriptions are for a small model: plain, short, say when to use the tool.
   - Files the user may want to analyse go into the co-work workspace folder, where the
     `sheets` site (Excel/CSV + SQL) can read them.
6. **Tests.** Add cases to `sites/<site>/tests.json` and update `sites/<site>/site.json`.
   Put ids/names of test-account items in `accounts.local.json` under `<site>.fixtures` and refer
   to them as `{{name}}` in tests.json, so nothing from an account is committed.
   Run `.venv/bin/python run_tests.py <site>` until it passes. Run all sites at the end.
7. **Hand back.** Tell the user, in plain words: what the new tool does, the test result,
   and "start a new co-work chat and ask again" (tools load when a chat starts). If the site
   is new, add it to `cowork.sites` in the co-work workspace folder.
