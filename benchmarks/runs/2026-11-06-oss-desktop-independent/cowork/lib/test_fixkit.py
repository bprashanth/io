"""Suggested fixes and layout rows, on made-up values (no real files).

  .venv/bin/python -m lib.test_fixkit
"""
import os
import shutil
import tempfile

import pandas as pd

from lib import filekit as fk
from lib import fixkit as fx

FAILS = []


def same(label, got, want):
    ok = got == want
    print(("ok  " if ok else "FAIL"), label, "" if ok else f"got {got!r}, want {want!r}")
    if not ok:
        FAILS.append(label)


def to(rule, v, arg=None, options=None):
    return (fx.suggest(rule, v, arg, options) or {}).get("to", "NO SUGGESTION")


same("approx number", to("number", "approx 12"), "12")
same("placeholder number", to("number", "pending"), "")
same("unit in cell", to("number", "12 cm"), "12")
same("two numbers need a person", to("number", "9.4, 11.5"), None)
same("letter O for zero", to("number", "1O0"), "100")
same("date in another format", to("date", "2026-07-21", ["%d/%m/%Y"]), "21/07/2026")
same("excel serial date", to("date", "45123", ["%d/%m/%Y"]), "16/07/2023")
same("impossible date needs a person", to("date", "31/09/2026"), None)
same("TBD date -> blank", to("date", "TBD"), "")
same("phone with country code", to("phone", "+91 98765 43210"), "9876543210")
same("short phone needs a person", to("phone", "982211"), None)
same("email with spaces", to("email", "a.b @ example.org"), "a.b@example.org")
same("list: capitals only", to("in_list", "approved", None, ["Approved", "Pending"]), "Approved")
same("list: one close typo", to("in_list", "Psychotria bisulcta", None, ["Psychotria bisulcata", "Litsea wightiana"]),
     "Psychotria bisulcata")
same("list: nothing close", to("in_list", "UKS2", None, ["neoscr", "litwig"]), None)
same("required needs a person", to("required", ""), None)

rows = [["Village", "Officer", "Households", "Amount"], ["Village A", "Ravi", "12", "1200"],
        ["Village B", "Sita", "8", "900"], [None, None, None, None],
        ["Village", "Officer", "Households", "Amount"], ["Block 2", None, None, None],
        ["Village C", "Ravi", "5", "500"], ["Total", None, "25", "2600"]]
d = tempfile.mkdtemp()
p = os.path.join(d, "messy.xlsx")
pd.DataFrame(rows).to_excel(p, header=False, index=False)
sheets, hdr = fk.raw_sheets(p)
df = next(iter(sheets.values()))
lay = fx.layout_rows(df)
same("layout kinds", sorted(lay.values()), ["repeated_header", "subheading", "total"])
same("real sheet rows (blank row counted)", [fk.sheet_row(df, i, hdr["Sheet1"]) for i in sorted(lay)], [5, 6, 8])
same("cell ref", fk.cell_ref(df, 4, "Amount", hdr["Sheet1"]), "D7")
kept = fx.keep_rows(df, {})
same("repeated heading skipped by default", len(kept), len(df) - 1)
same("kept rows keep their sheet rows", kept.attrs["sheet_rows"], [2, 3, 6, 7, 8])
same("skip all layout when taught", len(fx.keep_rows(df, {"skip_rows": ["repeated_header", "subheading", "total"]})), 3)
shutil.rmtree(d)

print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED")
