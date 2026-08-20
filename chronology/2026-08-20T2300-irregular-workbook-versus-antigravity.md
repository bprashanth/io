# Merged-header and stacked-subtable journey versus Antigravity

We built the first non-flat workbook case after the user explicitly warned against assuming one sheet and one rectangular table. The fixture has merged two-row headings, two vertically stacked attendance tables, three tabs and a larger irrelevant rectangular enrolment sheet. The measured correction is ordinary language: “there is another attendance table below for secondary school.”

The initial loader was replaced for this pattern with a structure-preserving region scan. It records all sheets, merged ranges, table titles, header/data rows and exact ranges, then pivots compatible block/year observations into four reported metrics. It does not ask the model to infer values from a flattened, already-damaged sheet.

GPT-OSS 20B Low passed the counted run in five calls and one repair: 26.872 seconds and $0.00047230. It focused on primary in turn 1, added secondary in turn 2, returned the exact 73% versus 66% and 7 pp secondary-girls comparison in turn 3, and preserved a two-row traceable download in turn 4. Human and browser checks passed.

Five discarded repetitions taught the executor to handle null filters, remove UI placeholders, reject unfinished participant prose, prohibit averaging already-unique observations, prohibit deriving percentages from reported percentages and normalize subtraction units from known metric types. Raw model plans and normalized plans are both retained.

Antigravity's untouched default resolved to Gemini 3.7 Flash (High). It correctly parsed both tables and generated a beautiful, feature-rich page, but its turn ended in an artifact-path permission error and a foreground server process. The outer run timed out after 613.597 seconds and 239,543 tokens, before the user could send the correction or comparison turns. A separately served artifact worked offline and exposed correct secondary values, but invented performance tiers, could not select exactly two blocks, and exported the wrong scope without provenance under a primary-labelled filename.

This is a strong split-path result and a real Antigravity operational fault, but not a general Excel or GUI-equivalence claim. The exact adapter pattern and all failed runs remain replayable.

