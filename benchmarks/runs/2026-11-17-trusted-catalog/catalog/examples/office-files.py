"""office-files: read and write Word (.docx) and Excel (.xlsx) files, and work on tables with pandas.

Usage: python office-files.py OUT_FOLDER
Writes a small report.docx and visits.xlsx, then reads both back and prints what is in them.
"""
import os
import sys

import pandas as pd
from docx import Document
from openpyxl import load_workbook

d = sys.argv[1]
os.makedirs(d, exist_ok=True)

# A spreadsheet from a table (pandas writes it with openpyxl), then a total added by hand.
visits = pd.DataFrame({"village": ["रामपुर", "शिवगढ़", "नंदपुर"], "visits": [12, 7, 9], "trees": [120, 60, 95]})
xlsx = os.path.join(d, "visits.xlsx")
visits.to_excel(xlsx, index=False, sheet_name="Visits")
wb = load_workbook(xlsx)
ws = wb["Visits"]
ws.append(["Total", "=SUM(B2:B4)", "=SUM(C2:C4)"])  # Excel computes these on opening; pandas reads them as empty
wb.save(xlsx)

# A Word report with a heading, a paragraph and the same table.
doc = Document()
doc.add_heading("मासिक रिपोर्ट", level=1)
doc.add_paragraph(f"इस महीने {visits.visits.sum()} दौरे हुए और {visits.trees.sum()} पेड़ लगाए गए।")
table = doc.add_table(rows=1, cols=3)
for cell, name in zip(table.rows[0].cells, visits.columns):
    cell.text = name
for row in visits.itertuples(index=False):
    for cell, v in zip(table.add_row().cells, row):
        cell.text = str(v)
docx = os.path.join(d, "report.docx")
doc.save(docx)

# Read both back.
back = pd.read_excel(xlsx)
print(back.to_string(index=False))
for p in Document(docx).paragraphs:
    print(p.text)
print("tables in the report:", len(Document(docx).tables))
