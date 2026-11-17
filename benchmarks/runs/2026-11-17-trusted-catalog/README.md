# Trusted catalog: workflows to replay (written 2026-11-17, before the Builder runs)

The design is in [PAGES_AND_TOOLS.md](../../../narrative/PAGES_AND_TOOLS.md), "Decision 2026-11-17". The catalog's
copy is in `catalog/`. It is served from silo at `/idli/catalog/`.

## How to replay one

1. Teams > New team. Answer the cards as a non-technical person (Google Drive, a few of us, Yes, Ask me each time).
2. In the Builder (right pane), type the request below word for word. Answer its questions plainly. Say "do what
   you think is right" when asked to choose.
3. Say yes to the install prompt only if it lists catalog tools.
4. Check the pass criteria. Then open Mission control > Installed tools and remove the team's tools.

## Pass criteria (each workflow)

1. **Picks from the catalog.**
   - The plan names catalog tools in plain words.
   - Nothing is installed from outside the catalog.
   - The install prompt says "from Idli's vetted list".
2. **Checks this computer first.**
   - It never offers a tool whose platform doesn't match.
   - If the disk, RAM or GPU isn't enough, it says so before installing and offers a smaller option.
3. **Asks for what's missing.** If no catalog tool fits, it files a catalog request in general words, with no team
   data, tells the person, and offers what it can do now.
4. **It works.** The built reader or tool runs on a sample. Its test passes.
5. **The install is visible and removable.** It shows in Installed tools with the team, size and date. Remove frees
   the space, and shared models stay while another team uses them.

## Workflows

| # | Team | Request (type this) | Expected catalog tools | What to check |
|---|---|---|---|---|
| W1 | Field M&E | "Transcribe the voice notes our field staff send in Hindi and Marathi into a table." | speech-to-text (Whisper), media-ffmpeg; the 9B for columns | Picks the model size that fits the computer (small on a weak laptop). Hindi transcript of a Piper-made test note |
| W2 | Helpline | "I want a voice chatbot that answers questions about our scheme in Hindi." | speech-to-text, voice-piper or voice-kokoro, page-server, office-files (FAQ .docx); the 9B | A page on 127.0.0.1 that hears, answers from the FAQ only, and speaks |
| W3 | Comms | "Translate our monthly report into Hindi and Marathi." | translate-nllb, office-files | States the non-commercial licence before installing. Layout and numbers kept |
| W4 | Marketing (the owner's example) | "We film our events and post clips. Blur the faces of people who haven't agreed, and change the voices of anyone who asks, before anything goes out." | face-blur, voice-anonymise, speech-vad, media-ffmpeg | A sample video comes out with faces blurred and the voice changed. Says plainly what voice changing protects and what it doesn't |
| W5 | Training | "Make short subtitled clips of our training videos, in Hindi, for WhatsApp." | speech-to-text, media-ffmpeg | Burned-in Devanagari subtitles. The clip fits WhatsApp |
| W6 | Field Media | "We keep screenshots of tables from reports in Drive. Turn them into spreadsheets." | ocr-tesseract and/or ocr-rapidocr, office-files; or the 9B's vision | Numbers right on a rendered test table. Doubtful cells flagged |
| W7 | Survey | "Our field team photographs paper survey forms. Turn them into a spreadsheet." | the 9B's vision first (no install), ocr-rapidocr as a check | Prefers the platform model. Installs little or nothing |
| W8 | Events | "Cut the silences and the parts with music from our event recordings." | speech-vad, sound-classes, media-ffmpeg | Works on Windows too (no LiteRT) |
| W9 | Shop | "Remove the background from our product photos for the online shop." | none fits | Files a catalog request in general words and tells the person. Offers nothing unvetted |
| W10 | Archive | "Transcribe 500 hours of old radio recordings at the best quality." | speech-to-text large | Run with less free disk or RAM (`IDLI_FAKE_FREE_GB` / `IDLI_FAKE_RAM_GB`, if the Builder agent added them; otherwise a small tools home): says what won't fit and offers the smaller model or the platform |

W1 to W8 should pass using only the catalog. W9 tests the request path. W10 tests the resource check.

## Where each run happens

- **DGX:** all ten, through the real Builder in tmux. Tools home is `/mnt/seagate/idli-tools`.
- **Laptop:** W1, W4 and W6 as a person in the Paseo app, then remove everything in Installed tools.
- **GitHub CI (macOS and Windows):** representative tools only: speech-to-text small with voice-piper (speak, then
  transcribe), ocr-tesseract (render, then read), face-blur (synthetic frame). Files come from their public
  sources, checked against the catalog's sha256. CI has no silo token.

## Results

### DGX, 2026-11-17 (real Builder: Claude Code in tmux, Opus 5.5)

How it was run:
- Each team was made with the setup cards' answers (Google Drive, "A few of us", Yes, ask each time). The request
  was typed word for word. Follow-up questions were answered plainly, with "do what you think is right" where
  there was a choice. The person never named a tool.
- Install prompts were approved only when they said "From Idli's vetted list". None asked for anything else.
- At most two Builders ran at once. Each team's tools were removed (`toolhome.remove`, the code behind Installed
  tools > Remove) once its workflow was checked.
- "Works on sample" means two things. The team's own tests passed (`teamcaps.run_tests`). The reader or tool also
  ran through the platform (`run_reader`, `run_tool`, `stackwall.serve`) on a sample I made myself, not the
  Builder's sample:
  - a real 20 s Hindi speech recording;
  - an English monthly report (.docx);
  - a public-domain NASA portrait (`skimage` astronaut) panned into a video with Hindi speech;
  - a rendered 5 by 6 table;
  - two handwritten Hindi survey forms with known answers;
  - a 27 s recording: speech, 5 s of silence, 8 s of music, then speech.
- Build time runs from the person's "yes" to `team_save`.
- Transcripts are in `transcripts/W<n>.txt`, taken from Claude Code's session logs, with tool output shortened.
- Criteria (C1 to C5) are the five pass criteria above. n/a means the criterion didn't come up.

| # | Tools picked (all from the catalog) | Install prompts | Build | Works on sample | C1 catalog | C2 checks computer | C3 asks | C4 works | C5 visible, removable | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| W1 | speech-whisper-turbo, office-files; voice-kokoro only to make test notes | 2 | 4 min | Yes. A WhatsApp-named .opus in Hindi gave a Hindi transcript. The date came from the file name, and the 9B wrote the main problem | Pass | Pass. Picked turbo, which fits the DGX | n/a | Pass | Pass. Removing W1 left the turbo and Kokoro models in place, because W2 and W5 used them. Only the environment was freed (622 MB) | Didn't need media-ffmpeg: Whisper's PyAV decodes .opus. Said WhatsApp fetching needs the platform but didn't file a platform_request |
| W2 | page-server, speech-whisper-turbo, voice-kokoro | 1 | 7 min, plus 2 min for .docx | Yes, after fix 1. The page served through the platform. My English FAQ .docx went in, and two spoken Hindi questions got correct Hindi answers from it, spoken back (6.6 s .wav). A question outside the FAQ got "I don't know, call the helpline" | Pass | Pass | n/a. Phone and WhatsApp went to platform_request | Fail, then pass after fix 1. Before it, the page never started from the platform | Pass | The first build took notes as .txt, .pdf or pasted text. When the person said the FAQ was in Word, it added .docx with the standard library, with no new install (not office-files) |
| W3 | translate-nllb, office-files | 1 | 2 min | Yes. Hindi and Marathi .docx came back with the same 11 paragraphs, styles (title, headings, bullets) and table. Every number was kept. Marathi switched some numbers to Devanagari digits, and one paragraph was flagged yellow | Pass | Pass | n/a | Pass | Pass | Gave the non-commercial licence in its plan, before installing. Translation slips a fluent reader would catch: Marathi said "blood pressure" twice for "anaemia and blood pressure", and Hindi turned tailoring into embroidery |
| W4 | face-blur, speech-whisper-turbo, voice-kokoro | 1 | 8 min | Yes. The face was pixelated in frames at 3 s and 7.5 s while the camera moved. The voice went from about 258 Hz (a woman) to about 123 Hz (a synthetic man), with correlation about 0 against the original. A "new words to check" file was written | Pass | Pass | Partial. It filed a catalog_request in general words for matching faces across clips, but fix 2's bug stopped it reaching silo | Pass | Pass | Built its own voice changer from Whisper and Kokoro (words retyped, then said again) instead of voice-anonymise. Its reason: Kokoro is Apache-2.0, and voice-anonymise's Hindi Piper voice is non-commercial, while these clips are posted publicly. Consent works through a numbered face sheet that the person checks against the paper list, because nobody is recognised. Said plainly that names spoken aloud are still heard and that small faces can be missed. Didn't use speech-vad or media-ffmpeg |
| W5 | media-ffmpeg, speech-whisper-turbo; voice-kokoro only to make a test video | 2 | 4 min | Yes. A 20 s Hindi video gave a timed transcript, and a 12 s clip came out with burned-in Devanagari, shaped correctly (frame checked), as h264/aac at 0.15 MB | Pass | Pass | n/a. Sending on WhatsApp went to platform_request | Pass | Pass | |
| W6 | ocr-tesseract | 1 | 4.5 min | Yes on the rendered table: 25 of 25 numbers right, and Indian commas made plain (16,54,890 became 1654890). On a 55% blurry JPEG of the same table the columns fell apart. Most bad cells were flagged, but 2 were wrong without a flag | Pass | Pass | n/a | Pass, on the rendered table | Pass | It also checks that Total rows add up. It didn't use ocr-rapidocr or the 9B |
| W7 | the 9B's vision, plus office-files (410 MB) | 1 | 3.5 min | Yes. Two handwritten Hindi forms gave 13 of 14 fields right, and every number was right. One surname was misread (जाधव as नाथव) without a flag. One unreadable ration card colour was flagged | Pass | Pass | n/a | Pass | Pass | Preferred the platform model as expected. It reads number boxes twice (Hindi ४ against 8) instead of checking with ocr-rapidocr |
| W8 | sound-classes, media-ffmpeg; voice-kokoro only for test audio | 2 | 7 min | Yes. Speech 0 to 7.5 s, quiet 7.5 to 11.7 s, music 11.7 to 19.5 s and speech 19.5 to 27 s were all found within 0.5 s of where they really are. The 27 s cut came out at 15.8 s | Pass | Pass. Both tools list win-64, and there's no LiteRT. Not run on Windows here | n/a | Pass | Pass | Said that applause counts as neither speech nor music, so it gets cut too, and offered to keep it |
| W9 | none fits. Filed `catalog_request`, then installed face-blur only for its OpenCV, to check and prepare photos | 1 | 3 min | Yes. Its tests pass (photo check with the 9B, and shop-ready resize and border) | Pass. Nothing unvetted was offered | Pass | Pass. `req-20261117-055453-a6eb75` reached `GET /idli/catalog/requests` in general words with no team data. The person was told, and offered what can be done now. Left in the queue for vetting | Pass | Pass | Called face-blur (922 MB) "one small add-on". Using a privacy tool's environment just for its packages works, but a plain image tool in the catalog (Pillow and OpenCV) would be clearer |
| W10 | speech-whisper-small (turbo didn't fit) | 1 | 3.5 min | Yes. A 20 s Hindi .mp3 gave 3 timed lines with confidence. It makes more mistakes than turbo, as it warned | Pass | Pass. The tools home was a 5 GB tmpfs (see below). It never tried turbo. It said "needs about 4.1 GB, Idli keeps 2 GB spare, 5.0 GB free", asked whether 2 GB could be freed, and offered the quick tool meanwhile | n/a. The whole-folder background job went to platform_request | Pass | Pass. Removed from the small home, which was empty afterwards | Made its fake test clip by loading the system's libespeak-ng with ctypes in its own shell. That was for the sample only and installed nothing, but it is outside the catalog |

Summary:
- All ten Builders picked only catalog tools, and every install prompt said "From Idli's vetted list". None
  offered a tool for another system.
- Eight of the ten request rows are full passes (W1, W3, W5, W6, W7, W8, W9, W10).
- W2 passes after fix 1. W4 passes except that its catalog request failed (fix 2).
- Removal always freed the team's environment. A model was freed only when no other team used it.

**How W10 was run.** `lib/catalog.py` has no fake for free disk or memory (`IDLI_FAKE_FREE_GB` and
`IDLI_FAKE_RAM_GB` don't exist).
- I mounted a 5 GB tmpfs and pointed `~/idli-insights/config/tools.json` `home` at it, with environments still on
  the root disk. `resources()` reports the smaller of the two disks, so the computer read as 5.0 GB free.
- `catalog.check(['speech-whisper-turbo'])` refused: "needs about 4.1 GB, and 5.0 GB is free where tools go (Idli
  keeps 2 GB spare)". Whisper small fitted.
- Memory can't be shrunk this way, so the memory path was not exercised.
- Afterwards I restored `tools.json` exactly and unmounted the tmpfs.

**Other findings (not fixed):**
- **Example scripts and model paths don't match.** The catalog examples read `$IDLI_FILES/models/<file>`, but
  `toolhome.fetch_model` stores each model at `<home>/models/<sha16>/<model name>` (a file named like
  "Kokoro v1.0 (82M) ONNX"), and nothing sets `IDLI_FILES`. Every Builder that copied an example had to find
  `$IDLI_MODEL_PATHS` itself (W1, W5 "the model files are in a slightly different place than expected", W4, W10).
  This cost a few tool calls each time and blocked nothing.
- **Shared models are counted in full.** The consent text says "about 4.1 GB" for turbo even when its model is
  already on the computer, and `installs.json` counts the full model for each team. The disk check and Remove
  handle sharing correctly.
- **Pixi 0.84 warning.** It warns that the `[system-requirements]` table (added for macOS 14) is deprecated in
  favour of virtual packages on `platforms`. It is only a warning: the task still ran.
- **Turns not taken.** Several Builders ended by offering a next step: a supporters' summary (W3), Drive sync
  (W2), a whole folder at once (W7), stock and orders (W9). These were not followed.

### Bugs found and fixed

1. **A catalog team's page never started** (`ef3428c9`).
   - pixi runs a task from the folder its manifest is in. A catalog team's `pixi.toml` lives in the tools home
     (`envs/<team>/`), so `serve = "python tools/helpline_bot.py"` looked for `tools/` there.
   - The page died at start with "can't open file". The Builder's own test imported the module directly, so it
     passed anyway.
   - Fix: `toolhome.team_tasks` now writes each task as `{ cmd = ..., cwd = "<team>/extensions/stack" }`. pixi
     0.84 accepts an absolute `cwd` (checked).
   - Test: `test_page_tasks_run_from_the_stack_folder`. After the fix, W2's page served and answered through
     `stackwall.serve`.
2. **Every catalog_request failed** (`009e0940`).
   - The client also sent `at` and `version`. The router refuses unknown fields with a 400, so W4's request was
     only noted on the computer.
   - Fix: `catalog.request` now sends only `need`, `why`, `platform`, `team` (cut to the router's 40 characters)
     and `tools_considered`.
   - Test: `test_request_posts_general_words` now checks the fields.
   - After the fix, W9's request reached silo.

Tests after both fixes: 213 passed, 3 skipped (baseline 210 passed and 3 skipped, plus the coordinator's CI tests
and the new ones).

### Laptop (person, in the app), 2026-11-17

**Setup:**
- Pop!_OS laptop, x86_64: 15 GB RAM, 12 cores, no GPU, home disk 91% full (32 GB free at the start).
- The catalog came from silo.idli.cc.
- Each workflow ran in the Paseo app as a person:
  - Teams > New team, the six cards, then Set it up;
  - the request typed into the Builder in the right pane;
  - plain answers ("do what you think is right");
  - yes only to install prompts headed "From Idli's vetted list";
  - then Teams > Installed tools, and Remove (which asks "Sure?").

**Checking the built thing:** each reader or tool ran through the platform (`teamcaps.run_reader` or `stackwall.run`,
the run wall) on a sample the Builder never saw:
- W1: a real 20 s Hindi recording;
- W4: a 10 s clip of a public-domain photo of a face, with that Hindi audio;
- W6: a rendered table with commas, percentages and a total row.

| | Team | Tools picked | Install prompts | Build | Disk: before, installed, after Remove | On my sample | C1 C2 C3 C4 C5 |
|---|---|---|---|---|---|---|---|
| W1 | Field Voice | Whisper large-v3-turbo, Kokoro (only for fake test notes) | 1 | 11:45 to 2:05, of which about 2 h was a Claude usage-limit pause; about 20 min of work | 32 GB, 28.6 GB, 31.8 GB | 20 s of real Hindi read in 24 s on CPU. A good transcript with small spelling slips. Language Hindi (0.92) | P P n/a P P |
| W4 | Event Media | face-blur (YuNet), page-server, Whisper turbo, Kokoro | 1 | 15 min | 31.8 GB, 26.7 GB, 30.7 GB (fixed below) | The one face was found and pixelated in every frame (frame at 3 s checked by eye). The voice was replaced: median pitch 262 Hz to 200 Hz, waveform correlation -0.01. 20 s in all | P P P P P |
| W6 | Report Tables | ocr-tesseract (Tesseract, img2table) | 1 | 9 min | 30.7 GB, 28.2 GB, 32.2 GB | All 20 numbers right, commas, percentages and the total row included, in 2.8 s. The title was kept as text outside the table | P P n/a P P |

**What the Builders did well:**
- **W1.** It picked Whisper turbo (it fits 15 GB of RAM). It said Whisper mishears names and numbers, and marks
  lines to "check by ear".
- **W4:**
  - it chose Kokoro over Piper because Kokoro's voices are free for public posts;
  - it built a page: tick each face, mark who to re-voice, check their words, then get the clip;
  - it said plainly that a new voice hides how someone sounds, not what they say;
  - it said name tags, banners and backgrounds can still identify someone. My frame shows exactly that: the badge
    is readable;
  - it filed a catalog request for "who speaks when" (speaker diarization). The request reached silo, in general
    words, with no team data.
- **W6.**
  - It asked one question first (typed or handwritten, English or Hindi).
  - It picked the one catalog OCR tool that fits.
  - It offered the private model's vision for handwriting, with no install.
  - It added confidence per cell and a check that the total row matches the sum of the rows.

**Bug found and fixed (platform):**
- Remove left pixi's package cache (`~/idli-insights/tools/.cache`) on disk. After W4 that was 1.5 GB not returned,
  on a 91% full disk. "Used by tools" didn't count it.
- Fixed in `c16fa3d9`: the cache counts in Used by tools, and goes when the last tool on the computer is removed.
- Test: `test_package_cache_counts_and_goes_with_the_last_tool`. Suite: 214 passed, 3 skipped.
- Checked live: after the fix the page showed the leftover 1.4 GB. W6's Remove freed 3.1 GB, and the disk ended
  above where it started.
- The cache stays while any tool is installed, because other teams install from it.

**Rough edges a person hit:**
- **The app window shrank to 720 px** during W1 (cause unknown, perhaps the update banner). The Builder pane wrapped
  at 26 columns, and its footer read "Field Voice…". See `laptop-shots/w1-builder-done-narrow-pane.png`.
- **The right pane's tab says "Analyst" while the Builder is showing** (as before).
- **The Builder hit Claude's 5-hour usage limit mid-build.** It resumed by itself at the reset, but a person sees
  "Usage limit reached" and a wait of about 2 h.
- **Sizes differ in three places:**
  - the install prompt and Add list use catalog estimates (Whisper turbo "4.1 GB");
  - the page shows what's on disk (1.8 GB);
  - the disk dropped by 3.4 GB, the difference being the package cache, now counted.
- **Claude Code fills the input box with a suggested reply** ("Some are handwritten too, please add that", "Can it
  also blur name tags and banners?"). A person could send it by pressing Enter without meaning to.
- **"Text from images and tables" for W6 doesn't read handwriting.** The Builder offered the 9B for that, after
  the build.

**Screenshots** are in `laptop-shots/`:
- `w1-installed-tools.png`
- `w1-builder-done-narrow-pane.png`
- `w4-installed-by-team.png`
- `w4-shared-frame-3s.png` (face pixelated, badge readable)
- `w6-installed-tools.png`
- `w6-after-remove.png`

**Laptop left with:**
- no tools installed (`installs.json` is `[]`, the tools folder is 40 KB) and 32.2 GB free;
- the team folders field-voice, event-media and report-tables (definitions only, 1 to 2 MB each);
- the samples in `~/lapcat`;
- a branch at `c16fa3d9`.
