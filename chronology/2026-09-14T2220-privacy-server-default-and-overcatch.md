# 2026-09-14 22:20 - Scanner on the DGX by default; the over-marking in chat logs measured and cut

Asked for: point the scanner at the DGX by default (local install kept behind a flag),
remove the over-catching in non-spreadsheet files, test both, and write it down.

## Where the time goes (measured on this DGX, CPU vs GPU)

| | CPU (laptop-class path) | GPU (`.venv-pii`, cu130) |
|---|---|---|
| model load | 3.5 s | 3.4 s |
| one 2 KB chunk | 370 ms | 34 ms |
| 200 short cells, one call each | ~7.5 s (1.5 s per 40) | 770 ms |
| 200 short cells, one batched call | - | 136 ms |
| the six planted-PII fixtures, whole folder scan through io | 10.2 s | **0.64 s** via the server |

Two engine changes on the way: `make_gliner` now batches the chunks of a long text into one
call, and `IO_SCANNER_DEVICE=cuda` moves the model to the GPU (laptops stay on cpu). The
DGX needed one workaround: torch 2.13's triton kernels compile a helper against `Python.h`,
which the system python lacks; `CPATH=~/.local/share/io/runtime/include/python3.12` (the
headers from a thin-install python) makes the build pass.

## The default is now the privacy server

`service.py`: `DEFAULT_PRIVACY_SERVER = http://100.82.28.38:8899` (the DGX on the tailnet;
`IO_PRIVACY_SERVER` overrides, the settings gear overrides per session). `IO_SCANNER`
picks the order: `auto` (server, then the on-device model if installed, then patterns),
`local`, `server`, `regex`. The warm-up call has a 4 s timeout so an unreachable server
costs four seconds at startup, not a hang. `/api/scanner` reports `mode`, `server_url`,
`server_error`, `order`; the confirm dialog says "scanned on the privacy server" instead
of "on this laptop" when that is where it goes. The on-device install (`install.sh`,
`bootstrap.js`, the fat packs) is untouched; it is no longer the first choice.

The server is running here now, started by hand (a systemd unit and a Cloudflare name are
for after the discussion):

    cd app/io && CPATH=~/.local/share/io/runtime/include/python3.12 IO_SCANNER_DEVICE=cuda \
      HF_HOME=$PWD/hf-cache HF_HUB_OFFLINE=1 setsid ../../.venv-pii/bin/python privacy_server.py 8899 \
      > ~/.local/share/io-privacy-server/server.log 2>&1 &

Verified: a service started with no flags picks `mode: server`, scans the fixture folder
in 0.64 s, and the numbers match the local run exactly (same engine, same rules).

## Over-marking: what it was, what it is

`benchmarks/runs/2026-09-14-io-codex/overcatch/measure.py` scans
`benchmarks/t0/text-fixtures/` (the set the doc scanner was accepted on, 2026-08-25) and
counts, per file, planted mentions covered, total spans, and spans that touch no planted
value ("over-marks"), by label.

| run | covered | spans | over-marks |
|---|---|---|---|
| before | 497/497 | 1289 | 792 |
| no title-case pass, propagate names only | 497/497 | 937 | 440 |
| + dates only with a birth-context word | 497/497 | 637 | 140 |
| + propagate only full names or confident hits | 497/497 | **608** | **111** |

Recall never moved. What the 792 were: **chat timestamps and log dates** flagged as birth
dates by the regex validator (260 in the 260-line WhatsApp export, 40 in the helpline log);
the **title-cased second model pass** ("Bhej Sakta Hai"); **propagation** turning one wrong
hit into a code on every line ("sabko" x27, and "borewell" as a PLACE in today's Codex
run); and place names (Bhor, Pune, Hyderabad). Of the 111 left, 70 are real place names
(the shield hides villages on purpose; "Hyderabad buyer" is the trade), 25 are the model's
own remaining hits on Hindi words in the chat, 10 are ages.

Rules now, in `make_text_v2` (documents only; the column rules are unchanged): one model
pass; a `dob` span survives only within 40 characters of dob / born / birth / age / janm /
जन्म, so message timestamps and visit dates stay as they are; a name is propagated to its
other occurrences only when it is two or more words or the model scored it at 0.8 or above;
village and address spans are never propagated. The rule applies to spans from the server
too (it runs its own regex pass), which the first attempt missed - the via-server run still
showed the 300 dates until the filter moved after the model call.

## Left open

- GPS precision (two decimals, about a kilometre) is code, not the model; a setting if wanted.
- Tables: the fast path for clean spreadsheets (validators + header words + name shape,
  model only on free-text columns) is designed, not built.
- Consent for the server at an event: the confirm dialog now says where the scan happens;
  the consent screen text still describes the failure case only.
