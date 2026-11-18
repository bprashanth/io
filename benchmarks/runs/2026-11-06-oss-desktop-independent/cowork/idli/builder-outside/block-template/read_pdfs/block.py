import io

from pypdf import PdfReader


def text_of(data, first=10):
    """The first pages and a few from further in: enough for the 9B, quick on a 400-page PDF.
    A page pypdf can't read is skipped, so one odd page doesn't stop the file."""
    reader = PdfReader(io.BytesIO(data))
    n = len(reader.pages)
    pick = sorted(set(list(range(min(n, first))) + [int(n * at) for at in (0.3, 0.55, 0.8) if int(n * at) >= first]))
    parts = []
    for i in pick:
        try:
            parts.append(reader.pages[i].extract_text() or '')
        except Exception:  # noqa: BLE001
            continue
    return '\n'.join(parts)


def run(kit, question='What are the main themes and ideas?'):
    texts, empty, unread = {}, [], []
    for f in kit.files(['pdf']):
        try:
            text = kit.remember(f, 'text', lambda: text_of(kit.read_bytes(f)))
        except Exception:  # noqa: BLE001  a damaged PDF doesn't stop the others
            unread.append(f.title)
            continue
        if text.strip():
            texts[f.title] = text
        else:
            empty.append(f.title)
    if not texts:
        return {'reply': 'None of these PDFs has text to read (they may be scans).', 'used': [],
                'no_text': empty + unread}
    kit.progress(f'Read {len(texts)} PDFs.')
    notes = kit.summarise_all(texts)
    reply = kit.answer(question, notes)
    if empty:
        reply += '\n\nNo text in: ' + ', '.join(empty) + ' (they may be scans).'
    if unread:
        reply += '\n\nCould not open: ' + ', '.join(unread) + '.'
    return {'reply': reply, 'used': list(texts), 'no_text': empty + unread}
