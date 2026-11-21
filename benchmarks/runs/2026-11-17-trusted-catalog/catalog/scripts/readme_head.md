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
