"""Score reader output (a list of row strings) against the known table: each true row is matched to its most similar
output row; row = similarity of the row text (0-100); cells = share of cells with 3+ characters found exactly in it."""
import difflib, json, re, sys
def norm(s):
    s = str(s).casefold().replace('"', '')
    s = re.sub(r'(?<=\d),(?=\d{3})', '', s)           # 35,951,686 -> 35951686
    s = re.sub(r'\s+%', '%', s.replace(',', ' '))       # "56.9 %" -> "56.9%"
    s = re.sub(r'(?<=\d) (?=\d{3}\b)', '', s)          # a number split by CSV commas
    return re.sub(r'\s+', ' ', s).strip()
def score(truth, rows):
    rows = [norm(r) for r in rows if norm(r)]
    sims, hit, total = [], 0, 0
    for tr in truth:
        t = norm(' '.join(c for c in tr if c))
        best = max(rows, key=lambda r: difflib.SequenceMatcher(None, t, r).ratio(), default='')
        sims.append(difflib.SequenceMatcher(None, t, best).ratio())
        for c in tr:
            if len(c) >= 3:
                total += 1; hit += norm(c) in best
    allt = ' | '.join(rows)
    cells = [c for tr in truth for c in tr if len(c) >= 3]
    anywhere = sum(norm(c) in allt for c in cells)
    return round(100 * sum(sims) / len(sims)), round(100 * hit / max(total, 1)), round(100 * anywhere / max(len(cells), 1))
