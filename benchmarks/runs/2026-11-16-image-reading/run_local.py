import json, subprocess, sys, time, os
sys.path.insert(0, os.path.dirname(__file__))
from score import score
D = os.environ.get('IMGDIR') or os.path.dirname(os.path.abspath(__file__))
truth = json.load(open(f'{D}/truth.json'))
from rapidocr import RapidOCR
eng = RapidOCR()
def tess(p, lang='eng'):
    return subprocess.run(['tesseract', p, 'stdout', '--psm', '6', '-l', lang], capture_output=True, text=True).stdout.splitlines()
def rapid(p):
    r = eng(p)
    boxes = [(b, t) for b, t in zip(r.boxes, r.txts)] if r.boxes is not None else []
    rows = []
    for b, t in sorted(boxes, key=lambda x: sum(pt[1] for pt in x[0]) / 4):
        y = sum(pt[1] for pt in b) / 4; h = abs(b[2][1] - b[0][1]) or 10
        if rows and abs(rows[-1][0] - y) < h * 0.6: rows[-1][1].append((b[0][0], t))
        else: rows.append([y, [(b[0][0], t)]])
    return [' '.join(t for _, t in sorted(ws)) for _, ws in rows]
res = {}
for name, rows in truth.items():
    p = f'{D}/{name}.png'
    if not os.path.exists(p): p = f'{D}/{name}.jpg'
    for eng_name, fn in [('tesseract', lambda p: tess(p, 'eng+hin' if 'hindi' in name else 'eng')), ('rapidocr', rapid)]:
        t = time.time(); out = fn(p); dt = time.time() - t
        res.setdefault(name, {})[eng_name] = (*score(rows, out), round(dt, 1))
        json.dump(out, open(f'{D}/out-{eng_name}-{name}.json', 'w'), ensure_ascii=False)
for n, r in res.items(): print(n.ljust(22), '  '.join(f'{k}: row {v[0]} cells-in-row {v[1]} read {v[2]} ({v[3]}s)' for k, v in r.items()))
