# Pixi and the trusted catalog: refinements

Context:
- [PAGES_AND_TOOLS.md](../../../narrative/PAGES_AND_TOOLS.md), "Decision 2026-11-17" and "As built";
- the results in `benchmarks/runs/2026-11-17-trusted-catalog/README.md` (DGX W1 to W10, laptop W1, W4 and W6, CI).

Found during the POC, roughly in order of how much they bite.

1. **Model paths.** The catalog examples read `$IDLI_FILES/models/<file>`. Installs store models at
   `<home>/models/<sha16>/<name>`, and nothing sets `IDLI_FILES`. Builders found `$IDLI_MODEL_PATHS` themselves, at
   a few extra tool calls each. Pick one layout, and make the examples and the run env agree.
2. **Sizes disagree.** The install prompt shows the catalog estimate. The page showed what's on disk, and the disk
   dropped by something else again. A model that is already shared is counted in full. Show one number: what this
   install will add to the disk.
3. **Removing one tool doesn't shrink the environment.** The team's `pixi.toml` is rewritten, but its packages stay
   until the next install. Re-run `pixi install` (or prune) after a removal.
4. **One environment per team.** Two teams with Whisper each hold about 1 GB of the same packages (pixi's cache
   helps installs, not disk). Consider one environment per catalog tool set, shared by the teams using it.
5. **The DGX tools home is split.** `/mnt/seagate` is exFAT (no symlinks), so environments sit on the root disk.
   A mounted ext4 image on the Seagate (root, once) would put everything on the big disk.
6. **`[system-requirements]` is deprecated in pixi 0.84** in favour of per-platform entries. It's only a warning;
   move the Whisper tools' `macos = "14.0"` to the new form. Decide what Macs older than 14 get (a different
   Whisper build, or "not on this Mac").
7. **Conflicting pins between tools.** The union of a team's tools can conflict. Today it reports this. Vet tools
   in groups that are known to install together, and test the common groups in CI.
8. **Catalog updates.** No flow yet for a new version of a tool: tell the teams using it, reinstall with the
   person's yes, and keep the old one until the new one passes the team's tests.
9. **Catalog integrity.** It is trusted because it comes over silo (TLS plus Cloudflare Access). Sign
   `catalog.json`, check the signature in `catalog.py`, and keep sha256 on every file.
10. **Requests.** `requests.jsonl` on silo has no review page. Add a vetting checklist (licence, weights format,
    run-time downloads, platforms solved, example passes offline) and a way to tell the asking team it's ready.
11. **Tool defaults found while vetting:**
    - Tesseract: `hin+mar+eng` misreads English digits, so use `eng` for numbers;
    - Tesseract tables need `configs/hocr`;
    - RapidOCR's line-turning step flips Devanagari;
    - Hindi subtitles need ASS with `shaping=complex`;
    - the Hindi Piper voice is non-commercial.

    Put these in each tool's `example` and `cautions`, as now, and in the Builder's catalog view.
12. **Resource checks.** The memory check was never exercised (W10 faked the disk with a tmpfs). Add
    `IDLI_FAKE_FREE_GB` and `IDLI_FAKE_RAM_GB` for tests. Count what a run needs, not only the install (Whisper turbo
    on CPU needs about 4 GB of RAM while running).
13. **Offline at run time on Mac and Windows** (no wall there, for the POC). Set `HF_HUB_OFFLINE=1` and
    `TRANSFORMERS_OFFLINE=1`, and check pages bind 127.0.0.1. Done in part; add a test per platform in CI.
14. **CI.** `test_tools_page_api` needs pandas and duckdb in the CI job. Run CI on a schedule, so upstream
    breakage (a yanked wheel, a new macOS image) shows up before a person meets it.
