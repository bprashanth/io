# A tool store for io: vetted tools that may reach out, when the assistant may not

> Status, 2026-09-15 (DGX): the first cut is built and is called the **toolbox**, not a
> store: one local MCP server io registers, one tool (the renderer), and the escalation
> question below answered without intercepting the PTY. See
> `chronology/2026-09-15T2350-dgx-toolbox-and-the-closed-escalation.md`. The catalogue,
> signing and the other two tools remain proposals.

## Context

io gives a person three settings when they shelter a folder (`Offline`, `T4GC tools`,
`Open`). They say what the *tools* the assistant uses may reach; none of them changes the
model traffic, which is always tokenised and encrypted. The middle setting is the suggested
one and it currently promises something that does not exist yet: that tools T4GC has vetted
may go online while nothing the assistant runs can.

The mechanism for that turned out to exist already and was proved on the laptop on
2026-09-15 (`chronology/2026-09-15T1640-laptop-sandbox-edges-and-the-tool-channel.md`). This
proposal is about what to build on top of it.

## What was proved

In a folder session with the wall's network switched off:

- a shell command the assistant ran could not reach a loopback listener (`EXIT=7`);
- a tool on a local MCP server that io had registered reached the same listener and said so.

Commands run inside the wall. An MCP server io registers runs outside it. That is a process
boundary, not a promise, and it is the enforcement "only T4GC tools go online" needs.

Two constraints came with it:

- Codex's approval policy is the same switch for command escalation and for tool calls.
  `-a never` makes `Offline` honest and also makes tools impossible there. So **Offline has
  no tools, by construction** — a property to state, not to engineer around.
- In `T4GC tools`, the approval prompt that lets a vetted tool run also lets the model ask
  to run an ordinary shell command outside the sandbox. io owns the PTY and can see that
  prompt, so it can intercept; until it does, the two are not separable.

## The idea

A small, signed catalogue of tools that T4GC has reviewed, installed into io, surfaced to
the person, and exposed to the assistant as MCP servers that io launches.

### What a tool is

A directory with a manifest and an executable. The manifest declares, in the person's words
and in machine-readable form:

- what it does, in one line ("looks up a map background for a set of coordinates");
- what it reaches (`network: tile.openstreetmap.org`), which is the line io shows;
- what it is given (the folder? a named file? only coordinates?);
- what it returns.

The gap between "what it reaches" and what it actually does is what vetting closes. That is
the whole value of the store and it cannot be enforced by io.

### Who vets

T4GC to begin with. The natural second step, and the one that makes this an app store
rather than a bundled toolbox, is an organisation's own IT or data team publishing tools for
their own staff. That wants a signing key per publisher and a trust list in io, and it is
out of scope here.

### What the person sees

The `T4GC tools` card should stop being an unfalsifiable claim. A "what's in the toolbox"
link showing each tool, one line each, and what it reaches. Nothing else on the card changes.

On first use of a tool, the assistant's own approval prompt already asks, per tool, with an
"always allow" that persists. That is the install gesture; io does not need to invent one.
io should replace the raw prompt text with its own wording, because the built-in text
("Allow the t4gc-probe MCP server to run tool net_check?") is not for this audience.

### The first three tools, and why

1. **Map background.** The one the map journey actually needs. Given coordinates, it
   returns a basemap image or a bundled tile set, so a map is a map instead of dots on a
   grid. Reaches one tile host, and only it.
2. **Renderer.** Given a page the assistant wrote, io renders it and returns a screenshot so
   the assistant can see its own work. Reaches nothing. See the caveat below; this one is
   the most valuable and the most delicate.
3. **Geocoder.** Given place names, returns coordinates. The honest example of the risk the
   store exists to manage: it is the most natural thing in the world for an assistant to
   reach for, and doing it casually ships beneficiary locations to a third party.

### The renderer's caveat, which is a hard requirement

The proxy is blind to images. It rewrites strings in a JSON body; a screenshot is base64
that passes through untouched and the leak check cannot see inside it. So a screenshot of
the real dashboard would send real names to the model as pixels, invisibly, with the footer
still saying Protected.

The renderer must therefore **render from tokenised data, never tokenise a rendered image**.
io holds the vault, so it re-applies real-to-code over the page's data, renders that copy,
and screenshots it. The person always sees the real page; the model only ever sees one with
`NAME_001` in the legend.

Three residual leaks to design against:

- values not in the vault (amounts, dates, free text) appear as themselves;
- geometry leaks even when labels do not — a map with coded names still plots real
  coordinates, and a model can read positions off a picture;
- the proxy needs an explicit carve-out for image payloads or it will run every validator
  over megabytes of base64 each turn.

## Open questions

- Whether io intercepts the approval prompt so that a vetted tool call and a shell
  escalation can be answered differently. It owns the PTY, so it can; it is work.
- Whether tools are available in a conversation with no folder, where the wall is looser.
- What happens to a tool's output in the transcript: it crosses the proxy like any other
  tool output, so a geocoder's reply is coded on the way up like everything else.
- Signing and a publisher trust list, when this stops being T4GC-only.

## What this replaces

Nothing yet. Today `T4GC tools` and `Offline` differ only in whether io will open a page for
the person. This proposal is what makes the middle setting worth choosing.
