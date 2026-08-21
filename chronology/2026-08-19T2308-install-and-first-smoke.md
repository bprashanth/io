# The tools installed, and the first Cline smoke exposed a resume bug

We installed the official ARM64 CLIs on the Ubuntu runner: Antigravity `1.1.15`
and Cline `3.0.55`. Cline's npm installer needed a current Node, so Node
`24.19.0` was installed under the user's local directory. Playwright `1.61.0`
already worked once its ARM64 Chromium 149 payload was present. Docker 29.2.1
was already available.

The first Cline attempts were useful failures. Normal Cline CLI execution did
not honour `CLINE_PROVIDER` and `CLINE_MODEL`; it fell back to the Cline provider
and failed authentication with zero model tokens. Explicit provider/model flags
selected Qwen but Cline still required the OpenRouter key in its isolated
provider store. Running Cline's official `auth` command against that isolated
state fixed the authentication path.

The successful first turn used `qwen/qwen3.8-27b`. It made a correct, clean
static dashboard from the six-row smoke CSV. It initially tried a 7,787-character
editor write, which Cline rejected because it exceeded the recommended 6,000
characters. The model recovered by splitting the edit. Cline reported 331,447
input tokens, 318,208 cache-read tokens, 19,259 output tokens and 652.7 seconds.
It also reported zero cost. Applying the public OpenRouter prices to those
counters gives an estimate of USD 0.08350, but this is not provider-billed cost.

We opened the generated page through a resource-capped read-only container on an
internal Docker network. Playwright got HTTP 200 with no console, page or failed
request errors. Both years' coverage values and the source label matched the
oracle. Desktop visual quality was good. At a 390 px viewport, the details table
extended 89 px beyond the viewport, confirming that a source-only or desktop-only
check would have missed a real visual defect. The preliminary unblinded visual
score was 7.42/10.

The complete smoke conversation did not run. Cline `--json --id` discarded the
follow-up prompt in every positional and piped form we tried. This reproduces
open upstream issue #10856. It happened before a model call, so it is a runner
failure rather than a Qwen failure. The run is marked `invalid`, and the measured
multi-turn runner will use Cline's ACP interface instead of JSON resume.

Antigravity was installed but still required the human SSH URL/code login when
this entry was written. No Antigravity model run had happened yet.

## Evidence

- [smoke run notes](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/README.md)
- [run record](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/run.json)
- [raw successful turn](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/agent-turn-01-retry-02.ndjson)
- [desktop screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/browser/desktop.png)
- [narrow screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/browser/narrow.png)
- [deterministic browser checks](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/grading/deterministic-turn-01.json)
- [visual review](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-01/grading/visual-human.json)
- [browser checker](../benchmarks/scripts/check_smoke_001.py)
