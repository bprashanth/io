"""Masked copies of the person's files for Claude's working folder.

Claude's scripts run on these copies, never on the real files: private cells hold the same codes Claude sees in
its conversation, so a script that searches the data for a guessed name finds nothing. The copies keep the real
file's layout, sheets and number types, so a script behaves the same on the copy and (after Idli swaps the codes
back) on the real file when a saved Mini runs.

  build(data_dir, work_dir)      write work/drive/<path> for every reviewed (mask-mode) file; drop the rest
  rehydrate_script(text, vault)  put real values back into the string literals of a Mini script
"""
import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import tokenize

from . import filekit as fk
from . import privacy
from .privacy_engine.pseudonymize import TOKEN_RE, normalise

MANIFEST = '.idli-masked.json'


def _masker(vault):
    """One compiled matcher for every known value (the same rules as the proxy's _known)."""
    values = sorted((v for v in vault.display.values() if v.strip() and v.strip().casefold() not in privacy.NEVER_PRIVATE),
                    key=len, reverse=True)
    if not values:
        return lambda text: text
    pattern = re.compile('|'.join(privacy._value_pattern(v) for v in values), re.I)
    in_url = re.compile('|'.join(privacy._url_pattern(v) for v in values), re.I)
    cache = {}

    def sub(m):
        return privacy._code_for(vault, m.group())

    def mask(text):
        if text not in cache:
            out = privacy.URL.sub(lambda u: in_url.sub(sub, u.group()), text)
            cache[text] = pattern.sub(sub, out)
        return cache[text]
    return mask


def _cell_code(value, chosen, forward, allowed, mask):
    """The masked form of one cell, or the cell itself when nothing in it is private. `chosen` is the heading of a
    column the person hid (or None)."""
    if value is None or value == '':
        return value
    text = fk._cell_text(value)
    if chosen is not None and normalise(text) == normalise(chosen):
        return value  # the heading repeated inside the sheet
    if chosen is not None:
        code = forward.get(normalise(text))
        if code in allowed:
            return value
        # A chosen cell is always replaced whole; an unseeded one is hidden rather than passed through.
        return code or 'HIDDEN'
    if isinstance(value, str):
        return mask(value)
    out = mask(text)
    return value if out == text else out


def _mask_xlsx(src, dst, columns, forward, allowed, mask):
    import openpyxl
    sheets, headers = fk.raw_sheets(str(src))
    book = openpyxl.load_workbook(src)  # keeps formulas as text; values of formula cells are not needed by pandas
    stats = {'cells': 0, 'hidden': 0}
    for ws in book.worksheets:
        frame = sheets.get(ws.title)
        h = headers.get(ws.title)
        chosen_cols = {}
        if frame is not None:
            for name, col in zip(frame.columns, frame.attrs.get('sheet_cols', [])):
                if columns.get(str(name)):
                    chosen_cols[col + 1] = str(name)  # openpyxl columns are 1-based
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                chosen = chosen_cols.get(cell.column) if h is not None and cell.row > h else None
                new = _cell_code(cell.value, chosen, forward, allowed, mask)
                if new is not cell.value and new != cell.value:
                    stats['cells'] += 1
                    stats['hidden'] += new == 'HIDDEN'
                    cell.value = new
        # Comments, hyperlinks and defined names can carry values too: drop them from the copy.
        for row in ws.iter_rows():
            for cell in row:
                cell.comment = None
                cell.hyperlink = None
    for name in list(book.defined_names.keys()) if hasattr(book.defined_names, 'keys') else []:
        del book.defined_names[name]
    book.properties.creator = None
    book.properties.lastModifiedBy = None
    book.properties.title = None
    book.save(dst)
    return stats


def _mask_csv(src, dst, columns, forward, allowed, mask):
    sheets, headers = fk.raw_sheets(str(src))
    frame, h = sheets.get('csv'), headers.get('csv')
    chosen_cols = {col: str(name) for name, col in zip(frame.columns, frame.attrs.get('sheet_cols', []))
                   if columns.get(str(name))} if frame is not None else {}
    stats = {'cells': 0, 'hidden': 0}
    with open(src, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    for i, row in enumerate(rows, start=1):
        for j, value in enumerate(row):
            chosen = chosen_cols.get(j) if h is not None and i > h else None
            new = _cell_code(value, chosen, forward, allowed, mask)
            if new != value:
                stats['cells'] += 1
                stats['hidden'] += new == 'HIDDEN'
                row[j] = new
    with open(dst, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)
    return stats


def build(data_dir, work_dir):
    """Rebuild work/drive from the reviewed files. Files that were never reviewed are not copied at all."""
    data_dir, work_dir = Path(data_dir).resolve(), Path(work_dir).resolve()
    target = work_dir / 'drive'
    if target.is_symlink():  # the old layout linked straight to the real downloads
        target.unlink()
    target.mkdir(parents=True, exist_ok=True)
    path = data_dir / 'privacy.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    with privacy.session_lock(data_dir):
        full = privacy.session_vault(data_dir)
        vault, allowed = privacy.proxy_vault(data_dir, full)
        mask = _masker(vault)
        written, report = set(), {}
        for file, options in sorted(settings.items()):
            if options.get('mode') != 'mask' or not file.startswith('drive/'):
                continue
            src = data_dir / file
            if not src.is_file() or src.suffix.lower() not in ('.xlsx', '.csv'):
                continue
            dst = work_dir / file
            dst.parent.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(dir=dst.parent, suffix=src.suffix)
            os.close(fd)
            try:
                fn = _mask_xlsx if src.suffix.lower() == '.xlsx' else _mask_csv
                report[file] = fn(src, temp, options.get('columns', {}), full.forward, allowed, mask)
                os.replace(temp, dst)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            written.add(dst.relative_to(work_dir).as_posix())
    # Remove copies of files that are no longer reviewed (and anything else that is not ours).
    for p in sorted(target.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        rel = p.relative_to(work_dir).as_posix()
        if p.is_symlink() or (p.is_file() and rel not in written):
            p.unlink()
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    (target / MANIFEST).write_text(json.dumps({'built': dt.datetime.now().isoformat(timespec='seconds'),
                                               'files': sorted(written), 'report': report}, indent=1))
    return report


def _escape(real, quote_prefix):
    if 'r' in quote_prefix.lower():
        if re.search(r'[\\\'"\n]', real):
            raise ValueError('A raw string in this script holds a value Idli cannot put back safely.')
        return real
    return real.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')


def rehydrate_script(text, vault):
    """Swap codes inside string literals for real values, so a saved Mini runs on the real file.
    Codes outside string literals (comments, names) are left alone. Returns (text, number of values put back)."""
    lines = text.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    edits, changed = [], 0
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type not in (tokenize.STRING, getattr(tokenize, 'FSTRING_MIDDLE', -1)):
            continue
        prefix = re.match(r'^[A-Za-z]*', tok.string).group() if tok.type == tokenize.STRING else ''
        def sub(m):
            nonlocal changed
            real = vault.display.get(m.group())
            if real is None:
                return m.group()
            changed += 1
            return _escape(real, prefix)
        new = TOKEN_RE.sub(sub, tok.string)
        if new != tok.string:
            a = starts[tok.start[0] - 1] + tok.start[1]
            b = starts[tok.end[0] - 1] + tok.end[1]
            edits.append((a, b, new))
    for a, b, new in reversed(edits):
        text = text[:a] + new + text[b:]
    return text, changed
