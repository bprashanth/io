"""ocr-tesseract: read printed Hindi, Marathi and English from a photo or scan, or pull its tables into a spreadsheet.

Usage: python ocr-tesseract.py IMAGE [OUT.xlsx] [LANGS=hin+mar+eng]
Without OUT.xlsx it prints the text. With it, each ruled table found (img2table) goes to the spreadsheet.
The language files are $IDLI_FILES/models/tessdata/<lang>.traineddata (tessdata_best), with configs/ beside them.
"""
import os
import shutil
import subprocess
import sys
import time

image = sys.argv[1]
xlsx = sys.argv[2] if len(sys.argv) > 2 else None
langs = sys.argv[3] if len(sys.argv) > 3 else "hin+mar+eng"
tessdata = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "tessdata")
t = time.time()

if not xlsx:  # plain text: the tesseract program with our language files, page read as one block
    text = subprocess.run([shutil.which("tesseract"), image, "-", "--tessdata-dir", tessdata, "-l", langs, "--psm", "6"],
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout
    print(text.strip())
else:  # tables: img2table finds the ruled cells, tesseract reads the words (sparse text mode)
    from img2table.document import Image
    from img2table.ocr import TesseractOCR
    ocr = TesseractOCR(n_threads=1, lang=langs, psm=11, tessdata_dir=tessdata)
    doc = Image(image)
    tables = doc.extract_tables(ocr=ocr, implicit_rows=False, borderless_tables=False, min_confidence=50)
    for tb in tables:
        for row in tb.df.itertuples(index=False):
            print(" | ".join("" if v is None else str(v) for v in row))
    doc.to_xlsx(xlsx, ocr=ocr, implicit_rows=False, borderless_tables=False, min_confidence=50)
    print(len(tables), "table(s) written to", xlsx)
print(f"done in {time.time() - t:.1f} s")
