"""Tests for the file form (lib/formkit.py). Run: .venv/bin/python -m lib.test_formkit

Uses sites/files/testdata/field_programme_tracker.xlsx (three tabs, messy on purpose) with a hand-written
skill in sites/files/testdata/skills, plus the taught skills in file-skills/ on the event-eval files.
Expected numbers were computed separately with pandas."""
import os
import shutil
import sys
import tempfile

import duckdb
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TD = os.path.join(HERE, "sites", "files", "testdata")
EVAL = os.path.join(HERE, "..", "..", "2026-11-07-cowork-event-eval", "data")
os.environ["IDLI_FILE_SKILLS"] = os.path.join(TD, "skills")
from lib import filekit as fk  # noqa: E402
from lib import formkit as fm  # noqa: E402

fails = 0


def ok(cond, what):
    global fails
    print(("ok   " if cond else "FAIL ") + what)
    fails += 0 if cond else 1


def opened(path, skills=None):
    if skills:
        fk.SKILLS_DIR = skills
    sheets, _ = fk.raw_sheets(path)
    s, score, _ = fm.match_file(sheets)
    con = duckdb.connect()
    b = fm.build(con, path, s, "t") if s else {}
    return sheets, s, con, b


TRACKER = os.path.join(TD, "field_programme_tracker.xlsx")
fk.SKILLS_DIR = os.path.join(TD, "skills")
sheets, s, con, b = opened(TRACKER)
ok(s and s["id"] == "field_programme_tracker", "recognises a three-tab workbook")
ok(fm.contract(s, sheets, con, b)["status"] == "ok", "contract ok on the taught file")
f = fm.form(con, s, "Visits", b)
r = fm.run(con, f, b["Visits"]["table"], {"measures": ["disbursed", "rows"], "group_by": ["officer_district"],
                                          "preset": "completed", "date": {"from": "01/07/2026", "to": "30/09/2026"}})
got = {x["Officer's district"]: (x["Amount disbursed (Rs)"], x["Number of visits"]) for x in r["rows"]}
ok(got == {"Pune": (219500, 15), "Satara": (140750, 13), "Kolhapur": (127000, 9), "Sangli": (82000, 9)},
   "lookup across tabs + preset + dd/mm dates: district totals match pandas")
ok(r["total"] == {"Amount disbursed (Rs)": 569250, "Number of visits": 46}, "grand total row")
r = fm.run(con, f, b["Visits"]["table"], {"filters": {"field_officer": ["ravi patil"], "status": ["follow-up"]}})
ok(r["total"]["Matching visits"] == 4, "row listing with case-insensitive choice filters")

for bad, why in [({"measures": ["sum(1); DROP TABLE x"]}, "unknown measure"),
                 ({"group_by": ['"x"; select 1']}, "unknown grouping"),
                 ({"filters": {"nope": ["a"]}}, "unknown filter column"),
                 ({"filters": {"village": ["x' OR '1'='1"]}, "measures": ["rows"]}, None),
                 ({"date": {"from": "yesterday-ish"}}, "unreadable date")]:
    try:
        r = fm.run(con, f, b["Visits"]["table"], bad)
        ok(why is None and r["rows"][0]["Number of visits"] == 0, "a quote in a value is data, not SQL")
    except fm.SpecError:
        ok(why is not None, f"rejects {why}")

# --- the contract test on edited copies of the workbook
tmp = tempfile.mkdtemp()


def edited(name, fn):
    frames = pd.read_excel(TRACKER, sheet_name=None, header=None, dtype=object)
    fn(frames)
    p = os.path.join(tmp, name + ".xlsx")
    with pd.ExcelWriter(p) as w:
        for k, df in frames.items():
            df.to_excel(w, sheet_name=k, index=False, header=False)
    sh, sk, c, bb = opened(p)
    return fm.contract(sk, sh, c, bb) if sk else {"status": "unrecognised"}


def new_status(fr):
    fr["Visits"].iloc[5, 5] = "On hold"
def rename_amount(fr):
    fr["Visits"].iloc[2, 4] = "Amount paid out"
def drop_officers(fr):
    del fr["Officers"]
def broken_dates(fr):
    fr["Visits"].iloc[3:, 0] = "sometime"
def new_column(fr):
    fr["Villages"][9] = ["Pincode"] + ["4110" + str(i) for i in range(len(fr["Villages"]) - 1)]
def renamed_tab(fr):
    fr["Field visits"] = fr.pop("Visits")


c = edited("status", new_status)
ok(c["status"] == "drift" and any("on hold" in m.lower() for m in c["messages"]), "new status value -> drift, named")
c = edited("rename", rename_amount)
ok(c["status"] == "changed" and any("amount_disbursed" in m for m in c["messages"]), "renamed used column -> changed")
c = edited("officers", drop_officers)
ok(c["status"] in ("changed", "unrecognised"), "a tab removed -> changed")
c = edited("dates", broken_dates)
ok(c["status"] == "changed" and any("Visit date" in m for m in c["messages"]), "dates stop parsing -> changed")
c = edited("newcol", new_column)
ok(c["status"] == "drift" and any("Pincode" in m for m in c["messages"]), "new column -> drift")
c = edited("tabname", renamed_tab)
ok(c["status"] == "drift" and any("Field visits" in m for m in c["messages"]), "renamed tab -> drift, still maps")
shutil.rmtree(tmp)

# --- the taught single-tab skills, on the event-eval files, through the generic form (no taught SQL)
fk.SKILLS_DIR = os.path.join(HERE, "file-skills")
sh, s, con, b = opened(os.path.join(EVAL, "tech_reimbursement_form.xlsx"))
t = next(iter(b))
f = fm.form(con, s, t, b)
r = fm.run(con, f, b[t]["table"], {"measures": ["amount", "rows"], "preset": "paid_out",
                                   "date": {"from": "2026-08-26", "to": "2026-10-26"}})
ok(r["rows"][0]["Amount (Rs)"] == 43020 and r["rows"][0]["Number of claims"] == 12, "reimbursements 26 Aug-26 Oct: 43,020 / 12")
r = fm.run(con, f, b[t]["table"], {"measures": ["amount"], "group_by": ["employee"], "preset": "not_rejected",
                                   "filters": {"category": ["Hardware"]}, "limit": 1})
ok(r["rows"][0] == {"Employee": "Anaya Rao", "Amount (Rs)": 24970}, "top hardware claimant without a taught query")
sh, s, con, b = opened(os.path.join(EVAL, "volunteer_register.xlsx"))
t = next(iter(b))
f = fm.form(con, s, t, b)
r = fm.run(con, f, b[t]["table"], {"measures": ["rows", "stipend"], "date": {"from": "2026-07-01"}})
ok(r["rows"][0]["Number of volunteers"] == 25 and r["rows"][0]["Stipend paid (Rs)"] == 32100,
   "volunteers since July from the real file: 25 / 32,100")
ok(fm.indian(3245678.5) == "32,45,678.5", "Indian digit grouping")
print("ALL PASSED" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
