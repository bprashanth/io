"""Draw the OCR test images with Pillow (runs inside the ocr-tesseract environment).

Usage: python make_table.py TABLE.png TEXT.png   Prints {"numbers": [...]} as its last line.
TABLE.png is a ruled 3 by 4 table in the catalog's own test geometry (300 by 90 px cells); TEXT.png has the same
words as plain lines. Lines are 2 px: in a local probe img2table missed this table with 3 px lines and 32-40 px text
(it found it with 1-2 px lines, or with 24 px text), and tesseract's plain page mode (psm 6) read nothing from any
ruled version, so plain text is checked on the unruled image.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

ROWS = [['Village', 'Wells', 'Pumps'], ['Rampur', '124', '37'], ['Sonpur', '58', '902'], ['Khedi', '713', '46']]
CW, RH = 300, 90
font = ImageFont.load_default(size=32)

img = Image.new('RGB', (CW * 3 + 40, RH * len(ROWS) + 40), 'white')
d = ImageDraw.Draw(img)
for r in range(len(ROWS) + 1):
    d.line([(20, 20 + r * RH), (20 + 3 * CW, 20 + r * RH)], fill='black', width=2)
for c in range(4):
    d.line([(20 + c * CW, 20), (20 + c * CW, 20 + len(ROWS) * RH)], fill='black', width=2)
for r, row in enumerate(ROWS):
    for c, text in enumerate(row):
        d.text((40 + c * CW, 35 + r * RH), text, fill='black', font=font)
img.save(sys.argv[1])

img = Image.new('RGB', (CW * 3 + 40, RH * len(ROWS) + 40), 'white')
d = ImageDraw.Draw(img)
for r, row in enumerate(ROWS):
    d.text((40, 35 + r * RH), '   '.join(row), fill='black', font=font)
img.save(sys.argv[2])
print(json.dumps({'numbers': [v for row in ROWS[1:] for v in row[1:]]}))
