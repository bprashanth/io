#!/usr/bin/env python3
"""Generate five wholly synthetic, related NGO workbooks; no personal data inputs."""
from datetime import datetime, timedelta
from pathlib import Path
import random

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

HERE = Path(__file__).resolve().parent
SEED = 20261114
OFFICERS = ["Kiran Pawar", "Madhavi Jadhav", "Imran Shaikh"]
GROUPS = ["Pragati", "Ujjwal", "Sakhi", "Maitri", "Disha", "Navchetna"]


def day(month, date):
    return datetime(2025 + month // 12, month % 12 + 1, date)


def workbook(filename, sheets):
    book = Workbook()
    book.remove(book.active)
    for name, headers, rows in sheets:
        sheet = book.create_sheet(name)
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        table = Table(displayName=name, ref=sheet.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)
        for cells in sheet:
            for cell in cells:
                cell.font = Font(name="Arial", size=11, bold=cell.row == 1)
                if isinstance(cell.value, datetime):
                    cell.number_format = "yyyy-mm-dd"
        for cell in sheet[1]:
            cell.fill = PatternFill("solid", fgColor="D9EAF7")
            cell.comment = Comment("Synthetic input generated with seed 20261114; see Notes and generate.py.", "Fixture")
            sheet.column_dimensions[cell.column_letter].width = min(32, max(18, len(cell.value) + 3))
    notes = book.create_sheet("Notes")
    for line in [
        "SYNTHETIC: fictional NGO Sahyog Livelihoods; all people and places are invented combinations.",
        "All rows are generated inputs, not a workbook for manual entry. No external data or formulas.",
        "Observation window: January 2025 to June 2026 (18 months); rupee amounts are INR.",
        "Stable IDs join sheets. Each household has exactly one group membership and one loan.",
        "Repayments are monthly observations, not loan principal totals; paid_rs is amount collected toward that due.",
        "Blank paid_rs means unknown, not zero. Blank paid_on is a missing receipt date.",
        "Training attended_members is blank when the attendance count is unknown; missed sessions have zero.",
        "Mixed case/spaces, rupee/comma text, blank notes/livelihoods, and alternate date strings are deliberate.",
        "Planted: Sakhi misses October 2025 training; repayment falls from November (association, not causation).",
        "Planted: Kiran has 30 assigned households versus 9 each, with fewer monthly visits per household.",
        "Planted: 24 of 48 households are in Ward 04; group/ward clustering is deliberate.",
        "Officer capacity of 16 households used by the proof is an illustrative planning assumption, not policy.",
        "Seed 20261114; edit generate.py to change assumptions, then regenerate and rerun the proof.",
    ]:
        notes.append([line])
        notes.cell(notes.max_row, 1).font = Font(name="Arial", size=11)
    notes.column_dimensions["A"].width = 125
    # Fixed metadata aids repeatability (ZIP timestamps can still vary).
    book.properties.created = book.properties.modified = datetime(2026, 11, 14)
    book.save(HERE / filename)


def main():
    rng = random.Random(SEED)
    first = ["Savita", "Jyoti", "Meena", "Sunita", "Farida", "Lata", "Rekha", "Anita"]
    last = ["More", "Shinde", "Kamble", "Patil", "Deshmukh", "Gaikwad"]
    villages = {"Ward 01": "Ambewadi", "Ward 02": "Chandrapurwadi", "Ward 03": "Sonkheda", "Ward 04": "Devgaon Khurd"}
    households, members, loans, payments, visits, trainings = [], [], [], [], [], []
    groups = [(f"G{g+1:02}", name, day(0, 1)) for g, name in enumerate(GROUPS)]
    for i in range(48):
        hid, gid, lid = f"H{i+1:03}", f"G{i//8+1:02}", f"L{i+1:03}"
        ward = "Ward 04" if i < 24 else f"Ward {(i-24)//8+1:02}"
        if i in (30, 31):
            ward = "Ward 02"
        if i in (38, 39):
            ward = "Ward 03"
        if i in (46, 47):
            ward = "Ward 01"
        officer = OFFICERS[0 if i < 30 else 1 if i < 39 else 2]
        raw_ward = f" {ward.lower()} " if i % 13 == 0 else ward.upper() if i % 11 == 0 else ward
        households.append((hid, f"{first[i%8]} {last[i//8]}", raw_ward, villages[ward], day(0, 2 + i % 7),
                           officer, None if i % 17 == 0 else rng.choice(["Tailoring", "Dairy", "Farm labour", "Petty trade"])))
        members.append((f"M{i+1:03}", hid, gid, day(0, 9)))
        principal = 18000 if i % 2 == 0 else 14400
        loans.append((lid, hid, gid, principal, day(0, 10)))
        for month in range(18):
            due = principal // 18
            # Distinct comparison-group baselines make the slope plot legible.
            rate = .99 - .03 * (i // 8)
            if gid == "G03" and month >= 10:
                rate = .49 - .01 * (month - 10)
            paid = round(due * min(1, rate + rng.uniform(-.015, .015)))
            raw_paid = None if (i, month) in {(0, 2), (40, 13)} else f"₹{paid:,}" if i % 13 == 0 else paid
            due_on = day(month, 28)
            # ISO strings and Excel date cells intentionally coexist.
            raw_date = due_on.strftime("%Y-%m-%d") if i % 19 == 0 else due_on
            payments.append((f"R{i+1:03}-{month+1:02}", lid, raw_date, due, raw_paid,
                             None if (i + month) % 23 == 0 else due_on + timedelta(days=1)))
            visited = (i + month) % 3 == 0 if i < 30 else (i + month) % 7 != 0
            if visited:
                visits.append((f"V{len(visits)+1:04}", hid, officer, day(month, 12 + i % 10),
                               " follow up " if i % 9 == 0 else "Routine", None if i % 10 == 0 else "Ledger reviewed"))
    for g in range(6):
        for month in range((g // 2) * 3, 18, 3):
            missed = g == 2 and month == 9
            trainings.append((f"T{len(trainings)+1:03}", f"G{g+1:02}", day(month, 15),
                              ["Bookkeeping", "Loan planning", "Market access"][(month // 3) % 3],
                              " missed " if missed else "HELD" if g % 2 else "Held",
                              0 if missed else None if (g, month) == (5, 12) else 7 + (g + month) % 2,
                              None if missed else "Nandita Kulkarni"))
    workbook("households.xlsx", [("Households", ["household_id", "contact_name", "ward", "village", "enrolled_on", "assigned_officer", "livelihood"], households)])
    workbook("groups.xlsx", [("Groups", ["group_id", "group_name", "formed_on"], groups),
                             ("Members", ["member_id", "household_id", "group_id", "joined_on"], members)])
    workbook("loans.xlsx", [("Loans", ["loan_id", "household_id", "group_id", "principal_rs", "disbursed_on"], loans),
                            ("Repayments", ["repayment_id", "loan_id", "due_on", "due_rs", "paid_rs", "paid_on"], payments)])
    workbook("field_visits.xlsx", [("Visits", ["visit_id", "household_id", "officer", "visited_on", "purpose", "notes"], visits)])
    workbook("trainings.xlsx", [("Trainings", ["training_id", "group_id", "scheduled_on", "topic", "status", "attended_members", "facilitator"], trainings)])
    print(f"Generated 5 workbooks: 48 households, 6 groups, 48 loans, {len(payments)} repayments, {len(visits)} visits, {len(trainings)} trainings")


if __name__ == "__main__":
    main()
