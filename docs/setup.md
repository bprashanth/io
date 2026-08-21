# Benchmark setup

## Host

The initial runner host is Ubuntu 24.04 on ARM64. Both agent CLIs and generated
websites should run in disposable containers, with separate containers for the
agent and its application. API credentials remain outside case and run
directories.

Required commands are `agy`, `cline`, `docker`, `playwright` with Chromium,
`python3`, `jq`, and `git`. Record versions in each run rather than relying on
this page. A measured batch pins versions for the whole batch.

## Authentication

Antigravity supports SSH authentication. Start `agy`, open the printed URL on a
local computer, sign in, and paste the returned code into the SSH terminal.

Cline uses the OpenRouter key in
`~/.config/idlisseus/openrouter.json`. Scripts must extract the key at runtime
without printing it, putting it in command arguments visible to process listings,
or copying it into benchmark output. Prefer a short-lived environment variable
and unset it after the command.

## Run isolation

For every case, system, model and repetition:

1. Copy case inputs to a fresh workspace outside every other run.
2. Start a per-run agent container with only that workspace, minimal credential
   mounts, and run-specific client state. Start a fresh Antigravity conversation
   or Cline ACP session and record its resolved model before the first prompt.
3. Execute the agent with structured output and save stdout/stderr separately.
4. Hash the resulting workspace.
5. Resolve how to start the generated application without modifying it.
6. Build/start it in a second disposable container without the Docker socket.
7. Open it with Playwright on a dynamically assigned localhost port.
8. Save screenshots, errors, downloads, health information and scores.
9. Stop/remove the application container.
10. Write `run.json` last with a truthful final status.

Do not reuse dependency directories or generated source between competitors.
A shared read-only package cache may be introduced only after checking it for
workspace or model-specific state.

Installation and smoke-test outcomes belong in chronology entries, so failed
attempts and version changes remain visible.

The first smoke proved that Antigravity's native `--sandbox` and a temporary
working directory are not sufficient isolation on this host: an attempted run
searched outside its workspace. Until outer agent containers are green, host
runs are diagnostic only and must include an observed-path audit.
