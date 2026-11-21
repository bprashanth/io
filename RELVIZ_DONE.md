# Relationship visualization task completed

- Added five synthetic NGO workbooks and a seeded generator in
  [`benchmarks/runs/2026-11-14-relviz/fixtures/`](benchmarks/runs/2026-11-14-relviz/fixtures/).
- Added the masked Claude
  [`relationship-visuals` skill](benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/idli/claude-skills/relationship-visuals/SKILL.md)
  with a decision table and seven executable Vega-Lite templates. It preserves
  chart consent, stable masked codes, and the no-consecutive-repetition rule.
- Updated `desktop/claude-masked.sh` to install skills and nested resources into
  the Claude work folder's `.claude/skills/` on each launch.
- Added seven CSV/spec/SVG examples, thumbnails, reproducible commands, and a
  [validation report](benchmarks/runs/2026-11-14-relviz/out/validation.json).
  See the [benchmark README](benchmarks/runs/2026-11-14-relviz/README.md).

Validation: workbook generation passed; all joins and planted patterns passed;
all seven specs rendered populated SVGs using `vl_convert`, with seven distinct
chart families; isolated launcher install/refresh and argument checks passed;
shell syntax and skill frontmatter/resource checks passed. Changes committed on
the existing branch; no push performed.
