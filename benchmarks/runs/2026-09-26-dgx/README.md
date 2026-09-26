# DGX verification, 2026-09-26

Synthetic-only evidence for the [implementation entry](../../../chronology/2026-09-26T2220-dgx-six-feature-implementation.md).
PNG screenshots remain local and are ignored by git.

- `drive.js` / `drive-results.json`: actual Electron, live OpenRouter, public/private
  attachment, acknowledgment, thread continuity, key removal/replacement and fresh handover.
- `quota_drive.js` / `quota-results.json`: fixture ChatGPT quota metadata/refusal followed
  by live OpenRouter. It asserts that a response request reached the fixture before retry.
- `resume_probe.py` / `resume-results.json`: live bundled Codex resume with synthetic foreign
  ciphertext, AGENTS reread and a Python CSV calculation under the wall.
- `thin-results.json`: fresh install directory, pip cache disabled, elapsed time, disk bytes
  and complete installed package list. Existing DGX OS/network; not a clean OS benchmark.
- `composer-results.json`: measured textarea and overlay scrolling after pasted long text.

From repository root, with the existing `installation/smoke` Playwright installation:

```
xvfb-run -a node benchmarks/runs/2026-09-26-dgx/drive.js
xvfb-run -a node benchmarks/runs/2026-09-26-dgx/quota_drive.js
app/io/.venv/bin/python benchmarks/runs/2026-09-26-dgx/resume_probe.py
```

These are DGX investigation scripts, not portable CI. They use separate dated test data
roots, the installed runtime and the user's locally configured OpenRouter key. They perform
live provider requests and incur usage. They never print the key. The native file picker is
stubbed for automation. Quota/auth fixtures are synthetic; no real ChatGPT quota was exhausted.
