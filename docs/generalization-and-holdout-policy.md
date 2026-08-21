# Generalization policy for the NGO insight system

The system is intended for unknown sectors and unknown datasets. A benchmark pass is invalid evidence if production behavior was tailored to a case's subject, expected values or wording.

## Production boundaries

Production code must not branch on benchmark case IDs, expected answers, fixture filenames, sector names, named districts/blocks, or exact prompt sentences. It must not grow into a phrase-by-phrase English parser for the current question bank.

This boundary applies to prompts and routing as well as Python code. A list of sector indicators, known numerator/denominator pairs, familiar sheet names or preselected chart recipes is content-based specialization even if it is written in a prompt or connector rather than an `if` statement. The system may use names, units and relationships found in the participant's current files and conversation; it may not carry a hidden curriculum of expected event content.

Deterministic code is limited to mechanics that remain true across domains:

- retain file structure, cell/page coordinates and source provenance;
- identify candidate regions from geometry and value types;
- validate schemas, column existence, data types and executable scope;
- execute filters, joins, arithmetic and aggregations without model-authored values;
- distinguish typed count subtraction from percentage-point subtraction;
- prevent duplicate output, unsafe formulas, CSV injection and broken pages;
- render and browser-test the declarative result.

The LLM remains responsible for meaning: selecting relevant sheets/regions/measures, understanding follow-ups, choosing comparisons and views, and explaining limitations. A separate general-language critic can reject an incomplete plan and request one bounded repair. The critic is not given benchmark answers.

Benchmark oracles and verifiers are deliberately case-specific because they must check exact answers. They are outside the candidate system, cannot be imported by it, and are not evidence that a matching production rule is allowed.

Official-source connectors are optional retrieval accelerators, not the core intelligence path. A source-specific connector may retrieve and preserve files after the general agent has selected that source, but it cannot stand in for general discovery or interpretation. The planner and renderer must work across unrelated and unfamiliar subjects. Unknown sources route to bounded web discovery; unknown layouts route to a layout-capable extraction model. Neither should silently select a convenient table.

## Evidence discipline

Cases used while changing code are development cases. They cannot establish generalization. Promotion requires all of the following after code and prompts are frozen:

1. untouched holdout datasets from several undisclosed, unrelated subjects;
2. paraphrases that do not reuse development wording;
3. layout perturbations such as shifted rows/columns, reordered sheets, extra notes, horizontal and vertical regions, deeper headings, formulas and missing cells;
4. exact-value, provenance, download and browser checks;
5. human inspection of the rendered desktop page;
6. a paired Antigravity run on the same conversation;
7. early stopping and fallback rather than case-specific patching after a holdout failure.

Failure taxonomy matters. A model-selection failure, structure-extraction failure, semantic-plan failure, arithmetic failure, rendering failure and product-handoff failure are recorded separately. Fixes must target the responsible layer and then be tested on unrelated cases and mutations.

## Current status

The geometry-based Excel adapter now handles two development layout families: vertically stacked and horizontally adjacent regions with merged titles, two-row repeated headings and numeric bodies. It contains no sector, indicator or geography rules. This is still a narrow structural capability, not arbitrary Excel support. Unsupported merged layouts and workbooks with several plausible rectangular data sheets now fail closed for routing to a general layout-selection fallback instead of silently choosing the largest tab.

The earlier rule-assisted GPT-OSS results remain useful ablations, but are not the preferred product architecture. The generic planner plus an independent, metadata-only Gemini critic passed the new side-by-side mixed-unit journey; the critic saw the conversation, structure and proposed plan but no raw rows or hidden values. The same-model self-critic missed one of two requested answers, while an always-on Qwen critic was accurate but slow. Untouched cross-subject holdouts and a real layout-model fallback are still required before event readiness can be claimed.
