# 2026-09-01 09:00 - Catch-up entry: compare kit, simulations, packaging specs, hive idea, DS4 night

Work done 08-26 to 08-28 that shipped in commits but had no chronology entry.

## The compare kit grew into the event instrument

After the blind fanout landed (see 2026-08-27T0300), three UX rounds driven by the user:
preview chips + a spacious markdown reading panel (hand-rolled renderer, no libraries);
whys as a straight vertical list under full-width buttons - choose: more correct / written
better / citations / time-tokens less / not sure; all-bad: wrong answers / bad writing /
time-tokens high; both with an "optional: why.." free-text line. Time and token counts are
subtext on every blind chip (cost as a visible voting axis). A one-file room board
(`app/io/room_server.py`): every laptop pushes votes fire-and-forget, the projector shows
the live blind tally with per-model avg time/tokens and a why column. Verified live; the
board caught its own first bug (% formatting) and a data one (open-data's annual summary
contradicts its own CSV - kept deliberately as a grounding-vs-echoing demo beat).

## simulations/ became the handoff surface

Ten packets in the user's plain style (survey question, data, suggested questions,
answers, results, verification), including three graded-corpus orgs with data copied in
(asha-kiran, sunrise-shiksha, krishi-jal-vikas), chats-and-documents, open-data,
graded-corpus (40 questions with written answers - the model-comparison packet) and
adversarial-pii (try to beat the shield). `analyze_compare_log.py` turns vote logs into
the per-task preference table offline - no classifier at vote time.

## Packaging specs

`installation/{windows,linux,mac}.md` + `AGENT_PROMPT.md`: one double-click artifact per
platform, embeddable/standalone python, thin + fat (pre-baked, offline) variants, one
build pipeline, CI smoke benches. Handed to the packaging agent (its own entries:
2026-08-27T1400 onward).

## Hive mind proposal

`proposals/hive_mind.md`: ten focused 9Bs plus a planner vs one 27B, blind-testable as a
fourth anonymous card. Open questions listed; discussion pending.

## The DS4 night (full data: benchmarks/runs/2026-08-27-ds4-ssd/NOTES.md)

DeepSeek-V4-Flash 670B MoE (81 GiB Q2 imatrix) via ds4 SSD streaming, simulating the
32 GB Mac budget. Streaming from a spinning USB drive: DNF - 30 minutes, zero tokens,
drive pegged (experts are ~6.75 MiB random reads). Internal NVMe floor on this contended
GB10: 1.44 tok/s. Planner eval: 48/48 valid tool calls, evidence-driven follow-ups, one
fully correct multi-source answer - but 2/3 tasks over-explored past the step budget, and
minutes per cycle. Fallback measured on the same spinning drive: Qwen3.8-27B Q4 (17 GiB,
staged at /mnt/seagate/models/qwen38-27b) loads whole in 111 s and runs ~4 tok/s CPU-only.
Kit recommendation: dense 27B from SSD into RAM; DS4 is an NVMe-media research track.
