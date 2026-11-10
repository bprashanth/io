You are given `scores.json` (one row per scored span of a scripted chat; fields: model, variant, scenario, conv,
rep, span, segment, pass, checks (failed ones are false), deviations, invented (numbers not from any tool),
tools (tools the model called in that span), text (the reply the person saw, truncated)).

Write `failures.md` in this folder:
1. For each (model, variant) with at least one failing span, a table of failure categories with counts. Use exactly
   these categories (a span can have more than one):
   - card_as_text: check `card` false and no AskUserQuestion in tools, text present
   - wrong_card: deviations contain card_without_expected_option or card_where_user_types
   - misroute: tools_any false and a different flow was taken (e.g. file_peek or chart_request instead of file_get /
     file_ask, teach_file when the file was known)
   - wrong_spec: spec false while file_ask was called
   - incomplete_relay: spec true but relay false
   - asked_instead: no tool in tools_any, and the text ends with a question
   - made_up_number: invented non-empty
   - loop_or_timeout: deviations contain loop_same_call, step_cap or turn_timeout
   - api_error
   - other (say what)
2. Then, for muse30b/base and for or-qwen35-9b/guards and local-qwen35-9b/guards: list each failing span as one line
   "conv rN sK [segment]: category - <12-word gist from text>".
Be exact with counts (compute them, e.g. with a short Python script). Output only the file.
