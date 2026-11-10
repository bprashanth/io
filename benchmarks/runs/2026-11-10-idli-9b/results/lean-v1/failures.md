# Failure categories

Computed from 5,573 scored spans; 1,572 have `pass: false`. Only failing spans are counted. Each category counts spans once; categories may overlap, so their counts need not sum to the failing-span total.

`asked_instead` means `checks.tools_any: false` and nonempty text ending in `?`: the expected tool was absent, even if unrelated tools were called. `misroute` requires that same failed check plus an alternate flow tool (`file_get`, `file_open`, `file_peek`, `chart_request`, `chart_show`, `teach_file`, `teach_send`, `start`, `skills_list`, `show_progress`, or `report_gap`). Opening/reopening instead of answering, or opening instead of teaching, counts. Discovery alone (`drive_find`) and cards alone do not establish an alternate flow. Missing checks are not treated as false. `api_error` uses the row’s `api_error` field.

`other` is a fallback for failing spans matching none of the nine named categories; its reasons are itemised under each table. `wrong_spec` requires an actual `file_ask` call, and `incomplete_relay` requires `spec: true`, exactly as specified.

## local-qwen35-9b/base

Failing spans: 45.

| Category | Count |
| --- | ---: |
| card_as_text | 10 |
| wrong_card | 7 |
| misroute | 12 |
| wrong_spec | 10 |
| incomplete_relay | 2 |
| asked_instead | 5 |
| made_up_number | 2 |
| loop_or_timeout | 1 |
| api_error | 0 |
| other | 5 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; failed args:skill_delete: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.
- second required tool missing: 2.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.

## local-qwen35-9b/guards

Failing spans: 20.

| Category | Count |
| --- | ---: |
| card_as_text | 1 |
| wrong_card | 3 |
| misroute | 5 |
| wrong_spec | 8 |
| incomplete_relay | 1 |
| asked_instead | 4 |
| made_up_number | 1 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 2 |

Other reasons (each entry counts spans; combined failures stay together):
- required clarification missing: 2.

## lora-9b-004d/base

Failing spans: 25.

| Category | Count |
| --- | ---: |
| card_as_text | 8 |
| wrong_card | 0 |
| misroute | 3 |
| wrong_spec | 4 |
| incomplete_relay | 1 |
| asked_instead | 9 |
| made_up_number | 1 |
| loop_or_timeout | 1 |
| api_error | 0 |
| other | 3 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 1.
- required clarification missing: 1.
- required tool missing; failed args:skill_delete: 1.

## lora-9b-004d/guards

Failing spans: 4.

| Category | Count |
| --- | ---: |
| card_as_text | 2 |
| wrong_card | 0 |
| misroute | 0 |
| wrong_spec | 1 |
| incomplete_relay | 0 |
| asked_instead | 0 |
| made_up_number | 0 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 1 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 1.

## muse30b/base

Failing spans: 29.

| Category | Count |
| --- | ---: |
| card_as_text | 3 |
| wrong_card | 10 |
| misroute | 10 |
| wrong_spec | 4 |
| incomplete_relay | 2 |
| asked_instead | 2 |
| made_up_number | 1 |
| loop_or_timeout | 2 |
| api_error | 0 |
| other | 2 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; failed args:file_get: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.

## or-gpt-oss-20b/base

Failing spans: 130.

| Category | Count |
| --- | ---: |
| card_as_text | 5 |
| wrong_card | 44 |
| misroute | 23 |
| wrong_spec | 40 |
| incomplete_relay | 10 |
| asked_instead | 0 |
| made_up_number | 11 |
| loop_or_timeout | 4 |
| api_error | 0 |
| other | 21 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 3.
- file choices missing: 1.
- required card missing: 1.
- required tool missing: 3.
- required tool missing; failed args:skill_delete: 2.
- required tool missing; required card missing: 2.
- required tool missing; required card missing; failed args:file_get: 1.
- required tool missing; second required tool missing: 1.
- required tool missing; second required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.
- required tool missing; spec failed without file_ask; relay failed without a correct spec; chart not relayed: 2.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-gpt-oss-20b/guards

Failing spans: 105.

| Category | Count |
| --- | ---: |
| card_as_text | 2 |
| wrong_card | 10 |
| misroute | 11 |
| wrong_spec | 46 |
| incomplete_relay | 10 |
| asked_instead | 0 |
| made_up_number | 15 |
| loop_or_timeout | 10 |
| api_error | 0 |
| other | 26 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 2.
- file choices missing: 1.
- required card missing: 2.
- required clarification missing: 3.
- required tool missing: 3.
- required tool missing; failed args:file_get: 1.
- required tool missing; required card missing: 3.
- required tool missing; second required tool missing: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 8.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-gpt-oss-20b/guards2

Failing spans: 115.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 31 |
| misroute | 20 |
| wrong_spec | 43 |
| incomplete_relay | 10 |
| asked_instead | 0 |
| made_up_number | 9 |
| loop_or_timeout | 9 |
| api_error | 0 |
| other | 20 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 2.
- required tool missing: 2.
- required tool missing; failed args:file_get: 2.
- required tool missing; required card missing: 2.
- required tool missing; required card missing; failed args:file_get: 1.
- required tool missing; second required tool missing: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 5.
- required tool missing; spec failed without file_ask; relay failed without a correct spec; chart not relayed: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 4.

## or-gpt-oss-20b/starthere

Failing spans: 7.

| Category | Count |
| --- | ---: |
| card_as_text | 2 |
| wrong_card | 0 |
| misroute | 0 |
| wrong_spec | 0 |
| incomplete_relay | 0 |
| asked_instead | 0 |
| made_up_number | 0 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 5 |

Other reasons (each entry counts spans; combined failures stay together):
- forbidden tool called; required response content missing: 2.
- required card missing: 1.
- required tool missing; required response content missing: 2.

## or-granite-8b/base

Failing spans: 60.

| Category | Count |
| --- | ---: |
| card_as_text | 28 |
| wrong_card | 3 |
| misroute | 8 |
| wrong_spec | 2 |
| incomplete_relay | 4 |
| asked_instead | 0 |
| made_up_number | 13 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 8 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; chart not relayed: 1.
- required tool missing; failed args:skill_delete: 2.
- required tool missing; second required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-granite-8b/guards

Failing spans: 33.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 4 |
| misroute | 2 |
| wrong_spec | 5 |
| incomplete_relay | 2 |
| asked_instead | 0 |
| made_up_number | 16 |
| loop_or_timeout | 2 |
| api_error | 0 |
| other | 6 |

Other reasons (each entry counts spans; combined failures stay together):
- required clarification missing: 1.
- required tool missing: 2.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.

## or-granite-8b/guards2

Failing spans: 29.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 5 |
| misroute | 4 |
| wrong_spec | 3 |
| incomplete_relay | 4 |
| asked_instead | 0 |
| made_up_number | 11 |
| loop_or_timeout | 1 |
| api_error | 0 |
| other | 5 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; chart not relayed: 2.
- required tool missing; failed args:file_get: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-granite-8b/starthere

Failing spans: 2.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 0 |
| misroute | 0 |
| wrong_spec | 0 |
| incomplete_relay | 0 |
| asked_instead | 0 |
| made_up_number | 0 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 2 |

Other reasons (each entry counts spans; combined failures stay together):
- forbidden tool called; required response content missing: 2.

## or-ministral-8b/base

Failing spans: 88.

| Category | Count |
| --- | ---: |
| card_as_text | 5 |
| wrong_card | 22 |
| misroute | 24 |
| wrong_spec | 18 |
| incomplete_relay | 14 |
| asked_instead | 3 |
| made_up_number | 10 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 14 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 7.
- required tool missing; failed args:skill_delete: 2.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.
- second required tool missing: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-ministral-8b/guards

Failing spans: 79.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 4 |
| misroute | 7 |
| wrong_spec | 19 |
| incomplete_relay | 28 |
| asked_instead | 2 |
| made_up_number | 16 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 11 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 3.
- required tool missing: 3.
- required tool missing; chart not relayed: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.
- second required tool missing: 2.

## or-ministral-8b/guards2

Failing spans: 60.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 5 |
| misroute | 6 |
| wrong_spec | 3 |
| incomplete_relay | 26 |
| asked_instead | 0 |
| made_up_number | 12 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 14 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 6.
- required tool missing: 3.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 4.
- second required tool missing: 1.

## or-ministral-8b/starthere

Failing spans: 4.

| Category | Count |
| --- | ---: |
| card_as_text | 3 |
| wrong_card | 1 |
| misroute | 0 |
| wrong_spec | 0 |
| incomplete_relay | 0 |
| asked_instead | 0 |
| made_up_number | 0 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 0 |

## or-qwen35-35b-a3b/base

Failing spans: 71.

| Category | Count |
| --- | ---: |
| card_as_text | 15 |
| wrong_card | 9 |
| misroute | 12 |
| wrong_spec | 19 |
| incomplete_relay | 14 |
| asked_instead | 5 |
| made_up_number | 7 |
| loop_or_timeout | 4 |
| api_error | 0 |
| other | 7 |

Other reasons (each entry counts spans; combined failures stay together):
- forbidden tool called: 1.
- required tool missing; failed args:skill_delete: 1.
- second required tool missing: 3.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-qwen35-35b-a3b/guards

Failing spans: 51.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 10 |
| misroute | 10 |
| wrong_spec | 16 |
| incomplete_relay | 13 |
| asked_instead | 2 |
| made_up_number | 6 |
| loop_or_timeout | 3 |
| api_error | 0 |
| other | 9 |

Other reasons (each entry counts spans; combined failures stay together):
- forbidden tool called: 1.
- required tool missing: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.
- required tool missing; spec failed without file_ask; relay failed without a correct spec; chart not relayed: 1.
- second required tool missing: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-qwen35-35b-a3b/guards2

Failing spans: 54.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 13 |
| misroute | 15 |
| wrong_spec | 18 |
| incomplete_relay | 13 |
| asked_instead | 3 |
| made_up_number | 5 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 2 |

Other reasons (each entry counts spans; combined failures stay together):
- required clarification missing: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.

## or-qwen35-35b-a3b/guards3

Failing spans: 31.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 6 |
| misroute | 7 |
| wrong_spec | 10 |
| incomplete_relay | 10 |
| asked_instead | 4 |
| made_up_number | 3 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 1 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.

## or-qwen35-35b-a3b/starthere

Failing spans: 1.

| Category | Count |
| --- | ---: |
| card_as_text | 1 |
| wrong_card | 0 |
| misroute | 0 |
| wrong_spec | 0 |
| incomplete_relay | 0 |
| asked_instead | 0 |
| made_up_number | 0 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 0 |

## or-qwen35-9b/base

Failing spans: 102.

| Category | Count |
| --- | ---: |
| card_as_text | 17 |
| wrong_card | 23 |
| misroute | 28 |
| wrong_spec | 22 |
| incomplete_relay | 12 |
| asked_instead | 11 |
| made_up_number | 8 |
| loop_or_timeout | 1 |
| api_error | 0 |
| other | 9 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing: 2.
- required tool missing; failed args:skill_delete: 2.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.

## or-qwen35-9b/guards

Failing spans: 59.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 15 |
| misroute | 18 |
| wrong_spec | 20 |
| incomplete_relay | 12 |
| asked_instead | 9 |
| made_up_number | 5 |
| loop_or_timeout | 2 |
| api_error | 0 |
| other | 2 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-qwen35-9b/guards2

Failing spans: 60.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 12 |
| misroute | 22 |
| wrong_spec | 20 |
| incomplete_relay | 13 |
| asked_instead | 10 |
| made_up_number | 4 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 5 |

Other reasons (each entry counts spans; combined failures stay together):
- required clarification missing: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 4.

## or-qwen35-9b/guards3

Failing spans: 50.

| Category | Count |
| --- | ---: |
| card_as_text | 1 |
| wrong_card | 12 |
| misroute | 15 |
| wrong_spec | 18 |
| incomplete_relay | 10 |
| asked_instead | 10 |
| made_up_number | 5 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 3 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 2.

## or-qwen35-9b-think/base

Failing spans: 82.

| Category | Count |
| --- | ---: |
| card_as_text | 13 |
| wrong_card | 8 |
| misroute | 19 |
| wrong_spec | 12 |
| incomplete_relay | 13 |
| asked_instead | 9 |
| made_up_number | 6 |
| loop_or_timeout | 2 |
| api_error | 0 |
| other | 14 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 1.
- file choices missing: 1.
- forbidden tool called: 1.
- required card missing: 3.
- required tool missing; required card missing; failed args:file_get: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.
- required tool missing; spec failed without file_ask; relay failed without a correct spec; chart not relayed: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.

## or-qwen35-9b-think/guards

Failing spans: 80.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 18 |
| misroute | 14 |
| wrong_spec | 18 |
| incomplete_relay | 34 |
| asked_instead | 9 |
| made_up_number | 7 |
| loop_or_timeout | 1 |
| api_error | 0 |
| other | 10 |

Other reasons (each entry counts spans; combined failures stay together):
- chart not relayed: 1.
- file choices missing: 1.
- forbidden tool called: 1.
- required clarification missing: 2.
- required tool missing: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.
- second required tool missing: 1.

## or-qwen35-9b-think/guards2

Failing spans: 58.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 17 |
| misroute | 14 |
| wrong_spec | 15 |
| incomplete_relay | 15 |
| asked_instead | 10 |
| made_up_number | 6 |
| loop_or_timeout | 2 |
| api_error | 0 |
| other | 3 |

Other reasons (each entry counts spans; combined failures stay together):
- forbidden tool called: 1.
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.
- second required tool missing; spec failed without file_ask; relay failed without a correct spec: 1.

## or-qwen35-9b-think/guards3

Failing spans: 37.

| Category | Count |
| --- | ---: |
| card_as_text | 0 |
| wrong_card | 12 |
| misroute | 9 |
| wrong_spec | 16 |
| incomplete_relay | 9 |
| asked_instead | 1 |
| made_up_number | 2 |
| loop_or_timeout | 1 |
| api_error | 0 |
| other | 3 |

Other reasons (each entry counts spans; combined failures stay together):
- required tool missing; spec failed without file_ask; relay failed without a correct spec: 3.

## or-qwen35-9b-think/starthere

Failing spans: 1.

| Category | Count |
| --- | ---: |
| card_as_text | 1 |
| wrong_card | 0 |
| misroute | 0 |
| wrong_spec | 0 |
| incomplete_relay | 0 |
| asked_instead | 0 |
| made_up_number | 0 |
| loop_or_timeout | 0 |
| api_error | 0 |
| other | 0 |

# Failing-span details

Each gist contains exactly twelve whitespace-separated words. For empty `text`, the line explicitly records that no textual gist is available. Multiple applicable categories share the same line. Replicate and span numbers are copied unchanged from the source.

## muse30b/base

d04-volunteers-clean r0 s0 [open]: loop_or_timeout - No reply text was recorded; this span contains no user visible gist
d04-volunteers-clean r0 s1 [clean]: misroute - Says Idli cannot download this spreadsheet because it may no longer exist
d04-volunteers-clean r0 s2 [clean]: card_as_text - Says Idli cannot download this spreadsheet because it may no longer exist
d04-volunteers-clean r0 s4 [ask]: misroute - Displays a gap report about failed spreadsheet downloads and unavailable reading tools
d06-roadkill-gap r0 s1 [teach]: made_up_number - Computes Old Valparai frog deaths as 20.8 percent of all monsoon deaths
d11-learned r0 s1 [skills]: card_as_text - Confirms that Idli has already forgotten the previously learned Volunteer register file
d11-learned r0 s2 [skills]: misroute - Lists learned files and invites deletion or refreshing the current skills list
d11-learned r1 s1 [skills]: card_as_text - Confirms that Idli has already forgotten the previously learned Volunteer register file
d11-learned r1 s2 [skills]: asked_instead - Says Volunteer register is forgotten and asks which other file to forget
d13-old-survey r0 s0 [find]: wrong_card - No reply text was recorded; this span contains no user visible gist
d13-old-survey r0 s1 [open]: wrong_card - No reply text was recorded; this span contains no user visible gist
d13-old-survey r1 s0 [find]: wrong_card - No reply text was recorded; this span contains no user visible gist
d13-old-survey r1 s1 [open]: other (required tool missing; failed args:file_get) - Says the old household survey is open and invites the first question
d14-mgnrega-compare r0 s0 [ask]: incomplete_relay - Shows village personday totals and points to dashboard or fuller Claude charts
d14-mgnrega-compare r1 s0 [ask]: misroute, asked_instead - Asks whether village persondays should cover all years or receive further breakdowns
h01-roadkill-groups r0 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
h01-roadkill-groups r1 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
h03-reimb-paid-hardware r0 s0 [ask]: wrong_spec - Reports no paid hardware claims and says the form displays that result
h03-reimb-paid-hardware r0 s1 [ask]: wrong_spec - Says no rows match the Hardware category together with the Paid status
h03-reimb-paid-hardware r1 s0 [ask]: wrong_spec - Reports paid hardware claims total zero rupees and points to the form
h03-reimb-paid-hardware r1 s1 [ask]: wrong_spec - Reports no matching paid hardware claims and consequently no employees with claims
h05-trees-species r1 s0 [ask]: wrong_card - No reply text was recorded; this span contains no user visible gist
h07-volunteers-district r0 s0 [ask]: other (second required tool missing; spec failed without file_ask; relay failed without a correct spec) - Cannot download Volunteer register and requests a Drive link or Sheets confirmation
h07-volunteers-district r1 s0 [ask]: loop_or_timeout - No reply text was recorded; this span contains no user visible gist
q05-mgnrega-work-mix r0 s1 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
q06-roadkill-season-rate r0 s3 [chart]: incomplete_relay - Summarises summer roadkill rates with highest lowest and combined figures plus chart
r01-family-vulnerability r0 s1 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r01-family-vulnerability r1 s1 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r02-village-population r0 s1 [chart]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist

## or-qwen35-9b/guards

d01-start-households r1 s7 [chart]: wrong_spec - Shows total monthly income by ward and offers Claude for fuller charts
d06-roadkill-gap r0 s0 [ask]: other (required tool missing; spec failed without file_ask; relay failed without a correct spec) - Lists several survey files and asks which one the user actually means
d06-roadkill-gap r1 s0 [ask]: wrong_spec - Opens roadkill data and uses average counts to identify monsoon frog deaths
d08-mgnrega-suggest r1 s0 [chart]: wrong_card - No reply text was recorded; this span contains no user visible gist
d08-mgnrega-suggest r1 s1 [teach]: misroute - Says MGNREGA data is open and offers possible topics for further analysis
d14-mgnrega-compare r0 s0 [ask]: made_up_number - Compares village personday totals and adds a calculated difference of 144 persondays
h01-roadkill-groups r0 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
h01-roadkill-groups r0 s5 [chart]: misroute, asked_instead - Says chart remains unsent and asks whether to display a quick chart
h01-roadkill-groups r1 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
h01-roadkill-groups r1 s5 [chart]: misroute, asked_instead - Says chart remains unsent and offers Claude quick charts or another question
h03-reimb-paid-hardware r0 s0 [ask]: wrong_spec - Reports 49,592 rupees paid for hardware claims then presents initial analysis choices
h03-reimb-paid-hardware r0 s1 [ask]: wrong_spec - Names Employee B as largest paid claimant with 17,795 rupees in claims
h05-trees-species r0 s0 [ask]: made_up_number - Reports twenty unique Korangumudi tree species and says fifteen species are listed
h05-trees-species r0 s1 [ask]: made_up_number - Reports 32 alien trees among 98 and calculates approximately 33 percent alien
h05-trees-species r0 s2 [chart]: incomplete_relay - Shows alien tree counts across fragments highlighting Puthuthottam Korangumudi and Injipara totals
h05-trees-species r1 s2 [chart]: incomplete_relay - Displays alien tree counts across fragments and offers fuller charting through Claude
h07-volunteers-district r0 s0 [ask]: wrong_spec - Shows district stipend totals and identifies District D as receiving most money
h07-volunteers-district r1 s0 [ask]: wrong_spec - Identifies District D as having most volunteers using total stipend payments instead
h07-volunteers-district r1 s1 [teach]: made_up_number - Drafts a report sentence calculating District D received 41 percent of stipends
q02-tracker-completed r0 s3 [chart]: incomplete_relay - Reposts the existing District C households chart and offers further Claude analysis
q02-tracker-completed r1 s3 [chart]: misroute, incomplete_relay, asked_instead - Prepares fake data for Claude and repeatedly seeks sending and label choices
q06-roadkill-season-rate r0 s3 [chart]: misroute, incomplete_relay, asked_instead - Explains Claude chart design and label sharing then says nothing was sent
q06-roadkill-season-rate r1 s3 [chart]: misroute, incomplete_relay, asked_instead - Says chart remains unsent recaps seasonal rates and offers further data comparisons
q07-tree-plots-invasion r0 s2 [ask]: incomplete_relay, made_up_number - Compares native and alien girths in Korangumudi rounding alien girth to 73.6
q07-tree-plots-invasion r0 s3 [ask]: incomplete_relay - Compares native and alien girths in Injipara saying native trees are thicker
q07-tree-plots-invasion r1 s2 [ask]: incomplete_relay - Lists Korangumudi native and alien average girths and offers fuller Claude charts
q07-tree-plots-invasion r1 s3 [ask]: incomplete_relay - Lists Injipara native and alien average girths noting failed rows remain included
r01-family-vulnerability r0 s1 [ask]: wrong_card, misroute - Acknowledges vulnerability by family size and says the file needs analysis preparation
r01-family-vulnerability r0 s2 [ask]: wrong_spec - Charts average household members by vulnerability score for Ward C household records
r01-family-vulnerability r0 s3 [ask]: wrong_spec - Charts average members grouped by family size for households in Ward A
r02-village-population r0 s1 [chart]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r02-village-population r0 s2 [ask]: wrong_card, wrong_spec - No reply text was recorded; this span contains no user visible gist
r02-village-population r1 s1 [chart]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r03-claim-size r0 s3 [ask]: wrong_spec - Says no paid hardware claims exist and offers alternative categories or statuses
r03-claim-size r0 s4 [ask]: asked_instead - Says no paid hardware average exists and asks about alternative claim subsets
r03-claim-size r1 s3 [ask]: wrong_spec - Reports no rows match Hardware category and Paid status in the form
r03-claim-size r1 s4 [ask]: asked_instead - Says paid hardware claims are absent and offers broader alternatives for analysis
r04-volunteer-hours r0 s1 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r04-volunteer-hours r0 s2 [ask]: wrong_spec - Shows total September hours by joining month for volunteers in District D
r04-volunteer-hours r1 s1 [ask]: wrong_card, misroute, asked_instead - Says Volunteer register is open with seventeen problems and presents starting choices
r05-check-dam-reach r0 s1 [ask]: wrong_spec - Shows household engagement totals for check dam construction grouped by each village
r05-check-dam-reach r0 s2 [ask]: wrong_spec - Shows household engagement totals for water body desilting grouped by each village
r05-check-dam-reach r0 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r05-check-dam-reach r0 s4 [ask]: other (required tool missing; spec failed without file_ask; relay failed without a correct spec) - Says previous answers became question text and requests sending and label choices
r05-check-dam-reach r1 s1 [ask]: wrong_spec - Answers average household engagement request with total check dam households by village
r05-check-dam-reach r1 s2 [ask]: wrong_spec - Shows total household engagement for water body desilting work in each village
r05-check-dam-reach r1 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r05-check-dam-reach r1 s4 [ask]: asked_instead - Explains row listings need Claude and repeatedly requests confirmation after card closures
r06-roadkill-groups r1 s1 [ask]: wrong_spec - Displays average animal counts by group at Azhiyar and offers further charts
r06-roadkill-groups r1 s2 [ask]: wrong_spec - Shows summer average animal counts by group at Azhiyar with dashboard chart
r07-tree-species-height r0 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r07-tree-species-height r0 s4 [ask]: misroute - Explains teaching native tree row listings then sends fake data to Claude
r07-tree-species-height r1 s1 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
r07-tree-species-height r1 s2 [ask]: wrong_spec - Lists native tree counts by species with additional rows in the form
r07-tree-species-height r1 s4 [ask]: wrong_spec - Reports native trees average 13.79 metres high and offers breakdown by species
r08-officer-roster-switch r0 s2 [ask]: wrong_card, incomplete_relay - Says the query returned visits instead of officers and promises another approach
r08-officer-roster-switch r0 s3 [find]: loop_or_timeout - Acknowledges switching to the reimbursement spreadsheet and says it will find it
r08-officer-roster-switch r1 s2 [ask]: wrong_card, incomplete_relay - Says the query returned visits instead of officers and promises another approach
r08-officer-roster-switch r1 s3 [find]: loop_or_timeout - Acknowledges switching to a different file and promises to find that file

## local-qwen35-9b/guards

d01-start-households r1 s7 [chart]: wrong_spec - Shows total monthly income by ward and offers Claude for fuller charts
d06-roadkill-gap r0 s0 [ask]: asked_instead - Finds the roadkill spreadsheet and asks whether this is the intended file
d06-roadkill-gap r1 s0 [ask]: asked_instead - Lists roadkill and household spreadsheets then asks which file the user wants
d07-trees-charts r0 s2 [chart]: card_as_text, asked_instead - Reasks whether Claude should improve the chart after misinterpreting earlier option selections
d07-trees-charts r1 s0 [chart]: wrong_spec - Shows alien tree counts per fragment then asks how the user starts
d10-find-none r0 s0 [find]: other (required clarification missing) - Reports no matching solar pump survey file and instructs asking another keyword
d10-find-none r1 s0 [find]: other (required clarification missing) - Reports no matching solar pump survey file and instructs asking another keyword
d14-mgnrega-compare r0 s0 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
d14-mgnrega-compare r0 s2 [ask]: wrong_spec - Shows household engagement totals grouped by village and work type with chart
d14-mgnrega-compare r1 s0 [ask]: incomplete_relay - Repeats village personday totals then asks whether to analyse more or clean
h01-roadkill-groups r0 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
h01-roadkill-groups r0 s4 [ask]: wrong_spec - Shows summer average counts and identifies Mollusca and Diplopoda as highest groups
h01-roadkill-groups r0 s5 [chart]: misroute, asked_instead - Says chart was prepared but unsent and offers sending or alternative questions
h01-roadkill-groups r1 s3 [ask]: wrong_card, misroute - No reply text was recorded; this span contains no user visible gist
h01-roadkill-groups r1 s4 [ask]: wrong_spec - Reports summer group averages then offers total counts for the original question
h01-roadkill-groups r1 s5 [chart]: misroute - Presents a summer chart as totals while describing average counts per record
h03-reimb-paid-hardware r0 s0 [ask]: wrong_spec - Reports hardware payouts of 64,245 rupees after offering initial file analysis options
h03-reimb-paid-hardware r1 s0 [ask]: wrong_spec - Reports hardware payouts of 64,245 rupees then repeats initial file analysis options
h05-trees-species r0 s0 [ask]: wrong_spec - Lists two species and counts for Korangumudi then asks what to investigate
h05-trees-species r1 s2 [chart]: made_up_number - Shows alien tree counts and describes the displayed results as top fifteen
