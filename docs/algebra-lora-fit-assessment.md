# Fit of the existing 2B/9B algebra LoRAs

## Decision

Do not use the existing Heartwood/Totalrecall LoRAs as the general dashboard planner or semantic critic. Reuse their architecture and evaluation lessons, not their current weights or place-query vocabulary.

The models were trained to compile natural language into a place/geospatial algebra built around `SELECT`, `RELATE`, `AGGREGATE`, `COMPARE`, `ESTIMATE`, `RANK`, and later `FILTER`/`BUFFER`. That executor is strong for place questions and connector-backed records, but it is not the same language as this benchmark's arbitrary uploaded-table plan: typed column filters, derived ratios, multi-measure views, workbook regions, downloads and chart intent. A translation layer would still need a general model to understand the uploaded schema, so using the old algebra directly would not remove the hard semantic step.

More importantly, the prior measurements already warn against assuming the LoRA is generic. On its own in-template bank, LoRA-9B reached 1.000 and LoRA-2B 0.985. On never-seen livelihoods questions, however, LoRA-2B scored 0.747 and LoRA-9B 0.772, below the untuned few-shot 9B at 0.889. The recorded diagnosis was that the adapters learned the training sectors' phrasing-to-tree map and lost some of the base model's transfer. The 2B also failed multi-turn synthesis through fabrication, helplessness and repetition; the 9B survived the same conversation much better.

This directly supports the current anti-overfitting boundary:

- retain typed IR, mechanical execution, evidence labels, provenance, clarification and fail-closed behavior;
- keep the uploaded-table plan vocabulary independent of every subject and source-specific connector;
- use a small model only for a role it passes on untouched cross-subject and table-layout holdouts;
- if tuning later, train on structural diversity and multiple unrelated data dialects, with undisclosed subjects and layout families held out;
- never interpret an in-template LoRA score as event-readiness.

## Possible later use

The algebra work remains a useful source for a future generic computation compiler. Its lessons already appear in the current pipeline: an LLM emits a small declarative plan, code validates and executes it, evidence/provenance are attached mechanically, ambiguous intent can request clarification, and unsupported inference is labelled rather than guessed.

A later experiment could define an adapter target specifically for uploaded tabular data and visuals, then initialize from an untuned 8–9B base or train a multi-dialect adapter. That is a new training experiment, not a claim that the existing place LoRA fits. It should be admitted only if it beats its untuned base on untouched datasets from several undisclosed subjects and on unseen spreadsheet-layout families.

The existing candidate services were not started or reconfigured during this assessment. Their registry says the relevant 9B service is an unpromoted candidate and the serving history warns that cache/model-ID collisions previously replayed outputs from the wrong adapters. Historical measurements and files were read only.

Sources inspected: `/home/beeps/src/github.com/bprashanth/heartwood/docs/architecture/memory/chronology/20260712_model_curve_roi.md`, `20260714_xsector_curves_9b.md`, `20260717_hermes_erode_bench.md`, the algebra IR spec, Totalrecall v2.4 conformance bank, model registry, executor and LLM routing.
