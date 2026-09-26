# 2026-09-16, 12:15 IST — laptop: checking the DGX's work, and one thing that will not install

Machine: Pop!_OS 22.04, kernel 6.12, x64, GNOME on X11, python 3.10.12. Verifies the four
DGX entries of 2026-09-15 on hardware that has a display and a real desktop. Screenshots in
`benchmarks/runs/2026-09-16-laptop/` (untracked, as the rule now says). **Incomplete: the
session was stopped part way through a repro; the open thread is at the end.**

The wall runs natively here. `sandboxCheck` answers ok with `/usr/bin/bwrap` and no AppArmor
grants are needed, because Pop!_OS 22.04 does not carry
`kernel.apparmor_restrict_unprivileged_userns`. That is the distribution difference the DGX
entry predicted, seen from the other side.

## The one that blocks a fresh install

`pins.json` now pins `matplotlib==3.11.2`, which requires **python >= 3.11**. `install.sh`
declares python **3.10+** as supported (line 16) and runs under `set -euo pipefail`, so on a
3.10 machine it aborts at `pip install $REST` before the scanner is ever fetched:

    ERROR: Could not find a version that satisfies the requirement matplotlib==3.11.2
    ERROR: No matching distribution found for matplotlib==3.11.2

This laptop is such a machine, and so is any Ubuntu 22.04 or Pop!_OS 22.04 participant
laptop. The newest matplotlib for 3.10 is 3.10.9. Either pin that, or raise the floor in
`install.sh` and say so in the install docs - but raising the floor excludes 22.04, which is
the commonest machine in the room. Not fixed here: it is a pin choice, and the DGX agent
should make it deliberately. I installed 3.10.9 locally to get the rest of the testing done.

## Verified, with the model in the loop and a real desktop

**A conversation no longer codes the person's words.** Typed "what is the capital of france?
my number is 9876543210 and Ramesh lives in Kandura" into the chat box with no folder open.
What left the machine, read from the proxy dump:

| in the question | what left |
|---|---|
| `capital of france` | `capital of france` |
| `my number is 9876543210` | `my number is PHONE_001` |
| `and Ramesh lives in Kandura` | `and Ramesh lives in Kandura` |

The validator still catches a phone; the scanner no longer invents codes for words the
person typed. The answer came back "The capital of France is Paris." The 2026-09-15 defect
is gone.

**Charts, offline.** Under T4GC tools with network off, Codex read the CSV with pandas
inside the wall and drew `households_per_village_top_8.png` with matplotlib. io's folder
watcher noticed it and the viewer opened with the chart, real village names, the bar reading
"this window has no internet, so nothing on the page can send your data anywhere", and a
footer chip offering to show it again.

**The renderer, and the escalation that stays closed.** Asked for a page and a render.
`Called io.render_page({"file":"visits.html"})` ran with **no approval prompt of any kind**,
under `codex -p io -a never`. This is the thing the laptop could not have before: the tool
channel and the escalation lock are no longer the same switch.

The toolbox window shows both sides at once, which is the clearest evidence in this whole
thread:

| what the assistant was shown | what the person sees |
|---|---|
| `NAME_566 / PLACE_003 / PHONE_304` | `U. A. Pillai / Karpi / 099433-78529` |
| `NAME_567 / PLACE_033 / PHONE_305` | `Milind Lobo / Dobhi / 093161-22451` |

Codex's own summary: "Picture of visits.html (1100x773). Names, places and phone numbers
show as codes in it; that is expected."

**The setting can be changed mid-thread.** T4GC tools → Open → Offline, twice through. Each
switch rewrote the profile and relaunched as `codex resume --last -p io -a never`; the whole
conversation stayed on screen across both. Offline writes no `[mcp_servers.io]` table at all,
so it has no toolbox, by construction.

**The resolver grant matters here too.** Pop!_OS also symlinks `/etc/resolv.conf` into
`/run/systemd/resolve`, so without the grant Open would have had network and no DNS on this
machine as well. Measured under Open: `HTTP=200 exit=0` against example.com. Under T4GC
tools and Offline the same command cannot resolve.

**Offline refuses to open a page.** Clicking the page link in the terminal and the footer
chip both opened nothing. Correct - and **silent**: the person is told nothing. `openViewer`
in `main.js` computes `canBrowser` and still opens the window; the refusal the person
actually meets comes from somewhere else and says nothing. Worth a line in the viewer or the
terminal saying this folder is set to stay offline.

## The open thread - a viewer that does not come back

After the viewer had been open once and then closed, it never opened again in that run:
neither the folder watcher on a new chart, nor the footer chip, nor the page link. A new
chart file was written correctly each time; no window appeared.

The Electron log says why, and it is not io's logic:

    EGL Driver message (Error) eglSwapBuffers: Failed to retrieve the size of the parent window
    GPU process exited unexpectedly: exit_code=8704
    GPU process exited unexpectedly: exit_code=139
    XGetWindowAttributes failed for window <the viewer>
    ContextResult::kTransientFailure: Failed to send GpuControl.CreateCommandBuffer

The GPU process segfaults when the viewer window closes, and afterwards no new
`BrowserWindow` can get a command buffer, so the viewer silently never appears again. On
this machine that is one crash away from "charts stopped working" with nothing on screen to
explain it.

**Not yet established** and the first thing to do on resume: whether this reproduces from a
clean start, or whether it needed the way the window was closed. A clean repro was set up
and got as far as step 1 (fresh app, chart written, viewer opened, id 54525979) before the
session ended. Steps remaining: close the viewer with its own window button, ask for a second
chart, and see whether the viewer returns. If it does not, try `--disable-gpu` or
`--in-process-gpu` to separate a driver bug on this box from something io can fix. The GPU
errors are specific to this laptop's stack, so it may not reproduce on the DGX under Xvfb,
which is exactly why it belongs here.

## Also seen

- Opening the viewer re-tiles the main io window into a quarter of the screen on GNOME; the
  terminal becomes 480px wide and the footer wraps into three lines. Cosmetic, environmental,
  but it is what a person on this desktop gets.
- The toolbox entry says the renderer "cannot render a chart image", which is right and
  worth keeping: a PNG's labels are pixels and cannot be coded.

## Tests

31 proxy, 15 launcher, both passing here with matplotlib 3.10.9 installed.
