"""Draw a small ruled table of villages and counts with Pillow (runs inside the ocr-tesseract environment).

Usage: python make_table.py OUT.png   Prints {"numbers": [...]} as its last line.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

ROWS = [['Village', 'Wells', 'Pumps'], ['Rampur', '124', '37'], ['Sonpur', '58', '902'], ['Khedi', '713', '46']]
W, H, PAD = 220, 70, 20
img = Image.new('RGB', (PAD * 2 + W * 3, PAD * 2 + H * len(ROWS)), 'white')
d = ImageDraw.Draw(img)
font = ImageFont.load_default(size=34)
for r, row in enumerate(ROWS):
    for c, text in enumerate(row):
        x, y = PAD + c * W, PAD + r * H
        d.rectangle([x, y, x + W, y + H], outline='black', width=3)
        d.text((x + 18, y + 16), text, fill='black', font=font)
img.save(sys.argv[1])
print(json.dumps({'numbers': [v for row in ROWS[1:] for v in row[1:]]}))
