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
