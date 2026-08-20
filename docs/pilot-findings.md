# First screening pilot findings

The first complete five-turn pair suggests that Qwen 3.8 27B is a credible
candidate, but it is not a benchmark result. It was used to calibrate the
download checker and browser network policy, so both runs are explicitly
excluded from measured aggregates.

| Pilot observation | Antigravity default | Cline + Qwen 3.8 27B |
|---|---:|---:|
| Preliminary weighted score | 88/100 | 86/100 |
| Elapsed time | 346.363 s | 970.407 s |
| Materially wrong displayed number | No | No |
| Correct requested CSV delivered | Yes | Yes |
| Unsupported interpretation | Invented performance bands | None found |
| Final follow-up state carried into page | No | No |
| Narrow viewport overflow | 557 px | 231 px |
| Offline-resilient page | No | Yes |

The two-point gap is inside the strict seven-point non-inferiority margin, and
Qwen's correctness and uncertainty handling were at least as good in this
pilot. That is promising, not conclusive: one known case, one repetition and
unblinded scoring cannot establish equivalence.

The main concern is the product harness rather than raw output quality. Cline
made 37 exact-model requests and spent 970 seconds, largely because it wrote
and repeatedly reran its own browser-like tests. This is retained as a measured
time/cost signal in the product track. A neutral or DeepSeek harness may later
be used as a diagnostic to determine whether the latency and incomplete
follow-up-page state are Cline-specific, but cannot support a Cline-equivalence
claim.

The pilot caused two protocol clarifications before the measured freeze:

1. A correct comparison CSV may be long or sensibly wide if it preserves every
   required observation and required provenance fields.
2. Browser scoring uses workshop-online as the primary condition, with every
   external request recorded. Offline resilience is separately reported, since
   public CDNs are realistic in the intended online workshop but matter for
   eventual local deployment.

## Evidence

- [Antigravity run](../benchmarks/runs/2026-08-20-screening-pilot/dev-csv-health-001/antigravity/default/rep-01/)
- [Qwen run](../benchmarks/runs/2026-08-20-screening-pilot/dev-csv-health-001/cline/qwen3.8-27b-nitro-xhigh/rep-01/)
- [benchmark design](../benchmarks/DESIGN.md)
