# Sanitized runtime evidence

The original Antigravity runtime log is intentionally not copied because its
startup arguments contain ephemeral CSRF credentials. The following facts were
derived from the host log without retaining those credentials:

- At 07:14:00 IST, the stale post-onboarding model state rejected the request:
  `neither PlanModel nor RequestedModel specified. You must specify a valid model.`
- The valid conversation ran from 07:18:18 to 07:28:13 IST and emitted 35
  `Requesting planner` records.
- Antigravity's browser subagent could not install Playwright 1.57.0 for arm64
  because the configured driver URL returned HTTP 404.
- One turn-three tool call referenced a nonexistent placeholder path and was
  retried automatically; the final page and export were still produced.
- The product exposed no per-session token counts or price metadata.

The raw persisted conversation is retained as `session/conversation.pb`; its
SHA-256 is recorded in `run.json`. Credential-pattern scans found no OAuth,
JWT, bearer-token or OpenRouter-key signatures in that file.
