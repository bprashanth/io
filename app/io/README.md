# io (minimal)

Point io at a folder. It shows what will leave as codes; you correct it by clicking. Then talk.

- Start: `cd app/io && ./install.sh` once, then `./run.sh`. That builds io's own python env
  in `.venv` and caches the scanner in `hf-cache`, using the versions pinned in `pins.json`.
  Full instructions, including Windows: [installation/INSTALL-from-source.md](../../installation/INSTALL-from-source.md).
  A developer with the privacy-shield extension installed can skip the env - io will borrow
  the extension's venv, which carries the same tested scanner (GLiNER, CPU-only).
  Headless: run `service.py 8801` with that venv and open `http://127.0.0.1:8801/`.
- Packaged builds carry their own python and model and need nothing installed; see
  `installation/` for how they are built and what is verified.
- Provider: an OpenRouter API key, or any OpenAI-compatible server address. Kept in memory;
  asked again on restart. Model defaults to `google/gemini-3.7-flash`; change it in settings (⚙).
- The sheet view highlights what the scanner flagged, with the reason under each header.
  Click a column to change it. Decisions are remembered by header signature
  (`~/.config/io/decisions.json`), the vault per folder (`vault-…-local-only.json`), exactly
  like the shield plugin.
- Questions and answers pass through the same vault both ways. A value you type that is coded
  strikes through as you type. Every answer says how many rows left as codes.
- Pages/dashboards: the model writes the page against `window.data`; io pours the real rows in
  locally, so figures are computed in your browser over the true data.

- Text, chat exports and PDFs scan too: the document shows every find highlighted; click to keep.
  The find box shows "27 hits, 0 redacted" with Redact all; terms are remembered per file.
  "hide: names, addresses, account ids" sends those words to the on-device scanner as labels.
- In chat, @ shows the file list; a mentioned question sends only that file.

Engine: `benchmarks/pii/{columns,detect,pseudonymize}.py` and the app's vendored copies - the
privacy-shield modules, unchanged.

## Scripts in this folder

- `install.sh` - one-time setup for running from a git checkout. Builds `.venv` and caches
  the scanner using the versions pinned in `pins.json`. Not needed for a downloaded build.
- `run.sh` - start io from a checkout. Runs `install.sh` first if it has not been run.
- `usb_copy.sh` - put the builds and the event data onto every plugged-in USB stick at once.
  Run it from the root of the repo:

      ./app/io/usb_copy.sh --builds bin        # copy to every stick it finds
      ./app/io/usb_copy.sh --dry-run           # list the drives, write nothing

  It finds drives the kernel reports as removable or hotplug, unpacks each archive once
  into a staging folder and reuses it, then copies to every stick in parallel. Each stick
  gets `insightout/io/` (the unpacked builds, plus any .dmg carried as-is for a Mac to
  open) and `insightout/data/` (the sample data from `simulations/foundation-without/data`).
  Running it again after plugging in more sticks is cheap: it skips whatever is already
  there.
- `privacy_server.py` - runs the scanner for machines that cannot run it themselves. Read
  the notes at the top of that file before starting one: the text sent to it is not
  redacted.
- `room_server.py` - the projector board that collects the blind-comparison votes.
