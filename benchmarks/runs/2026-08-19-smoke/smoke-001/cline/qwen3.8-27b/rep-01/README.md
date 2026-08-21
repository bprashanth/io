# Cline/Qwen smoke run 01

This is harness evidence, not a benchmark result.

The first two attempts failed at authentication with zero model tokens. Cline
ignored provider/model environment variables in its normal CLI path, then
required credentials in its own isolated provider store even when the key was
available as `CLINE_API_KEY`. `cline auth` configured the isolated state and the
third attempt completed.

Turn 1 produced `generated-site/index.html`. The model first exceeded Cline's
recommended 6,000-character editor call limit, recovered by splitting the file,
and completed after 652.7 seconds. Its generated host HTTP server was stopped
after evidence capture.

The live page was served from a resource-capped, read-only container on an
internal Docker network. Host Playwright reached the container's private IP,
opened both viewport sizes, recorded screenshots and errors, and exercised the
year control. All declared turn-1 values and the source label passed. The narrow
table overflowed the 390 px viewport.

Five attempts to send turn 2 with `cline --json --id` failed before model calls.
This matches open Cline issue #10856: JSON resume drops positional and piped
follow-up prompts. The measured runner must use Cline ACP for persistent
multi-turn sessions. Because turns 2 and 3 did not run, this smoke unit is
`invalid`, not a model failure and not an aggregate result.

Cline reported zero cost. The public OpenRouter prices at run time and Cline's
token counters imply an estimated USD 0.08349675 for the successful turn, but
future runners must capture OpenRouter billing before/after or request-level
generation metadata.

