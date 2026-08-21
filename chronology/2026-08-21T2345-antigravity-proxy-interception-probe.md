# Antigravity traffic can be intercepted locally without TLS tricks

Probe for `proposals/pii_antigravity.md`. Antigravity's language server honours
a `CLOUD_CODE_URL` environment variable (log line: "Overriding
CloudCodeServerURL via CLOUD_CODE_URL"). With it pointed at a plain-HTTP local
reverse proxy (`benchmarks/pii/agy_stream_proxy.py`, forwarding to
`daily-cloudcode-pa.googleapis.com`), one headless `agy -p` turn that read a
two-row CSV completed normally. Observations that shape the redactor design:

- Endpoint is `v1internal:streamGenerateContent?alt=sse`, JSON body
  `{project, requestId, request:{contents, systemInstruction, tools...}, model}`;
  not the public Gemini API shape the proposal assumed.
- Request bodies are chunked; responses are SSE. A buffering proxy hangs the IDE.
- One trivial turn made 7 model calls (1 title + 6 agent steps), each
  resending the whole conversation (60-70 KB, ~14-16k tokens). A redactor must
  cache per-part so GLiNER runs only on new text.
- File contents reach the model inside `functionResponse` parts (with line
  numbers) and `run_command` outputs; user prompts inside `<USER_REQUEST>`.
  All are redactable text fields. `thoughtSignature` blobs must pass untouched.
- Responses split names across chunks ("file:///tmp/cla" + "ude-..."), so
  rehydration needs a hold-back buffer.
- The agent freely ran `find /home/beeps -name people.csv`; a proxy does not
  confine file access. Sheltered mode needs `--sandbox`/workspace trust too.

Traffic log kept in the session scratchpad only (contains the proprietary
system prompt and project id); not added to the repository.
