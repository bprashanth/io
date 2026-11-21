# Team stacks: what's left

Context: [TEAM_STACKS.md](../../../narrative/TEAM_STACKS.md), built and tested on the DGX on 2026-11-17. In order:

1. **The laptop run.** It needs the owner's Tailscale browser check once, so the laptop can `git fetch dgx`. Then:
   - sync and install pixi (x86_64) into `~/idli-insights/platform/bin`;
   - run Teams > New team end to end in Paseo (cards, then the Builder in the team's workspace, then the install
     prompt in that terminal);
   - install Event Media's stack from its locks on x86 (the first cross-architecture teammate test).
2. **Share and join.** A team bundle is the extensions definitions only (not their git history: two test teams'
   histories carry gigabytes from before the ignore fix), uploaded to silo.
   - Joining shows the same install prompt and installs with `pixi install --locked` (`IDLI_STACK_LOCKED=1` today).
   - It refuses any repo commit or download sha256 that doesn't match.
3. **Tool outputs into the privacy review.** A tool's tables (a marked leads sheet, a transcript) land in
   `outputs/`. They should become workspace files with masked copies, as reader tables do, so the Analyst can keep
   working on them.
4. **Speech to text as a platform private model.** Whisper on CPU ran at about 0.6 to 4 times real time on the
   DGX. A GPU Whisper server next to the 9B, reached through the stack's model door, would make D2, H1 and H4 fast.
   Menu entry: "the platform's speech-to-text".
5. **The Windows and macOS walls:** an Idli WSL2 image (`wsl --import`) and a Lima (or Apple container) VM, both
   running the same `stackwall.py`. Measure the first-install time and size on a normal laptop.
6. **Answers that quote their source.** H1's chatbot gave a wrong month with the FAQ in front of the 9B. Pages and
   tools that answer from a document should show the line they used.
7. **Fewer install prompts on a first build.** D1 asked 8 times, mostly from bugs since fixed. The H runs asked 0 to
   3 times. Consider one prompt per plan, listing everything, and asking again only for additions (as now).
