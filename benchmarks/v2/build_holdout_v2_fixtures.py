#!/usr/bin/env python3
"""Deterministically build the realistic-shape holdout-v2 fixtures.

The v2 gate and holdout-v1 used tiny (<=21 row) snake_case fixtures. Real NGO
files have headers with spaces, units and parentheses, aggregate "Total" rows
mixed with detail rows, hundreds of transactional rows, blank cells, and years
spread across columns. These fixtures reproduce those shapes with synthetic
values only. Regenerating with the same seed yields byte-identical files; the
manifest records their SHA-256 so a changed fixture is detectable.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "holdout-v2"
OUT.mkdir(exist_ok=True)
rng = random.Random(20260821)


def write(name: str, header: list[str], rows: list[list]) -> None:
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


# ---------------------------------------------------------------- fixture A
# Wide NFHS-style district factsheet: messy headers, two survey rounds,
# "State Total" rows mixed in, a few NA cells in the older round.
states = {
    "Bihar": ["Gaya", "Nalanda", "Purnia", "Kishanganj", "Rohtas", "Saran", "Madhubani", "Bhojpur"],
    "Jharkhand": ["Ranchi", "Dumka", "Gumla", "Palamu", "Giridih", "Hazaribagh"],
    "Odisha": ["Koraput", "Kalahandi", "Rayagada", "Ganjam", "Cuttack", "Mayurbhanj"],
}
header_a = [
    "State", "District", "Survey Round", "Households surveyed",
    "Women age 15-49 years who are literate (%)",
    "Children age 12-23 months fully vaccinated (%)",
    "Institutional births (%)",
    "Children under 5 years who are stunted (%)",
    "Households with improved sanitation facility (%)",
    "Source",
]
rows_a: list[list] = []
na_districts = {"Rayagada", "Giridih"}
for state, districts in states.items():
    totals = {"NFHS-4": [0, 0.0, 0.0, 0.0, 0.0, 0.0], "NFHS-5": [0, 0.0, 0.0, 0.0, 0.0, 0.0]}
    for district in districts:
        base = {
            "lit": rng.uniform(38, 72), "vac": rng.uniform(45, 78), "inst": rng.uniform(55, 85),
            "stunt": rng.uniform(28, 50), "san": rng.uniform(20, 55),
        }
        for round_name in ("NFHS-4", "NFHS-5"):
            later = round_name == "NFHS-5"
            hh = rng.randint(700, 1400)
            lit = base["lit"] + (rng.uniform(-3, 9) if later else 0)
            vac = base["vac"] + (rng.uniform(-8, 14) if later else 0)
            inst = base["inst"] + (rng.uniform(2, 12) if later else 0)
            stunt = base["stunt"] + (rng.uniform(-7, 3) if later else 0)
            san = base["san"] + (rng.uniform(5, 25) if later else 0)
            values = [round(min(99.0, max(1.0, v)), 1) for v in (lit, vac, inst, stunt, san)]
            t = totals[round_name]
            t[0] += hh
            for i, v in enumerate(values):
                t[i + 1] += v
            if not later and district in na_districts:
                values_out = ["NA", round(values[1], 1), round(values[2], 1), "NA", round(values[4], 1)]
            else:
                values_out = values
            rows_a.append([state, district, round_name, hh, *values_out, "District factsheet"])
    for round_name in ("NFHS-4", "NFHS-5"):
        t = totals[round_name]
        n = len(districts)
        rows_a.append([state, "State Total", round_name, t[0], *[round(x / n, 1) for x in t[1:]], "State factsheet"])
write("district_health_factsheet.csv", header_a, rows_a)

# ---------------------------------------------------------------- fixture B
# Long SHG loan register: 360 transactional rows across 2022-2024.
blocks = ["Atri", "Barachatti", "Belaganj", "Dobhi", "Fatehpur", "Wazirganj"]
purposes = ["Agriculture", "Livestock", "Petty trade", "Education", "Health", "Housing"]
shg_names = ["Jagriti", "Saraswati", "Lakshmi", "Ekta", "Pragati", "Sahyog", "Ujjwala", "Kiran", "Asha", "Shakti"]
header_b = [
    "Loan ID", "Disbursement Date", "Block", "SHG Name", "Member Count",
    "Loan Amount (Rs)", "Purpose", "Repayment Status", "Amount Repaid (Rs)", "Source",
]
rows_b: list[list] = []
for i in range(360):
    year = rng.choice([2022, 2022, 2023, 2023, 2023, 2024, 2024, 2024, 2024])
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    block = rng.choice(blocks)
    purpose = rng.choices(purposes, weights=[30, 22, 18, 10, 10, 10])[0]
    amount = rng.choice([15000, 20000, 25000, 30000, 40000, 50000, 60000, 75000, 100000])
    if purpose == "Housing":
        amount = rng.choice([60000, 75000, 100000, 120000])
    if year == 2024:
        status = rng.choices(["Regular", "Overdue", "Closed"], weights=[70, 15, 15])[0]
    elif year == 2023:
        status = rng.choices(["Regular", "Overdue", "Closed"], weights=[40, 20, 40])[0]
    else:
        status = rng.choices(["Regular", "Overdue", "Closed"], weights=[15, 15, 70])[0]
    if status == "Closed":
        repaid: int | str = amount
    elif status == "Regular":
        repaid = int(amount * rng.uniform(0.2, 0.9)) // 100 * 100
    else:
        repaid = int(amount * rng.uniform(0.0, 0.5)) // 100 * 100
    if year == 2024 and month >= 10 and status == "Regular" and rng.random() < 0.6:
        repaid = ""  # not yet reported
    rows_b.append([
        f"LN-{year}-{i + 1:04d}", f"{year}-{month:02d}-{day:02d}", block,
        f"{rng.choice(shg_names)} SHG {rng.randint(1, 9)}", rng.randint(8, 15),
        amount, purpose, status, repaid, "Block MIS export",
    ])
rows_b.sort(key=lambda r: r[1])
write("shg_loan_register.csv", header_b, rows_b)

# ---------------------------------------------------------------- fixture C
# Wide enrolment with years as columns, plus an infrastructure table to join.
school_blocks = ["Atri", "Barachatti", "Belaganj", "Dobhi"]
school_words = ["Rajkiya", "Utkramit", "Madhya", "Prathmik", "Kanya", "Adarsh", "Navin", "Buniyadi"]
village_words = ["Tetariya", "Bankat", "Chakand", "Lodipur", "Sonbarsa", "Karmauni", "Bhadeya", "Amas", "Khizarsarai", "Rampur"]
header_c1 = ["School Code", "School Name", "Block", "Girls 2022", "Girls 2023", "Girls 2024", "Boys 2022", "Boys 2023", "Boys 2024", "Source"]
header_c2 = ["School Code", "Toilets functional (girls)", "Drinking water", "Electricity", "Classrooms", "Inspected On", "Source"]
rows_c1: list[list] = []
rows_c2: list[list] = []
for i in range(40):
    code = f"10{rng.randint(10, 99)}{i:04d}"
    name = f"{rng.choice(school_words)} Vidyalaya {rng.choice(village_words)}"
    block = school_blocks[i % 4]
    g = rng.randint(40, 180)
    b = rng.randint(40, 180)
    girls = [g, g + rng.randint(-10, 15), g + rng.randint(-10, 25)]
    boys = [b, b + rng.randint(-10, 15), b + rng.randint(-10, 25)]
    rows_c1.append([code, name, block, *girls, *boys, "UDISE-style school return"])
    rows_c2.append([
        code, rng.choices(["Yes", "No"], weights=[65, 35])[0],
        rng.choices(["Yes", "No"], weights=[85, 15])[0],
        rng.choices(["Yes", "No"], weights=[75, 25])[0],
        rng.randint(2, 9), f"2024-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}", "Inspection register",
    ])
write("school_enrolment_by_year.csv", header_c1, rows_c1)
write("school_infrastructure.csv", header_c2, rows_c2)
print("wrote", sorted(p.name for p in OUT.iterdir()))
