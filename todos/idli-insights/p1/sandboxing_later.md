# Sandboxing team tools properly (after the catalog POC)

Context:
- [PAGES_AND_TOOLS.md](../../../narrative/PAGES_AND_TOOLS.md) has the full discussion and evidence.
- For the POC (decided 2026-11-17), tools come only from Idli's vetted catalog on silo.
- They install with plain pixi on Mac and Windows. Linux keeps the bwrap install and run walls.
- This todo is what has to be true before a team can add software we haven't vetted, or before we promise
  "nothing leaves this computer" on Mac and Windows.

## What we know

- **Linux:** done.
  - The bwrap install wall (an egress proxy to package hosts only, every host logged) and the run wall (no
    network, inputs read-only, one output folder, an optional door to the 9B) are built.
  - The attacks were tested: a wrong sha256, other hosts, plain HTTP, a raw socket, home folders. All refused.
- **Native Windows sandboxes are not ready** (2026-09-27 io/Codex CI, Windows Server, admin accounts):
  - Codex's elevated sandbox let processes reach services on the same machine, and sometimes failed to launch.
  - MXC/PSEC was unavailable on the CI images. Microsoft says not to treat it as a security boundary yet.
  - Antigravity's Windows sandbox uses the same PSEC/AppContainer technology, and only on Windows 11 24H2 with the
    August 2026 update or later.
- **Claude Code** doesn't sandbox on native Windows at all. It needs WSL2, where it uses bwrap plus a proxy (our
  design).
- **Mac:** Seatbelt is mature. Claude Code's open-source `sandbox-runtime` and Antigravity both use it.
- **Packages don't need Linux:** 11 of 12 test stacks solve for win-64 and osx-arm64. The wall is the reason for
  Linux, not the packages.
- **Which recipes need a wall** (PAGES_AND_TOOLS.md, "How much isolation each recipe needs"):
  - anything with faces or voices;
  - pickle weights (NLLB's `pytorch_model.bin`);
  - downloads at run time (RapidOCR from modelscope.cn, Hugging Face by default);
  - pages that listen.
- **Local Kubernetes** (kind, minikube, k3s, Rancher Desktop) is a VM plus 0.5 to 1 GB of RAM, with no better
  isolation. Not worth it.
- **The DGX per-user container** (io.idli.cc V1 gateway) works in prototype.
  - It needs a person's Access sign-in, or a gateway change to accept the silo service token.
  - Files over 100 MB need chunked uploads through Cloudflare.

## To do, in order

1. **WSL2 on a real Windows 11 laptop, standard account.**
   - Count admin prompts, reboots and minutes from a fresh machine.
   - Run `tests/test_stacks.py` inside the imported image, wall attacks included.
   - Check that CUDA works.
2. **A Mac wall with Seatbelt:**
   - try `sandbox-runtime`, or our own profile, around a native osx-arm64 pixi env;
   - the same attack list as Linux: no network except the 9B door, inputs read-only, home hidden.
3. **Run-time hardening that needs no wall, for all platforms now:**
   - `HF_HUB_OFFLINE=1` and similar offline variables;
   - pages bound to 127.0.0.1 only, checked at start;
   - catalog weights in safetensors or ONNX, never pickle;
   - a clean environment with no keys.
4. **Risk tiers:** low-risk catalog tools run unwalled; the rest need a wall, or the DGX where no wall is
   available. Record the tier in each catalog entry.
5. **The DGX fallback:**
   - the gateway accepts the silo token, or a sign-in per person;
   - chunked uploads, quotas and backups;
   - an explicit consent line: "Runs on your team's server".
6. **Re-check native Windows sandboxing** (PSEC/MXC) when Microsoft calls it a boundary, with the unchanged
   conformance suite.
7. **Only after 1 to 5:** let teams add software outside the catalog again, inside the wall, with the person's
   yes (the overnight 2026-11-17 design).
