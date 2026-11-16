"""Synthetic table images with known contents, from easy to hard."""
import json, random, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
OUT = __file__.rsplit('/', 1)[0]
random.seed(7)
def font(name, size):
    path = subprocess.run(['fc-match', '-f', '%{file}', name], capture_output=True, text=True).stdout
    return ImageFont.truetype(path, size)
def draw(rows, f, colw, rowh=44, pad=14, lines=True):
    w, h = sum(colw) + 2 * pad, rowh * len(rows) + 2 * pad
    im = Image.new('RGB', (w, h), 'white'); d = ImageDraw.Draw(im)
    for i, r in enumerate(rows):
        x = pad
        for c, cw in zip(r, colw):
            d.text((x + 6, pad + i * rowh + 10), c, fill='black', font=f); x += cw
        if lines: d.line((pad, pad + (i + 1) * rowh, w - pad, pad + (i + 1) * rowh), fill=(150, 150, 150))
    if lines:
        x = pad
        for cw in colw[:-1]:
            x += cw; d.line((x, pad, x, h - pad), fill=(150, 150, 150))
    return im
names = ['Kavita Jadhav', 'Suresh Pawar', 'Lata Shinde', 'Rahul More', 'Anita Kale', 'Vijay Patil', 'Meena Gaikwad', 'Sunil Bhosale']
villages = ['Ramtekdi', 'Hadapsar', 'Yerawada', 'Kondhwa']
reg = [['No', 'Name', 'Village', 'Mon', 'Tue', 'Wed']] + [[str(i + 1), n, random.choice(villages)] + [random.choice('PPPA') for _ in range(3)] for i, n in enumerate(names)]
fin = [['Source of finance', 'Area', 'SC/ST', 'OBC', 'Other']]
for src in ['No outside finance', 'Institutional finance', 'Moneylender', 'Unregistered firms']:
    for area in ['Rural', 'Urban']:
        fin.append([src if area == 'Rural' else '', area] + [f'{random.uniform(2, 80):.1f}%' for _ in range(3)])
hin = [['क्रम', 'नाम', 'गाँव', 'उपस्थिति']] + [[str(i + 1), n, v, p] for i, (n, v, p) in enumerate([
    ('सीमा पाटील', 'रामटेकडी', 'हाँ'), ('राजेश मोरे', 'हडपसर', 'नहीं'), ('गीता काळे', 'येरवडा', 'हाँ'), ('अमित शिंदे', 'कोंढवा', 'हाँ')])]
cases = {}
def save(name, im, rows):
    im.save(f'{OUT}/{name}.png'); cases[name] = rows
save('1-clean-register', draw(reg, font('DejaVu Sans', 22), [60, 220, 160, 70, 70, 70]), reg)
big = draw(fin, font('DejaVu Sans', 22), [300, 110, 110, 110, 110])
save('2-dense-screenshot', big.resize((big.width // 2, big.height // 2), Image.BILINEAR), fin)
ph = draw(reg, font('DejaVu Serif', 22), [60, 220, 160, 70, 70, 70]).rotate(3.5, expand=True, fillcolor=(235, 230, 220))
sh = Image.new('L', ph.size, 0); ImageDraw.Draw(sh).rectangle((0, 0, ph.width // 3, ph.height), fill=70)
ph = Image.composite(Image.new('RGB', ph.size, (120, 115, 105)), ph, sh.filter(ImageFilter.GaussianBlur(40)))
ph = ph.filter(ImageFilter.GaussianBlur(1.1))
ph = Image.eval(ph, lambda v: max(0, min(255, v + random.randint(-12, 12))))
save('3-register-photo', ph, reg)
save('4-hindi-register', draw(hin, font('Lohit Devanagari', 22), [70, 200, 160, 120]), hin)
loose = draw(reg[:6], font('DejaVu Sans Oblique', 21), [60, 220, 160, 70, 70, 70], lines=False)
save('5-no-lines-italic', loose, reg[:6])
json.dump(cases, open(f'{OUT}/truth.json', 'w'), ensure_ascii=False, indent=1)
print(list(cases))
