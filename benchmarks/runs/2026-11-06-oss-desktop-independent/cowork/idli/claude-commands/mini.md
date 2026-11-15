Make a reusable Mini from the analysis in this conversation.

Work with the person in small steps. Propose a short title, a plain-language story, and the questions colleagues
will ask, and agree on them once. Keep at most 8 questions, each with at most 3 options (choice or number, with defaults).
Write one self-contained Python script per question in the current work folder. It reads the current drive/ files,
accepts --name value options and prints its answer. To include a live chart, print a final single-line JSON object
with vega_lite and data. Use the exact current files; never invent results.
Run EVERY script on the current files with its defaults and check the result. Also test each choice and reasonable
number values. Fix failures before proceeding. Tell the person briefly what the Mini can answer and any limits, and
then call idli_draft_mini straight away (do not ask again: the editor page is where they check and change it). Call idli_draft_mini(title, story, questions, code). Each question has id, question, script (the Python path),
params (names mapped to {type: "choice"|"number", choices?, default}), and asks: 3 to 5 ways a colleague
might ask it in their own words ("who is most stretched in <a ward>", "top 3 debtors in <a ward>"). A small local
model matches people's questions to these, so cover the everyday words for each measure and option. code is the folder containing the scripts.
Idli adds only this workspace's pinned charts and shows the editable draft in the Drivey chat on the left, under the
charts. The person edits and saves there. If this conversation started from a Mini, the page offers Add to that Mini or Save as a new Mini.
Do not call idli_save_mini: the person saves from the editor.
