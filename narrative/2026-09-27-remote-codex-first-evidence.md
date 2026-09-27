# Moving Codex's workspace to Linux

The [remote experiment](../chronology/2026-09-27T1210-dgx-remote-experiment.md)
establishes a useful boundary: io's terminal transport and explicit file controls
can operate against a separate Linux container. The bundled Codex's command sandbox
works there, including child processes, and two ephemeral containers keep their
workspace and authentication directories separate. This reduces the server command
sandbox problem to a controlled Linux deployment.

It does not yet establish the whole product path. A real user-owned ChatGPT login
and subsequent model-driven CSV conversation remain to be demonstrated. Nor does it
preserve local mode's data-location claim: uploaded copies and OAuth credentials now
live on a trusted server, and this experiment bypasses local tokenisation. The UI
states that distinction explicitly. Moving the privacy proxy and hardening the
container host require their own work before a remote product decision.

Two failures were especially useful. A PTY that displayed output still did not
handle interruption correctly until it became the process's controlling terminal.
A container that restarted still invalidated the client's address when Docker chose
a different published port. The checks now cover both. These are reasons to keep the
laptop drive as a separate acceptance step even after credential-free CI is green.
