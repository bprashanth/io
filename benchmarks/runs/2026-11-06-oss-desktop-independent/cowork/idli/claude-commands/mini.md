Make a reusable Mini from the analysis in this conversation.

Work with the person in small steps. Agree on a short title, a plain-language story, and the questions colleagues
will ask. Keep at most 8 questions, each with at most 3 options (choice or number, with defaults).
Write one self-contained Python script per question in the current work folder. It reads the current drive/ files,
accepts --name value options and prints its answer. To include a live chart, print a final single-line JSON object
with vega_lite and data. Use the exact current files; never invent results.
Run EVERY script on the current files with its defaults and check the result. Also test each choice and reasonable
number values. Fix failures before proceeding. Tell the person what the Mini can answer and any limits.
Then call idli_draft_mini(title, story, questions, code). Each question has id, question, script (the Python path),
and params (names mapped to {type: "choice"|"number", choices?, default}). code is the folder containing the scripts.
Idli adds only this workspace's pinned charts and opens an editable page on the right. The person edits and saves
there. If this conversation started from a Mini, the page offers Add to that Mini or Save as a new Mini.
Do not call idli_save_mini: the person saves from the editor. Offer Back to Claude when they want to keep working.
