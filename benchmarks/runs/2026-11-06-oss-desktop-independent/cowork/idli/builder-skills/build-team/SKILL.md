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
  sites/<app>/         site tools for web apps, run in a Chrome profile (below)
  stack/               the team's tools from Idli's catalog (optional, below)
    catalog.json       the catalog tools the team uses (written by Idli)
    pixi.toml          made by Idli from those tools; pixi.lock pins them
    stack.json         optional: {"model": true} if your code asks the private model, and
                       {"tasks": {"serve": "python tools/page.py"}} for a page
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
    `"tasks"` of stack/stack.json that serves the page on `127.0.0.1:$PORT`;
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

## Site tools (web apps in a Chrome profile)

A site tool is a `tool` that works in a web app (Gmail, Calendar, Sheets, a portal) in a Chrome profile. You learn
the app on the team's test accounts with the browser tools, then write it here. Idli runs it: on the test accounts
when you call `rehearse`, and later on the real account (a profile only Idli opens). You never touch the real one.

```
extensions/
  sites/gmail/find_new_leads.py     the tool: run(inputs, args, out)
  samples/pages/gmail-inbox.json    a page from the TEST account, saved with browser_read(save_as="gmail-inbox")
  tests/test_find_new_leads.py      runs with no browser (chromectl.Replay)
```

```json
{"id": "find-new-leads", "title": "Find new lead emails in Gmail", "kind": "tool", "takes": ["none"],
 "profile": "me", "entry": "sites/gmail/find_new_leads.py", "test": "tests/test_find_new_leads.py",
 "analyst": "args: {\"days\": 7}"}
```

```python
import chromectl                         # the platform's helper (lib/chromectl.py)

def leads(b, days):                      # the logic, written against a browser (real or Replay)
    b.open(f'https://mail.google.com/mail/u/0/#search/newer_than%3A{int(days)}d')
    page = b.read()                      # {'url','title','text','links':[{ref,text,href}],'controls':[{ref,kind,label}]}
    return [a['text'] for a in page['links'] if 'Enquiry' in a['text']]

def run(inputs, args, out):
    found = leads(chromectl.Browser('me'), args.get('days', 7))   # 'me' is the role in "profile"
    return {'count': len(found)}         # short: counts, ids. Real content stays on this computer.
```

```python
# tests/test_find_new_leads.py
import importlib.util, json, chromectl
spec = importlib.util.spec_from_file_location('t', 'sites/gmail/find_new_leads.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
b = chromectl.Replay([json.load(open('samples/pages/gmail-inbox.json'))])
assert m.leads(b, 7) == ['Enquiry about volunteering'], m.leads(b, 7)
```

- `chromectl.Browser(role)` has `open(url, new_tab=False)`, `read()`, `find(text)`, `click(ref=None, text=None)`,
  `type(ref, text, enter=False, clear=False)`, `tabs()`, `use_tab(n)`, `evaluate(js)` and `shot(path)`: the same as
  your browser tools.
- `"profile"` is one role or a list (`["me", "lead"]`). Each role must be a confirmed test account (`profiles`).
- It runs in Idli's wall with no network: the only way out is that profile's browser. No stack (`"stack"` stays off).
- **Draft, don't send.** Tools prepare: a draft email, a calendar entry to confirm, a row to check. The person sends.
  Never write a tool that sends WhatsApp messages.
- Read pages by stable addresses and visible names (`aria-label`, button text), not by position. Google changes its
  pages: the saved samples and tests show when a tool broke.
- Return short results (counts, ids, yes/no). The Analyst and you never get real emails or names back.

## The stack: tools from Idli's catalog

When the menu below doesn't have what the team needs, add tools from **Idli's vetted catalog**. Nothing else is
installed: no packages, repos or downloads you pick yourself.

1. **Pick.** `catalog` lists the tools built for this computer's system (Linux, Mac or Windows; never install one
   for another system). Each has what it is for, its licence, cautions (for example a non-commercial licence), its
   size, and what it needs (disk, memory, cores, GPU). `catalog(example="<id>")` shows a short script using it.
2. **Check.** Each tool says whether it fits this computer and, if not, why. If it doesn't fit, tell the person
   plainly and offer a smaller tool, the platform (`platform_request`), or a request (step 3). Say the size and any
   caution before installing.
3. **Ask.** If nothing fits, `catalog_request(need, why, tools_considered)` in general words, with no names, places,
   files or anything from the team. Tell the person our team will check a safe tool and add it. Meanwhile, offer
   what can be done now.

- **Install:** `stack_install(tools=["<id>", ...])`. Idli checks this computer again and refuses with the reasons,
  or asks the person with a summary it writes from the catalog. Tools add to what the team has. Idli writes
  `stack/catalog.json`, `stack/pixi.toml` and `stack/pixi.lock` (don't edit them); teammates get the same.
  The environment and the models live in Idli's tools folder, shared between teams. The person can remove tools on
  the Installed tools page (in Teams).
- **Your code** goes in `stack/tools/`. Model files are at `$IDLI_MODEL_<NAME>` (the model's name in capitals,
  other characters as `_`), all of them in `$IDLI_MODEL_PATHS` (JSON), under `$IDLI_MODELS`. Hugging Face and
  transformers run offline: load from those paths, never by a hub name.
- **Run:** no internet at all (on Linux inside Idli's wall). The stack is read only; write to `$IDLI_OUT` or a temp
  folder. With `"model": true` in `stack/stack.json`, `$IDLI_MODEL_URL` reaches the private model and nothing else.
- **Try:** `stack_run` runs a command from `stack/` (`python tools/x.py ../samples/a.wav`).
- **Threads:** use `$IDLI_THREADS` for any thread count (`cpu_threads=int(os.environ.get('IDLI_THREADS', 4))`).
  Never all cores: on some computers that runs many times slower.
- **Logins and sending:** a stack never logs in to accounts and never sends messages. Web apps are driven by site
  tools (below), which run without the stack.
- **Older teams** may have a hand-made `stack/pixi.toml` and `stack.json` from before the catalog. They keep
  working (`stack_install` with no tools reinstalls them). Don't add to them; new tools come from the catalog.

## The capability menu (cheapest first)

| Need | Local (default) | Private model | Outside |
|---|---|---|---|
| OCR | `capmenu.ocr_text(path)`, `capmenu.ocr_words(path)` (Tesseract; words with position, line and confidence) | The 9B with vision, from a stack with `"model": true` (best on handwriting and Hindi; tested 2026-11-17) | masked text after OCR, automatic |
| Speech to text | `capmenu.transcribe(path)` (faster-whisper) | platform request | masked text, automatic |
| Text to speech | `capmenu.speak(text, out_wav)` (Kokoro) | none | none |
| Video | `capmenu.ffmpeg(args)` | none | none |
| PDF | `capmenu.pdf_text(path)` (pdftotext) | platform request | masked text, automatic |

A function raises `capmenu.Missing` when this computer doesn't have the tool: then add a catalog tool for it to the
team's stack instead. The list in your CLAUDE.md says what this computer has.

## Finishing

`team_check` runs every test and lists what the team can do now. `team_save` (only after the tests pass) saves a
version with your one-line summary. The team picks it up on the next message, with no restart.
