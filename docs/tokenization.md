# Tokenization: what the model sees

Part of [ARCHITECTURE.md](ARCHITECTURE.md). The full privacy claim is in
[io-codex.md](io-codex.md).

## The claim

**io replaces private values with codes in everything Codex sends to the model provider, and
puts the real values back in what comes back.** The provider sees `NAME_001`, `PLACE_003`,
`PHONE_002`. The person, their files, and the commands Codex runs all work with the real
values.

That claim covers model traffic only. What commands do on the network is the wall's job; see
[sandboxing.md](sandboxing.md).

## Where it happens

One place: io's proxy (`app/io/codex_proxy.py`, with the live vault from
`app/io/service.py`, `IoPolicy`). It listens on `127.0.0.1` on the person's own computer.
io's profile points Codex's model traffic at it and has no other address to fall back to, so
if the proxy is down, Codex fails visibly rather than going direct.

It refuses everything until the person has approved the folder's review.

## Going out

For every string in the JSON body of a request:

1. **Known values** from the folder's vault, longest first and case-insensitive.
2. **Validators** for phones, Aadhaar, emails, account numbers, PAN and similar, on every
   string. A value never seen before gets a new code.
3. **The on-device scanner** for names and places, only on what the person typed and only
   when a folder is sheltered. In a conversation with no folder, typed words are left alone:
   the vault is empty and the person typed them. A typed phone number is still caught by the
   validators. Tool output never goes through the scanner; its files were scanned at review.

Column names are not coded. Each string is transformed once and cached, because Codex
resends the whole history every turn. After transformation, the whole body is checked again
against the vault. If any known value is still there, the request is refused with a 403 and
never sent.

## Coming back

Every string in a JSON reply and every streamed event is restored. When a code is split
across two streamed chunks (`NAME_0` then `01`), the proxy holds the tail until the next chunk
arrives, so it still comes back as the real value. Codes the vault does not know pass through.

Two live-only details, each found by running the app rather than by a test:

- **chatgpt.com streams its answers with no Content-Type header.** The proxy looks at the first
  bytes of the body to recognise a stream. Before that fix, nothing was restored and people
  read `PLACE_003` where a village belonged.
- **A code glued to a literal `\n` in a shell command** was not treated as a code, because it
  had no word boundary. The boundary now allows escape sequences.

## What is refused outright

| request | why |
|---|---|
| a WebSocket upgrade | refused with 426, so Codex falls back to plain streaming the proxy can read |
| OpenAI-hosted plugins and apps | tool arguments could go there |
| analytics | not needed |
| anything not on the allow list | fail closed |
| anything before the folder's review is approved | fail closed |
| a body the proxy cannot read | never forwarded |
| a body that still contains a known value | 403 |

## Pictures

The proxy is blind to images. A picture crosses it as base64 and no check can see inside it.
The proxy passes `data:` URLs through untouched, so a validator does not mistake a run of
digits in the base64 for a phone number and corrupt the picture.

The consequence is a rule: **what a picture shows is decided where it is made.** io's renderer
tool never screenshots the real page. It codes the page's text the way a request is coded,
renders that copy in a window that can load nothing else, and hands the model that picture.
Verified on the laptop: the model saw `NAME_566 / PLACE_003 / PHONE_304` while the person saw
`U. A. Pillai / Karpi / 099433-78529`. Chart images (PNGs) are refused by the renderer,
because their labels are pixels and cannot be coded.

## What it does not cover

- **Values the vault does not hold.** Amounts, dates and free-text notes go as themselves.
  Numbers read off a rendered picture do too.
- **Paths and file names.** Codex tells the model its working folder and file names. A folder
  named after a person names that person.
- **Anything a command sends.** The proxy only sees Codex's model traffic.
- **Web search** runs on the provider's side, from the coded conversation.
- **Token refresh** goes from Codex to OpenAI's sign-in service directly; it carries no
  workspace content.
