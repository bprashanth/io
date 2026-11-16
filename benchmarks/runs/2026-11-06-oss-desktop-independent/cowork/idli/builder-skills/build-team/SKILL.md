---
name: build-team
description: The contract for extending an Idli team - the manifest, file readers, Analyst skills, tests, the sandbox they run in, and the capability menu. Read before changing anything in extensions/.
---

# Extending a team

A team's base (Drivey's) reads Excel, CSV and Google Sheets, hides private values as codes, charts and saves Minis.
You extend it in this folder. A capability counts only while its test passes, so untested work is never used.

## The folder

```
extensions/
  manifest.json        the capabilities (below)
  <reader>.py          a file reader
  tests/test_<x>.py    one test per capability; it passes when it exits 0
  samples/             fake files to build and test with (never real ones)
  skills/<name>/SKILL.md   an Analyst skill (optional)
```

## manifest.json

```json
{"capabilities": [
  {"id": "read-images", "title": "Read photos and scans of forms (text, line by line)",
   "kind": "reader", "reads": ["images"], "entry": "read_images.py", "test": "tests/test_read_images.py",
   "skill": "photo-tables", "analyst": "tables made from photos: check the confidence column"}
]}
```

- `id`: lowercase letters, digits and `-`. `title`: plain words the person reads on the team card.
- `kind`: `reader` (turns a kind of file into tables) or `skill` (only teaches the Analyst something).
- `reads` (readers): one or more of `images`, `audio`, `video`, `pdf`, `documents`.
- `skill` (optional): a folder in `skills/` copied to the Analyst at its next start.
- `analyst` (optional): one short line added to the Analyst's list of what the team can do.

## A reader

```python
import csv, os, capmenu          # capmenu is the platform's menu (lib/capmenu.py)

def read(src, out):
    """src: the downloaded file. out: an empty folder. Write one or more .csv files into out."""
```

- Each CSV becomes a file the person can review and send to the Analyst. **Column names matter**: Idli guesses
  which columns hold names, places or phone numbers partly from their names. When the page has a heading row, use
  it as the column names (`Name`, `Village`, `Mon`), not `column_1`. Keep the original text as it is; add a
  `confidence` or `source` column instead of guessing.
- For safety, Idli starts every text column of a reader's table as hidden (numbers and one- or two-letter marks
  such as P or A stay visible). The person can switch columns on in the privacy review.
- Then Idli does the rest: the privacy review hides names and places in your table, the Analyst gets masked
  copies, and Minis can be saved on it.

**It runs inside Idli's sandbox:** no network, the whole filesystem read only, home folders hidden. It can see
only the input file, the output folder, this folder and the platform's `lib/`. It can use the platform's Python
packages (pandas, openpyxl, Pillow, matplotlib) and the tools on the capability menu. Don't try to reach the
network, write elsewhere or install anything; it will fail.

## A test

```python
# tests/test_read_images.py runs from extensions/ inside the same sandbox; TMPDIR is writable
import csv, importlib.util, os, tempfile
spec = importlib.util.spec_from_file_location('r', 'read_images.py'); m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = tempfile.mkdtemp(); m.read('samples/register.png', out)
rows = list(csv.DictReader(open(os.path.join(out, 'lines.csv'))))
assert any('Asha' in r['text'] for r in rows), rows
```

Make the sample yourself with fake values (Pillow can draw a register; ffmpeg can make a short clip). Check
something real about the output, not just that a file exists.

## The capability menu (cheapest first)

| Need | Local (default) | Private model | Outside |
|---|---|---|---|
| OCR | `capmenu.ocr_text(path)`, `capmenu.ocr_words(path)` (Tesseract; words with position, line and confidence) | Muse vision: platform request | masked text after OCR, automatic |
| Speech to text | `capmenu.transcribe(path)` (faster-whisper) | platform request | masked text, automatic |
| Text to speech | `capmenu.speak(text, out_wav)` (Kokoro) | none | none |
| Video | `capmenu.ffmpeg(args)` | none | none |
| PDF | `capmenu.pdf_text(path)` (pdftotext) | platform request | masked text, automatic |

A function raises `capmenu.Missing` when this computer doesn't have the tool: then call `platform_request` and tell
the person it is a platform feature. The list in your CLAUDE.md says what this computer has.

## Finishing

`team_check` runs every test and lists what the team can do now. `team_save` (only after the tests pass) saves a
version with your one-line summary. The team picks it up on the next message, with no restart.
