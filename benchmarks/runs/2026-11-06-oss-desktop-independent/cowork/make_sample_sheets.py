#!/usr/bin/env python3
"""Synthetic NGO field-visit workbooks with the mess real ones have (title rows, blank rows,
inconsistent spellings and dates, a second sheet). `test` is the mock that DIY mode sees;
`real` stands in for a user's private sheet (same structure, different and larger data).
All names are invented.  usage: make_sample_sheets.py test|real OUT.xlsx [seed]"""
import random
import sys

import openpyxl

kind, out = sys.argv[1], sys.argv[2]
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else (1 if kind == "test" else 7))
if kind == "test":
    names = ["Asha Example", "Bharat Sample", "Chitra Test", "Dev Mock", "Esha Dummy"]
    villages = {"Hillcrest": ["Hillcrest", "hillcrest ", "Hill crest"], "Riverbend": ["Riverbend", "River Bend"],
                "Lakeside": ["Lakeside"]}
    workers, n = ["Worker A", "Worker B"], 14
else:
    first = ["Lakshmi", "Meena", "Kavya", "Ramesh", "Suresh", "Anjali", "Priya", "Gowri", "Farida", "Joseph",
             "Selvi", "Arun", "Divya", "Imran", "Nandini", "Prakash", "Revathi", "Sangeetha"]
    last = ["Gowda", "Naik", "R", "K", "Shetty", "Bhat", "Khan", "D'Souza", "Murthy", "Patil"]
    names = [f"{rnd.choice(first)} {rnd.choice(last)}" for _ in range(40)]
    villages = {"Halaguru": ["Halaguru", "halaguru", "Halaguru "], "Kirugavalu": ["Kirugavalu", "Kirugaval"],
                "Bannur": ["Bannur", "BANNUR"], "Malavalli": ["Malavalli", "Malvalli"]}
    workers, n = ["ASHA Saroja", "ASHA Parvathi", "ANM Rukmini"], 120
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Visits"
ws.append([f"Field visits Q3 2026 ({'MOCK' if kind == 'test' else 'synthetic stand-in for real data'})"])
ws.append([])
ws.append(["Sl No", "Beneficiary Name", "Village", "Visit Date", "Health Worker", "Weight (kg)", "Referred?"])
for i in range(1, n + 1):
    v = rnd.choice(list(villages))
    d = rnd.randint(1, 28)
    m = rnd.choice([7, 8, 9])
    date = rnd.choice([f"{d:02d}/{m:02d}/2026", f"2026-{m:02d}-{d:02d}", f"{d}-{['Jul', 'Aug', 'Sep'][m - 7]}-26"])
    weight = round(rnd.uniform(2.2, 14.5), 1) if rnd.random() > 0.08 else ""
    ws.append([i, rnd.choice(names), rnd.choice(villages[v]), date, rnd.choice(workers), weight,
               rnd.choice(["Yes", "No", "no", "N", "Y", ""])])
    if rnd.random() < 0.05:
        ws.append([])
ws2 = wb.create_sheet("Distribution")
ws2.append(["Village", "Item", "Quantity", "Month"])
for v in villages:
    for item in ["Nutrition kit", "ORS packets", "IFA tablets"]:
        for mon in ["Jul", "Aug", "Sep"]:
            ws2.append([v, item, rnd.randint(5, 120) * (1 if kind == "test" else 3), mon])
wb.save(out)
print(out, n, "visits")
