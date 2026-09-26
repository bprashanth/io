# Model switching: using another model when ChatGPT runs out

Part of [ARCHITECTURE.md](ARCHITECTURE.md).

**Status, 2026-09-26: mostly planned.** ChatGPT through the person's own sign-in is the only
model a person can use today. A development path to OpenRouter exists. The design below is
being built on the DGX; this page will be updated as parts are measured.

## Today

- The person signs in with ChatGPT. Codex's model traffic goes through io's proxy to
  chatgpt.com, coded on the way out.
- For development, `IO_CODEX_DEV_PROVIDER=1` adds a model provider pointing at the proxy's
  `/dev/v1`, which forwards to OpenRouter. The **same tokenising transforms** apply, so
  OpenRouter sees codes only. Full sessions have been driven this way with an OpenAI model.
- Nothing notices when the ChatGPT allowance is used up.

## One constraint shapes everything

The bundled Codex speaks only OpenAI's **Responses API**. Its own error text says:
`` `wire_api = "chat"` is no longer supported``. Any other model must be offered on a
`/v1/responses` endpoint. OpenRouter offers one. It has been proven with OpenAI models only.

## The plan

**A model control** in the terminal bar, next to the Setting control:

- **ChatGPT**, the person's plan, as the default;
- **OpenRouter**, starting with one smaller, cheaper model.

A local or room server (such as a 27B on the organisers' machine) comes later, in
`proposals/`. It needs a server that speaks the Responses API, or a translator in the proxy.

**Running out of allowance.** The refusal and Codex's own "how much is left" requests both pass
through the proxy, so io can see the allowance run out.

- **Before the person types:** if the allowance is already empty, io says so on the opening
  screen and has the fallback model selected.
- **During a conversation:** Codex cannot suggest anything, because with no allowance the
  model never runs. io shows a line above the terminal, "Your ChatGPT allowance is used up
  until <time>. Switch to <model> to carry on", with a button that switches and resends the
  last message.

io offers the switch; it never makes it silently. A different provider receives the coded
conversation, and that is the person's choice.

## Moving a conversation to another model

A saved Codex thread is mostly plain: every message, tool call and tool output is readable. Only
the old model's hidden reasoning is encrypted, and another provider cannot use it. That gives
three ways to carry on, in order of preference:

1. **Strip the reasoning and resume.** The proxy drops the encrypted reasoning items on their
   way to a non-OpenAI provider, and Codex resumes the same thread with the whole visible
   history. Seamless when it works. The first thing to test.
2. **Start afresh with a handover.** Needed when the thread is too long for the smaller model.
   io starts a new thread and writes a summary of the old one into `AGENTS.md`, which is
   rewritten at every launch and read from the first turn. The summary is built from the plain
   parts of the saved thread, so it does not need the old model, whose allowance may be gone.
   It holds real values, but it reaches the new model only through the proxy, so it is coded
   like everything else.
3. **Start afresh.** The same opening with no summary, if option 2 misbehaves.

When a fresh start is needed, the person is told why, in the terms they will understand:

> You're switching to a smaller model. It can't pick up this conversation exactly where the
> bigger one left off, so we'll start fresh. I can still see what was done in this folder.
> Would you like me to catch up on it first?

## The API key

- **The key never enters Codex's environment.** io's proxy adds it to requests on their way
  out. A command inside the wall can never read it. (The development path today still passes it
  to Codex as `IO_DEV_KEY`; that changes.)
- **Pin OpenRouter to providers that neither store nor train on data.** Codes hold regardless,
  but values outside the vault, such as amounts and notes, reach whoever runs the model.
- **How a person gets a key (decided 2026-09-26).** For testing, a config file on the
  developer's machine. For people, the organisers hand out OpenRouter keys, for example when
  someone's ChatGPT allowance runs out, and the person enters it in io's settings at any time,
  including mid-conversation. No key server, and no key built into the app.

## Costs

OpenRouter bills per token. Codex requests measured at roughly 7k to 35k tokens each, and the
whole history is resent every turn, so long conversations add up.
