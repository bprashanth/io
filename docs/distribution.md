# Distribution: the build on the USB sticks

Part of [ARCHITECTURE.md](ARCHITECTURE.md). How to prepare the drives is in
`installation/RELEASES.md` and `installation/EVENTS.md`.

**Status, 2026-09-26: decided, not yet built.** The next release is the first to go on the
sticks this way.

## The decision

From the next release, the sticks carry the **thin** build. A person copies their platform's
folder to their laptop and starts io. Scanning for names and places goes to the organisers'
**privacy server**, and people have agreed to that. Nothing large is downloaded.

## The builds

| build | size | first run | scanner |
|---|---|---|---|
| thin (CI default, on every push) | ~200–240 MB | installs python and file readers | privacy server |
| offline (`fat`, opt-in dispatch) | ~2 GB | downloads nothing | on the laptop |

The offline build stays available for rooms with no internet and for anyone who does not want
their text sent to the server.

## What still has to be built

Today a thin first run also installs torch and the on-device model, about 1.9 GB, before io
opens, even though the server is scanned first. io already has the path that skips them: Intel
Macs, which cannot run the model, install only the readers (about 100 MB). The work is to take
that path whenever the privacy server answers at first run, and keep the on-device download as
a choice. Then the drive instructions switch to the thin builds.

## What leaves the laptop

- **During a scan:** the text being scanned goes to the privacy server over HTTPS, through a
  Cloudflare Tunnel to the organisers' machine. Cloudflare terminates the TLS, so the text is
  readable at Cloudflare's edge as well as on the server.
- **Model traffic:** coded, as always. See [tokenization.md](tokenization.md).

## If the server does not answer

io says so and offers the on-device download or pattern matching only (phones, Aadhaar,
emails and the like; no names or places). `IO_SCANNER=local` forces the on-device model;
`IO_PRIVACY_SERVER` points at a different server, such as one on a laptop in the room.
