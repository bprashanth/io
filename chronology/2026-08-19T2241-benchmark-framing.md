# We changed the benchmark from screenshot generation to NGO data work

The first sketch proposed 100 LLM-generated CSVs, one prompt per dataset, two
desktop/CLI runners, and screenshot grading. That would have been easy to scale
but weak evidence. It had no dependable numerical oracle, represented students
rather than NGO staff, and did not measure the follow-up conversation that is
the main use case.

We now frame the question as: what is the smallest locally deployable model
that lets Cline match or beat untouched default Antigravity for non-technical
NGO data-dashboard work?

The benchmark will use a smaller checked case bank with CSV, Excel, PDF and web
discovery tasks. A case is an ordered conversation: make a website, filter it,
compare districts or years, explain without guessing, add citations, and make a
download. Exact input bytes, messages and answer keys will be retained so the
hosted winner can later be replayed against the same model running locally.

The initial candidate is `qwen/qwen3.8-27b` through OpenRouter. If it passes we
move smaller; if it fails we move larger through a predeclared list. The 80B and
122B examples discussed are from different Qwen generations and architectures,
so we will not treat parameter count as a clean scaling experiment.

We chose hybrid isolation. The official `agy` and Cline CLIs stay on the host so
SSH OAuth, ARM64 binaries and their own sandboxes work. Each run gets a fresh
workspace and isolated client state. Generated application code is opened and
tested inside a disposable container that cannot see sibling runs. Full CLI
containers remain an option if host isolation proves insufficient, but they add
keyring/OAuth and nested-sandbox complications at the start.

No benchmark result exists yet. The current `smoke-001` case is only for proving
installation, multi-turn runners, application launch, Playwright screenshots,
downloads and evidence capture. It must not appear in the final aggregate.

## Evidence

- [benchmark plan](../docs/benchmark-plan.md)
- [measured design](../benchmarks/DESIGN.md)
- [scoring rules](../benchmarks/config/scoring.json)
- [model ladder](../benchmarks/config/model-ladder.json)
- [smoke case](../benchmarks/cases/smoke-001/case.json)
- [run record schema](../benchmarks/schemas/run-record.schema.json)
