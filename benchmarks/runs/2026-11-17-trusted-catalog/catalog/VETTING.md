# Vetting the trusted tools catalog

The catalog is the list of software and model files the Builder may install for a team. Everything in it was
checked by our team first. This page says how a tool gets in and how requests for new tools are handled.

## Adding a tool

1. **Licence.** Read the licence of the code and of every model file, including the data a model was trained on
   (a voice's model card, for example). Open licences only. Non-commercial or research-only terms go into
   `cautions` in plain words.
2. **Source.** Download each model from its public upstream: a pinned Hugging Face commit, a GitHub tag or commit,
   or the publisher's release URL. Record the URL. Where upstream publishes a sha256 (Hugging Face LFS files,
   RapidOCR's model list), check it. Otherwise record the sha256 we got.
3. **Format.** Prefer ONNX, safetensors or CTranslate2. If upstream has only a pickle file
   (`pytorch_model.bin`), convert it once on our server with a safe loader (`torch.load(weights_only=True)`) and
   ship only the converted files. Say so in `cautions`.
4. **Nothing fetched at run time.** Every file the tool needs is mirrored under `files/`. Run the example with the
   network cut (`bwrap --dev-bind / / --unshare-net`) to prove it.
5. **Pins.** Write a `pixi.toml` with Python 3.11 from conda-forge and PyPI only where conda-forge lacks a
   package. Pin every listed package to an exact version (`==x.y.z`).
6. **Platforms.** Run `pixi lock` for each of linux-64, linux-aarch64, osx-arm64 and win-64 on its own. List
   only the platforms that solved. A solve is not a run: only linux-aarch64 (the DGX) is run.
7. **Example.** Write a short script that shows the tool's real use on tiny inputs we make ourselves (speech
   from a voice tool, text drawn into an image, a public-domain photo). It must run from the pins alone.
8. **Needs.** Install from the pins in an empty folder, fetch the files through the router, run the example,
   and record the environment size, file size, peak memory and time. `disk_gb` is environment plus files (an
   archive and its unpacked folder both count) plus 10%. `ram_gb` is 1.5 times the measured peak.
9. **Add the entry** to `catalog.json` with `vetted` set to the date, and copy the catalog and examples into the
   repo (`benchmarks/runs/2026-11-17-trusted-catalog/catalog/`).

To change a version, repeat steps 5 to 8. To remove a tool, delete its entry. Leave its files until no other
entry names them.

## Reviewing requests

The Builder sends `POST /idli/catalog/requests` when nothing in the catalog fits. A request holds what is
needed and why in general words, the platform, a short team name and the tools it considered. It holds no team
data. Each request is one line in `requests.jsonl` with a server timestamp and an id.

To review: `GET /idli/catalog/requests` (or read `requests.jsonl` on silo), then for each request:
- **Already covered?** If a catalog tool does it, reply through the team's usual contact and say which tool.
- **Worth adding?** Several teams or one clear need. Look for an open tool that runs on a laptop CPU.
- **Vet it** with the steps above, add it, and note the request id in the commit message.
- **Not possible?** Say why in plain words: no open licence, needs a GPU, or no build for the team's platform.

Nothing in a request is run or fetched automatically. Requests are text for people to read.
