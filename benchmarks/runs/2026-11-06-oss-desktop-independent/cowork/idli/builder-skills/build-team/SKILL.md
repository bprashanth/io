---
name: build-team
description: The contract for extending an Idli team - the manifest, file readers, tools, pages, Analyst skills, tests, the team's stack of open-source tools, the wall they run in, and the capability menu. Read before changing anything in extensions/.
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
  stack/               the team's own tools from the internet (optional, below)
    pixi.toml          packages and tasks; pixi.lock pins them at the first install
    stack.json         GitHub repos, downloads, extra hosts, private model use
    tools/             your code that uses the stack
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
- `kind`:
  - `reader`: turns a kind of file into tables (the person reviews them; the Analyst gets masked copies);
  - `tool`: does something to the original files on this computer and writes new files (a cut video, a translated
    document, an audio reply). The Analyst runs it with `team_run`, after working out what to do from masked
    tables. Needs `takes` (file kinds, or `none`) and an `entry` with `run(inputs, args, out)`;
  - `app`: a page the person uses in a browser tab (a voice chatbot, a form). Needs `serve`, a task in
    stack/pixi.toml that serves the page on `127.0.0.1:$PORT`;
  - `skill`: only teaches the Analyst something.
- `stack` (optional, true): the entry and test run with the stack's Python and packages, in the stack's wall.
- `reads` (readers): one or more of `images`, `audio`, `video`, `pdf`, `documents`.
- `skill` (optional): a folder in `skills/` copied to the Analyst at its next start.
- `analyst` (optional): one short line added to the Analyst's list of what the team can do. For a tool, say what
  `args` it takes, for example `args: {"keep": [[start_s, end_s], ...]}`.

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

## A tool

```python
def run(inputs, args, out):
    """inputs: original files (paths). args: the Analyst's instructions (JSON). out: an empty folder for results.
    Return a short dict (counts, durations). Never return the file's content: it goes to the Analyst."""
```

The pattern for media: a **reader** turns the file into signals (a timeline of who is speaking when, how many
people are in frame, scene changes) with no names, faces or words in it. The Analyst decides from that table. A
**tool** then does the work on the original (ffmpeg cuts at the Analyst's timestamps). Neither the Analyst nor you
ever see or hear the original.

## A page (app)

A small web page served from the stack (plain HTML with a tiny Python server, or Gradio). Idli runs it inside the
wall and opens it in a tab; the person's browser reaches it, it reaches nothing. Its working folder is `$IDLI_OUT`.
If it needs the private model, it calls `$IDLI_MODEL_URL` (OpenAI-style `/chat/completions`, model
`$IDLI_MODEL`, send `"chat_template_kwargs": {"enable_thinking": false}`). Test its logic in a normal test (import
its functions), not by opening it.

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

## The stack: tools from the internet, inside Idli's wall

When the menu below doesn't have what the team needs, add open-source tools to `stack/`:

```toml
# stack/pixi.toml
[workspace]
name = "team-stack"
channels = ["conda-forge"]
platforms = ["linux-64", "linux-aarch64"]

[dependencies]          # conda-forge first: it has ffmpeg, opencv, onnxruntime and most science packages
python = "3.11.*"
ffmpeg = "*"

[pypi-dependencies]     # only what conda-forge lacks
silero-vad = "==5.1.2"

[tasks]
fetch-models = "python tools/fetch_models.py"   # optional; runs once at install, with the install wall's internet
```

```json
// stack/stack.json
{"why": "Find speech and people in event videos",
 "repos": [{"url": "https://github.com/owner/repo", "ref": "v1.2.0", "license": "MIT", "why": "..."}],
 "downloads": [{"url": "https://huggingface.co/.../model.onnx", "to": "models/model.onnx"}],
 "setup": "fetch-models",
 "hosts": [],
 "model": false}
```

- **Choosing a tool:** well known and maintained, a permissive licence (MIT, Apache, BSD), runs on a normal laptop
  CPU, as small as will do. Prefer a package over a repo, and a repo's release tag over a branch. Say in `why`
  what each one is for.
- **Install:** `stack_install`. Idli asks the person first, with a summary it writes from these files. The install
  wall reaches only package and code hosts (conda-forge, PyPI, GitHub, Hugging Face). Anything else must be listed
  in `hosts`, and the person sees it. Model weights are fetched now, by `downloads` or the `setup` task, never at
  run time. The first install pins everything (pixi.lock, stack-lock.json); teammates get exactly the same.
- **Run:** no internet at all. The stack is read only; write to `$IDLI_OUT` or a temp folder. Repos are in
  `stack/repos/<name>`, downloads where `to` says, Hugging Face's cache in `stack/models/hf` (offline). With
  `"model": true`, `$IDLI_MODEL_URL` reaches the private model and nothing else.
- **Try:** `stack_run` runs a command from `stack/` in the run wall (`python tools/x.py ../samples/a.wav`).
- **Threads:** use `$IDLI_THREADS` for any thread count (`cpu_threads=int(os.environ.get('IDLI_THREADS', 4))`).
  Never all cores: on some computers that runs many times slower.
- **Size:** say roughly how big it is before installing if it is large (deep-learning packages are 1 to 3 GB).
- **Logins and sending:** a stack never logs in to accounts and never sends messages. That is the platform's:
  `platform_request`.

## The capability menu (cheapest first)

| Need | Local (default) | Private model | Outside |
|---|---|---|---|
| OCR | `capmenu.ocr_text(path)`, `capmenu.ocr_words(path)` (Tesseract; words with position, line and confidence) | The 9B with vision, from a stack with `"model": true` (best on handwriting and Hindi; tested 2026-11-17) | masked text after OCR, automatic |
| Speech to text | `capmenu.transcribe(path)` (faster-whisper) | platform request | masked text, automatic |
| Text to speech | `capmenu.speak(text, out_wav)` (Kokoro) | none | none |
| Video | `capmenu.ffmpeg(args)` | none | none |
| PDF | `capmenu.pdf_text(path)` (pdftotext) | platform request | masked text, automatic |

A function raises `capmenu.Missing` when this computer doesn't have the tool: then add a tool for it to the
team's stack instead. The list in your CLAUDE.md says what this computer has.

## Finishing

`team_check` runs every test and lists what the team can do now. `team_save` (only after the tests pass) saves a
version with your one-line summary. The team picks it up on the next message, with no restart.
