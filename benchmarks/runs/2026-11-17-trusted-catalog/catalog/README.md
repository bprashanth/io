# Idli trusted tools catalog

Software and model files our team has vetted. The Builder picks tools from here for a team's workflows and
installs them with plain pixi. Nothing is fetched from anywhere else at run time.

It lives on the DGX at `/mnt/seagate/silo/idli-catalog/` and is served by the router (`muse_prefix_proxy.py`)
through silo.idli.cc, with the same Cloudflare Access service token as the 9B.

## Addresses

| Method | Path | What |
|---|---|---|
| GET | `/idli/catalog/catalog.json` | The list of tools |
| GET, HEAD | `/idli/catalog/files/<path>` | A mirrored file (model, font or example). Sends Content-Length. No folder listings |
| POST | `/idli/catalog/requests` | Ask for a new tool. JSON, 16 KB at most. Answers `{"ok": true, "id": "req-..."}` |
| GET | `/idli/catalog/requests` | All requests so far, for our team to review |

A request has these fields, all text except `tools_considered` (a list of tool ids or names):
`need` (required), `why`, `platform`, `team` (a short name: letters, digits, space, `.`, `_`, `-`) and
`tools_considered`. Say what is needed in general words. Never put a team's data in a request.

## Folder

- `catalog.json`: the list.
- `files/examples/<id>.py`: one short script per tool that shows its use. Each one ran on the DGX.
- `files/models/...` and `files/fonts/...`: the mirrored files.
- `requests.jsonl`: one request per line, with the time it arrived.
- `README.md`: this page.

## The list

`{"version": 1, "updated": "<time>", "tools": [...]}`. Each tool has:

- `id`, `name`, `for` (what it does, in plain words), `licence`, `vetted` (date) and `cautions` (read them to the
  person before installing).
- `pixi`: `dependencies` (conda-forge) and `pypi-dependencies`, each pinned to one version. Python is 3.11.18.
- `platforms`: where `pixi lock` solved. Only these. A solve is not a run: the tools were run on linux-aarch64 only.
- `models`: the files the tool needs. Each has `name`, `file` (its path under `files/`), `source` (the public
  upstream it came from), `sha256`, `bytes` and `unpack` (`tar`, `zip` or `none`).
- `needs`: `disk_gb`, `ram_gb`, `cores` and `gpu`. Measured on the DGX on tiny inputs: `disk_gb` is the
  environment plus the files (an archive and its unpacked folder both count) plus 10%, `ram_gb` is 1.5 times the
  peak memory. Long recordings and big videos take longer but not much more memory.
- `example`: the path of the example script under `files/`.
- `tags`: words to search by.

## Installing a tool

1. Check the tool lists this computer's platform and that `needs` fit (free disk where tools go, memory, cores).
2. Write a `pixi.toml` with channel `conda-forge`, this platform only, and the tool's `pixi` sections as they are.
   Run `pixi install`.
3. Fetch each file in `models` from `/idli/catalog/files/<file>` into the shared model folder at the same path.
   Check `bytes` and `sha256`. A file already there with the same sha256 is not fetched again: tools share files.
4. `unpack: tar` means: unpack it in the folder that holds it. It holds one folder named like the archive without
   `.tar` (for example `models/whisper-small.tar` gives `models/whisper-small/`). The archive can then be deleted.
5. Run the example inside the environment with `IDLI_FILES` set to the shared model folder:
   `IDLI_FILES=<folder> pixi run python <example> ...`. Each example says its arguments at the top.

Note for the DGX: `/mnt/seagate` is exFAT, which has no symlinks, so a pixi environment cannot be installed
there (it fails on the first package that holds a symlink). Model files can live there. Environments must go on
the root disk.

## Tools

| id | For | Platforms | Files | Disk | RAM | Test on the DGX | Time |
|---|---|---|---|---|---|---|---|
| `media-ffmpeg` | Cut, join and convert video and audio, shrink clips for WhatsApp, and burn in subtitles (Hindi too). | linux-64, linux-aarch64, osx-arm64, win-64 | 0.6 MB | 0.8 GB | 0.5 GB | cut 3.5 s of a 640 px clip and burn Hindi subtitles | 0.31 s |
| `speech-whisper-small` | Type out speech quickly: a first pass over many recordings. Hindi, Marathi, English and more. | linux-64, linux-aarch64, osx-arm64, win-64 | 0.49 GB | 1.6 GB | 1.0 GB | 6.4 s of Hindi speech | 3.54 s |
| `speech-whisper-turbo` | Type out speech carefully, for the recordings that matter. Hindi, Marathi, English and more. | linux-64, linux-aarch64, osx-arm64, win-64 | 1.62 GB | 4.1 GB | 3.0 GB | 6.4 s of Hindi speech | 7.72 s |
| `voice-piper` | Say Hindi or English text out loud into a sound file. Fast, small, works offline. | linux-64, linux-aarch64, osx-arm64, win-64 | 0.13 GB | 0.5 GB | 0.5 GB | one Hindi sentence (6 s of speech) | 0.61 s |
| `voice-kokoro` | Say Hindi or English text out loud in a natural voice. Two women's and two men's Hindi voices. | linux-64, linux-aarch64, osx-arm64, win-64 | 0.35 GB | 0.8 GB | 1.0 GB | one Hindi sentence (5 s of speech) | 2.02 s |
| `translate-nllb` | Translate text between English, Hindi, Marathi and about 200 other languages, on this computer. | linux-64, linux-aarch64, osx-arm64, win-64 | 0.65 GB | 1.9 GB | 2.0 GB | 3 English lines into Hindi | 1.23 s |
| `ocr-tesseract` | Read printed Hindi, Marathi and English from scans and photos, and pull ruled tables into a spreadsheet. | linux-64, linux-aarch64, osx-arm64, win-64 | 40.7 MB | 1.2 GB | 0.5 GB | a 4 by 3 Hindi table into .xlsx | 1.06 s |
| `ocr-rapidocr` | Read Hindi and Marathi text from phone photos of forms and notices, line by line with a confidence. | linux-64, linux-aarch64, osx-arm64, win-64 | 12.8 MB | 0.6 GB | 1.0 GB | 3 lines of Hindi and Marathi | 3.31 s |
| `speech-vad` | Find the stretches of a recording where someone speaks, to cut silences or long pauses. | linux-64, linux-aarch64, osx-arm64, win-64 | 2.3 MB | 0.4 GB | 0.5 GB | 13 s of sound | 0.21 s |
| `sound-classes` | Label each half second of a recording as speech, music, quiet or one of 521 sound types. | linux-64, linux-aarch64, osx-arm64, win-64 | 5.1 MB | 0.4 GB | 0.5 GB | 13 s of sound | 0.23 s |
| `face-blur` | Pixelate faces in photos and videos before sharing. Finds faces without recognising anyone. | linux-64, linux-aarch64, osx-arm64, win-64 | 0.2 MB | 0.9 GB | 0.5 GB | 4 s video, 100 frames at 640 px | 1.17 s |
| `voice-anonymise` | Make a speaker unrecognisable by voice: the words are typed out and said again by a synthetic voice. | linux-64, linux-aarch64, osx-arm64, win-64 | 1.75 GB | 4.9 GB | 3.0 GB | 4.6 s of Hindi speech | 7.94 s |
| `office-files` | Read and write .docx and .xlsx files, and work on tables with pandas. | linux-64, linux-aarch64, osx-arm64, win-64 | none | 0.4 GB | 0.5 GB | write and read a .docx and an .xlsx | 0.53 s |
| `page-server` | Serve a small web page on this computer, for example a voice chatbot page with a microphone button. | linux-64, linux-aarch64, osx-arm64, win-64 | none | 0.2 GB | 0.5 GB | start, load the page, send sound | 0.22 s |

Times are whole runs of the example on the DGX (Grace CPU, 20 cores), including loading the model, with the
network cut. Every tool solved on all four platforms on 2026-11-17.

## Cautions in short

- Non-commercial: `translate-nllb` (NLLB weights CC-BY-NC-4.0) and the Hindi Piper voice in `voice-piper` and
  `voice-anonymise` (CC-BY-NC-SA-4.0). The English Piper voice comes from research-licence data.
- GPL code: ffmpeg (this build), piper-tts, phonemizer and espeak-ng. Fine to install and use. Copying them into
  something we hand out brings GPL terms.
- Converted by us: the NLLB model (from a pickle file to CTranslate2) and YAMNet (from TFLite to ONNX). How is in
  each tool's cautions.
- Privacy tools hide only what they say: `face-blur` hides faces, `voice-anonymise` hides the voice but keeps the
  words. Check results before sharing.

How tools are vetted and how requests are reviewed: `VETTING.md` in the repo at
`benchmarks/runs/2026-11-17-trusted-catalog/catalog/`.
