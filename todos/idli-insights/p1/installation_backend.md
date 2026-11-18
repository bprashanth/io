# The installation backend: flesh it out

Context:
- [PAGES_AND_TOOLS.md](../../../narrative/PAGES_AND_TOOLS.md), "Decision 2026-11-17: a catalog of trusted tools"
  and "As built". It covers the pixi installs, the vetted catalog on silo, the tools home and the walls.
- The refinements found in the POC are in [pixi_catalog_refinements.md](pixi_catalog_refinements.md).
- This todo is the backend as a service, not a list of fixes.

## What exists

- **The catalog on silo** (`/mnt/seagate/silo/idli-catalog/`, served by `muse_prefix_proxy.py`):
  `GET /idli/catalog/catalog.json`, `GET /idli/catalog/files/<path>`, and `POST /idli/catalog/requests`, which
  appends to `requests.jsonl`.
- **14 vetted tools**, pinned and solved for linux-64, linux-aarch64, osx-arm64 and win-64. CI is green on
  macOS, Windows and Linux.
- **The client:** `lib/catalog.py` (fetch, platform, resources, check, request) and `lib/toolhome.py` (tools home,
  `installs.json`, shared models, purge).

## To build

1. **Vetting workflow.** A review page for `requests.jsonl` (owner only).
   - Checklist: licence, weights format (no pickle), downloads at run time, platforms solved, example passes
     offline, sizes.
   - A script that takes a candidate from request to catalog entry: solve the four platforms, mirror files with
     sha256, run the example offline, write the entry.
   - Tell the asking team when it's ready.
2. **Catalog as data with history:**
   - versioned `catalog.json` (each tool has a version and a changelog);
   - a signed manifest (key held by the owner, checked in `catalog.py`);
   - rollback to the previous catalog.
3. **Mirrors:**
   - a package mirror or cache for the pinned conda-forge and PyPI files, so installs don't depend on upstream
     staying up;
   - model files already mirror to silo.
   - Plan the size (the Seagate has 3.1 TB free).
4. **Delivery to laptops:**
   - resumable downloads for big model files, with a progress report to the person;
   - a bandwidth-friendly path for slow office connections (a local LAN cache);
   - Cloudflare limits on the silo path.
5. **Updates:** when a tool's version changes, tell the teams using it, reinstall with the person's yes, keep the
   old one until the team's tests pass, then remove it.
6. **Ownership and access:**
   - who can add tools (the owner, then trusted vetters);
   - per-org catalogs later (an org's own approved list on top of Idli's);
   - audit of who installed what, where (from `installs.json` reports, with no personal data).
7. **Platform coverage:** decide Macs older than 14 (Whisper needs 14), Windows ARM, and Linux distros without
   glibc 2.28. Add CI on a schedule for the common tool groups.
8. **Where it runs:** keep it on silo for the POC. Write down what moves if silo is down: installs fail with a plain
   message, and already-installed tools keep working.
