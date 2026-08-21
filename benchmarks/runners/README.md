# Runner contract

The measured runner has four stages:

1. `prepare` — copy immutable case inputs to an isolated workspace and snapshot
   versions/settings;
2. `agent` — send exact messages in one conversation and retain structured raw
   events plus stdout/stderr;
3. `application` — identify and start the generated website in an ephemeral
   container on a dynamic port;
4. `browser` — open/exercise the live site with Playwright, score it, and write
   `run.json`.

Each stage writes its own status so an incomplete run remains useful evidence.
The orchestrator writes `run.json` last and validates it against
`../schemas/run-record.schema.json`.

```text
runs/<batch>/<case>/<system>/<model>/<rep>/
  run.json
  agent.ndjson
  agent.stderr.txt
  environment.json
  settings.redacted.json
  workspace-files.sha256
  generated-site/
  application/{build.txt,server.txt,container.json}
  browser/{desktop.png,narrow.png,events.json,downloads/}
  grading/{deterministic.json,visual-human.json,
           visual-judge-prompt.txt,visual-judge-response.json}
```

Secrets and browser/auth profiles never belong under `runs/`.

## Split-pipeline development runner

`scripts/run_split_pipeline.py` is a deliberately narrow runner for the event
architecture study. It asks a model only for a JSON analysis plan, validates
and binds that plan, executes it with DuckDB and fills a self-contained page
from trusted computed rows. The model does not author SQL, values, HTML or
JavaScript. The first prototype accepts one CSV; other inputs will use separate
deterministic adapters.

Use an isolated Python environment with DuckDB, pandas and jsonschema. The
runner records the profile, exact planner request, response metadata, validated
plan, result contract, page and complete-row CSV for each turn. Browser evidence
is still mandatory; runner completion by itself is not a benchmark pass.
