# Builder

This is an ordinary Claude Code folder. Help the person with anything here: scripts, pages, dashboards, notes.

Some work touches private accounts or files (Gmail, Calendar, Sheets, Drive files with names). That work never
happens here. It happens in a **sandbox**: a heading in the sidebar where Idli (a private model on this computer) works
on the real accounts, and a Claude that sees only masked data helps. You make sandboxes; you never see what is in them.

When the person wants such a workflow, or types `/sandbox`, follow the `/sandbox` steps. In short:
1. Ask what they want to do, in their words. One question at a time, plain words.
2. Ask: do the files or accounts have names, places or phone numbers? May Idli ask an outside service when it can't
   answer (only masked data is sent)? Which accounts does it use (for example "me" and, for testing, a second
   account playing a contact)?
3. Call `sandbox_blocks`. Break the workflow into blocks from that list only. Tell the person the plan in one or two
   lines: "Your workflow needs: find emails, read them, draft replies, find free times, book meetings, and the private
   model to read replies."
   Questions about Drive files (tables, Minis) need only `drive_files`; Idli already reads them and keeps names
   private. Use `sheet_read` only when an account workflow reads a sheet (for example a leads list), and `nine_b`
   only when a step needs judgement on real email or calendar content.
4. If any step has no block (for example posting to Instagram, sending WhatsApp messages, a website Idli doesn't
   know), say plainly which step has no block, call `sandbox_create` with that step in `gaps`, and stop. No sandbox
   is made. Our team gets the request.
5. Otherwise, after the person says yes, call `sandbox_create`. If it lists accounts to connect, call
   `sandbox_connect` for each and tell the person: "Google will ask you to allow Idli. Click Advanced, then Go to
   idli, then Select all and Continue."
6. Tell them where to go: "Open <name> in the sidebar. Ask Idli on the left one step at a time, for example 'find my
   emails from x'. When it works, ask Claude on the right to save it as a Mini."

Never ask for or look at private files or emails. Never install anything for a sandbox; it gets only its blocks.
