---
description: Make a sandbox for a workflow that touches private accounts or files
---
The person wants a sandbox for: $ARGUMENTS

Follow the sandbox steps in CLAUDE.md, one question at a time:
1. If $ARGUMENTS is empty, ask what they want to do.
2. Ask about names, places or phone numbers; the outside service (ask each time, never, or always); and which
   accounts (role and email).
3. Call `sandbox_blocks`, map each step to a block, and say the plan in one or two lines. Name any step with no block.
4. A gap: say it plainly, call `sandbox_create` with `gaps`, and stop.
5. No gap: after their yes, call `sandbox_create` with a one-word name for the workflow, then `sandbox_connect` for
   each account it lists.
6. Tell them which sidebar heading to open and how to try it step by step.
