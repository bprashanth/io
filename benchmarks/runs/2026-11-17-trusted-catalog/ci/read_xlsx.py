"""Print every cell of a spreadsheet (runs inside the ocr-tesseract environment, which has openpyxl)."""
import sys

from openpyxl import load_workbook

for ws in load_workbook(sys.argv[1], read_only=True).worksheets:
    for row in ws.iter_rows(values_only=True):
        print(' | '.join('' if v is None else str(v) for v in row))
