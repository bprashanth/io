#!/usr/bin/env python3
"""Generate district-comparison-2023-purnia-vs-nalanda.csv independently from
women_livelihood_outcomes.csv, in the exact format the page's download button produces."""
import csv, os

base = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base, "women_livelihood_outcomes.csv"), newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def get(d, y):
    for r in rows:
        if r["district"] == d and r["year"] == y:
            return r
    raise KeyError((d, y))

A, B, YEAR = "Purnia", "Nalanda", "2023"
ra, rb = get(A, YEAR), get(B, YEAR)

def f1(x):
    return f"{round(x, 1):.1f}"

def f_signed(x):
    v = round(x * 10) / 10
    if v == 0:
        return "0.0"
    return ("+" if v > 0 else "-") + f"{abs(v):.1f}"

def csv_field(s):
    s = str(s)
    if any(c in s for c in ',"\r\n'):
        return '"' + s.replace('"', '""') + '"'
    return s

def r(d):
    enr, comp, emp = int(d["women_enrolled"]), int(d["completed_training"]), int(d["employed_at_6_months"])
    return {
        "enrolled": enr, "completed": comp, "employed": emp,
        "completionRate": comp / enr * 100,
        "employedOfEnrolled": emp / enr * 100,
        "employedOfCompleted": emp / comp * 100,
    }

ra, rb = r(ra), r(rb)
lines = []
lines.append(["Metric", A, B, f"Gap ({B} minus {A})"])
lines.append(["Women enrolled (women)", str(ra["enrolled"]), str(rb["enrolled"]), ""])
lines.append(["Completed training (women)", str(ra["completed"]), str(rb["completed"]), ""])
lines.append(["Employed at 6 months (women)", str(ra["employed"]), str(rb["employed"]), ""])
lines.append(["Training completion rate (%)", f1(ra["completionRate"]), f1(rb["completionRate"]), f_signed(rb["completionRate"] - ra["completionRate"]) + " pp"])
lines.append(["Employment after 6 months, out of all enrolled (%)", f1(ra["employedOfEnrolled"]), f1(rb["employedOfEnrolled"]), f_signed(rb["employedOfEnrolled"] - ra["employedOfEnrolled"]) + " pp"])
lines.append(["Employment after 6 months, out of training completers (%)", f1(ra["employedOfCompleted"]), f1(rb["employedOfCompleted"]), f_signed(rb["employedOfCompleted"] - ra["employedOfCompleted"]) + " pp"])
lines.append([])
lines.append(["Year", YEAR])
lines.append(["Source file", "women_livelihood_outcomes.csv"])
lines.append(["Source field (all rows)", "synthetic women livelihood outcomes fixture"])
lines.append(["Gap direction", f"{B} minus {A}; percentage points for rate rows; count rows are numbers of women"])
lines.append(["Formulas", "Training completion rate (%) = completed_training / women_enrolled * 100; Employment out of all enrolled (%) = employed_at_6_months / women_enrolled * 100; Employment out of training completers (%) = employed_at_6_months / completed_training * 100"])

out = "\r\n".join(",".join(csv_field(c) for c in ln) for ln in lines) + "\r\n"
path = os.path.join(base, "district-comparison-2023-purnia-vs-nalanda.csv")
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(out)
print(out)
