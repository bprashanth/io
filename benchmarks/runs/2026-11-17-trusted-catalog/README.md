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

To be filled in by the runs.
