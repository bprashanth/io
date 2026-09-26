# Distribution: the build on the USB sticks

Part of [ARCHITECTURE.md](ARCHITECTURE.md). How to prepare the drives is in
`installation/RELEASES.md` and `installation/EVENTS.md`.

**Status, 2026-09-26: implemented; Linux arm64 first-run and packaged smoke tested on the DGX.** The next release is the first to go on the sticks this way.

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

## First-run selection and measurement

Thin setup probes the privacy server and installs only Python and the file readers.
It writes an honest marker saying the local scanner was not downloaded. If the
server is unavailable, the app offers another server, the on-device download, or
pattern matching. `IO_SCANNER=local` explicitly installs the local model even after
a readers-only setup. The build-time `bootstrap.js --dest` command still makes a
full offline payload; thin setup and payload baking are deliberately distinct.

On the DGX (Linux arm64), a new runtime directory with pip caching disabled took
**19.8 seconds**, occupying **475 MB**. It downloaded the 84 MB standalone Python
archive and file-reader wheels, **no torch and no model weights**. pandas,
openpyxl and matplotlib import; a synthetic name/place/phone scan succeeded through
the privacy server. The unavailable-server screen and pattern-only choice were
also driven in Electron. This is an empty-install measurement on an existing DGX,
not a reimaged participant laptop or a measurement of venue Wi-Fi.

## What leaves the laptop

- **During a scan:** the text being scanned goes to the privacy server over HTTPS, through a
  Cloudflare Tunnel to the organisers' machine. Cloudflare terminates the TLS, so the text is
  readable at Cloudflare's edge as well as on the server.
- **Model traffic:** coded, as always. See [tokenization.md](tokenization.md).

## If the server does not answer

io says so and offers the on-device download or pattern matching only (phones, Aadhaar,
emails and the like; no names or places). `IO_SCANNER=local` forces the on-device model;
`IO_PRIVACY_SERVER` points at a different server, such as one on a laptop in the room.
