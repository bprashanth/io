import io

from pypdf import PdfReader


def text_of(data, first=10):
    """The first pages and a few from further in: enough for the 9B, quick on a 400-page PDF."""
    reader = PdfReader(io.BytesIO(data))
    n = len(reader.pages)
    pick = sorted(set(list(range(min(n, first))) + [int(n * at) for at in (0.3, 0.55, 0.8) if int(n * at) >= first]))
    return '\n'.join((reader.pages[i].extract_text() or '') for i in pick)


def run(kit, question='What are the main themes and ideas?'):
    texts, empty = {}, []
    for f in kit.files(['pdf']):
        text = kit.remember(f, 'text', lambda: text_of(kit.read_bytes(f)))
        if text.strip():
            texts[f.title] = text
        else:
            empty.append(f.title)
    if not texts:
        return {'reply': 'These PDFs have no text to read (they may be scans).', 'used': [], 'no_text': empty}
    notes = kit.summarise_all(texts)
    reply = kit.answer(question, notes)
    if empty:
        reply += '\n\nNo text in: ' + ', '.join(empty) + ' (they may be scans).'
    return {'reply': reply, 'used': list(texts), 'no_text': empty}
