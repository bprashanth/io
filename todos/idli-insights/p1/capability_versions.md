# When a sandbox's Claude changes a capability, what happens to the other sandboxes?

Owner's question, 2026-11-19. Context: capabilities become CLIs with arguments (`narrative/SANDBOXES.md`,
"Capabilities as CLIs"). Sandbox Claude may add an argument to a capability so a forked Mini can do something new,
for example `--from-sheet` on `mail search`. The same capability is used by other sandboxes and their Minis.

## My answer: copy on write, additive only, promoted by the Builder

1. **A sandbox never edits the shared capability.** It gets an overlay: `<sandbox>/capabilities/<name>/` holds its
   changed copy, and the sandbox uses that copy from then on. Other sandboxes keep the shared one and don't see the
   change.
2. **Changes inside a sandbox are additive only.**
   - New arguments must be optional, with a default that keeps the old behaviour.
   - Defaults don't change, and nothing is removed or renamed.
   - So every existing Mini in that sandbox still runs the same.
   - The same import check applies as for transforms.
   - Its fake-data test and a preview run (through the two gates) must pass.
3. **Each Mini records the version it was built and tested with:** the capability name plus the hash of its code. A
   run with a different hash first replays the Mini's preview and compares. If the output differs, it says so
   rather than acting.
4. **Promotion goes through the Builder,** outside the sandbox:
   - The Builder sees the overlay, never the data.
   - It reviews the diff and the test, and publishes it as a new version of the shared capability.
5. **Other sandboxes opt in.**
   - They are told a newer version exists ("mail search can now limit to a sheet's people").
   - Upgrading replays each of their Minis in preview, and switches only if all still pass.
   - Nothing changes under a sandbox on its own.
6. **Actions are stricter.**
   - An added argument on a capability that writes, sends or books may only narrow what it does (filter, limit,
     skip). It can't widen it (new recipients, new targets).
   - Anything that widens is a Builder request to our team, as new actions are today.

## Why not simpler options

- **Shared and edited in place:** one fork's change could silently alter another team's leads Mini. That's the
  failure that makes people stop trusting Minis.
- **Every Mini vendors its own copy:** that's safe, but fixes never spread, and every sandbox drifts.

## To build

- The overlay folder and how capabilities are looked up: the sandbox's copy first, then the shared one.
- The additive check: compare old and new argument schemas, defaults and help text, and refuse a removal or a
  changed default.
- Mini records carry `capability@hash`. The replay-and-compare runs on a mismatch.
- A Builder view of the sandboxes' overlays (code and tests only) with Promote, plus an upgrade notice in the other
  sandboxes.
