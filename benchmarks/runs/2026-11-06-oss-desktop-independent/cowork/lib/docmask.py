"""PDFs that come with spreadsheets in a sandbox (owner, 2026-11-18): they go to Claude too, as masked text.

A folder of PDFs and Excel or CSV files, with a question, goes to Sandbox Claude after masking, the same as files:
- the spreadsheets through the privacy review, as always (lib/home.prepare, lib/maskcopy);
- each PDF's text, read here (pypdf), then masked with the folder's known values, the rules and the name scanner
  (lib/privacy.mask_account_text: the codes are kept, so Claude's replies show the person the real values again),
  written to Claude's folder as docs/<name>.txt. Claude never gets the PDF itself.
The text is read once per file version and kept beside the download.
"""
import json
import re
from pathlib import Path

from lib import home

CHUNK = 3000            # the name scanner's piece size
MAX_CHARS = 150_000     # about 50 pages; the rest is left out and the file says so


def pdf_text(path):
    cache = Path(str(path) + '.text.txt')
    if cache.is_file() and cache.stat().st_mtime >= Path(path).stat().st_mtime:
        return cache.read_text()
    from pypdf import PdfReader
    pages = []
    try:
        reader = PdfReader(str(path))
        for i, page in enumerate(reader.pages, 1):
            try:
                pages.append(f'[page {i}]\n' + (page.extract_text() or '').strip())
            except Exception:  # noqa: BLE001  (one bad page: skip it)
                pages.append(f'[page {i}: could not be read]')
    except Exception:  # noqa: BLE001
        return ''
    text = '\n\n'.join(pages)
    cache.write_text(text)
    return text


def _mask(data_dir, text):
    from lib import privacy
    parts, buf = [], ''
    for para in re.split(r'(\n\s*\n)', text):
        if len(buf) + len(para) > CHUNK and buf:
            parts.append(buf)
            buf = ''
        buf += para
    if buf:
        parts.append(buf)
    return ''.join(privacy.mask_account_text(str(data_dir), p) for p in parts)


def prepare(data_dir, paths):
    """Download the PDFs under these @ paths, and write their masked text to Claude's folder. Returns
    {'docs': [{'title', 'local' (in Claude's folder), 'pages', 'cut'}], 'missed': [titles]}."""
    from lib import transforms
    got = transforms.fetch_drive(Path(data_dir), paths, ['pdf'])
    if got.get('error'):
        return {'docs': [], 'missed': [], 'error': got['error']}
    out_dir = home.work_dir(data_dir) / 'docs'
    out_dir.mkdir(parents=True, exist_ok=True)
    docs, missed = [], list(got.get('missed') or [])
    for f in got['files']:
        text = pdf_text(f['path'])
        if not text.strip() or not re.search(r'\w{3,}', re.sub(r'\[page \d+[^\]]*\]', '', text)):
            missed.append(f['title'])  # a scan, with no text to read
            continue
        cut = len(text) > MAX_CHARS
        body = _mask(data_dir, text[:MAX_CHARS])
        name = re.sub(r'[^\w .()-]+', '_', Path(f['title']).stem).strip(' .')[:80] or 'document'
        local = f'docs/{name}.txt'
        head = (f'Text of the PDF "{_mask(data_dir, f["title"])}", masked by Idli: codes stand for names, places '
                'and other private values.' + (' Only the first part is here.' if cut else '') + '\n\n')
        (home.work_dir(data_dir) / local).write_text(head + body)
        docs.append({'title': f['title'], 'local': local, 'pages': text.count('[page '), 'cut': cut})
    home.write(Path(data_dir) / '.idli' / 'docs-last.json', {'docs': docs})
    return {'docs': docs, 'missed': missed}


def words(docs):
    return ', '.join(d['title'] for d in docs)


def note_for_claude(docs):
    if not docs:
        return ''
    return (' Also the text of ' + str(len(docs)) + (' PDF' if len(docs) == 1 else ' PDFs') + ', masked by Idli: ' +
            ', '.join(d['local'] for d in docs) + '.')


def dumps(docs):
    return json.dumps(docs)
