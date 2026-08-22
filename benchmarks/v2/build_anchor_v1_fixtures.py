#!/usr/bin/env python3
"""Deterministically build the anchor-v1 fixtures and query manifest.

Mirrors three real NGO asks (a sportathon baseline/endline fitness cohort, a
family-welfare household survey, a scholarship outreach-vs-application
reconciliation with messy school names) plus two generic patterns (a
same-concept/different-header cross-year join, and a repeat-donor share).
Regenerating with the same seed reproduces the same synthetic values.

Run with the v2 project's venv:
    .venv-v2/bin/python benchmarks/v2/build_anchor_v1_fixtures.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "benchmarks" / "v2" / "anchor-v1"
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = ROOT / "benchmarks" / "v2" / "query-anchor-v1.json"
SEED = 20260823
rng = random.Random(SEED)

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Rohan",
    "Kabir", "Aryan", "Devansh", "Yash", "Om", "Anaya", "Diya", "Ira", "Myra", "Sara",
    "Aadhya", "Kiara", "Pari", "Riya", "Ananya", "Priya", "Neha", "Pooja", "Kavya", "Meera",
    "Sunita", "Anil", "Ramesh", "Suresh", "Deepak", "Manoj", "Rajesh", "Vikas", "Sanjay", "Prakash",
    "Fatima", "Ayesha", "Zara", "Imran", "Irfan", "Nasreen", "Salma", "Asha", "Kiran", "Lata",
]
LAST_NAMES = [
    "Sharma", "Verma", "Yadav", "Singh", "Kumar", "Gupta", "Mishra", "Pandey", "Tiwari", "Shah",
    "Patel", "Rane", "More", "Pawar", "Jadhav", "Kamble", "Gaikwad", "Chavan", "Sawant", "Shaikh",
    "Ansari", "Khan", "Sheikh", "Reddy", "Nair", "Iyer", "Menon", "Das", "Ghosh", "Roy",
    "Mondal", "Bhat", "Naidu", "Rao", "Chowdhury", "Bora", "Kaur", "Malik", "Bansal", "Agarwal",
]


def full_name() -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def unique_names(n: int) -> list[str]:
    used: set[str] = set()
    names: list[str] = []
    while len(names) < n:
        name = full_name()
        if name not in used:
            used.add(name)
            names.append(name)
    return names


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


# ============================================================ fixture 1 ===
# Sportathon fitness cohort: baseline and endline, same Child ID, ~8 dropouts.
SITES = ["Dharavi", "Govandi", "Mankhurd", "Kurla", "Chembur", "Wadala"]
COACHES = {
    "Dharavi": ["Ramesh Yadav", "Sunita More"],
    "Govandi": ["Irfan Sheikh", "Kavita Pawar"],
    "Mankhurd": ["Deepak Rane", "Fatima Shaikh"],
    "Kurla": ["Vikram Jadhav", "Anjali Kamble"],
    "Chembur": ["Suresh Gaikwad", "Nasreen Ansari"],
    "Wadala": ["Prakash Sawant", "Meena Chavan"],
}
child_names = unique_names(200)
child_ids = [f"SPA-{i + 1:04d}" for i in range(200)]
baseline_rows: list[list] = []
endline_rows: list[list] = []
dropout_ids = set(rng.sample(child_ids, 8))
# Engineer the top of the sit-ups-improvement distribution so the top-5
# ranking task has no ties: 6 distinct large deltas, kept clear of the
# randint ceiling used for everyone else.
top_improver_ids = rng.sample([cid for cid in child_ids if cid not in dropout_ids], 6)
top_improver_delta = dict(zip(top_improver_ids, [16, 15, 14, 13, 12, 11]))
sport_header = ["Child ID", "Child Name", "Gender", "Age", "Location", "Coach", "Height cm",
                "Weight kg", "Shuttle Run sec", "Sit Ups", "Standing Jump cm", "Life Skills Score"]
for cid, name in zip(child_ids, child_names):
    site = rng.choice(SITES)
    coach = rng.choice(COACHES[site])
    gender = rng.choice(["M", "F"])
    age = rng.randint(8, 14)
    height_b = round(rng.uniform(118, 162), 1)
    weight_b = round(rng.uniform(22, 54), 1)
    shuttle_b = round(rng.uniform(9.0, 14.5), 1)
    situps_b = rng.randint(8, 28)
    jump_b = round(rng.uniform(85, 158), 1)
    life_b = rng.randint(4, 15)
    baseline_rows.append([cid, name, gender, age, site, coach, height_b, weight_b, shuttle_b, situps_b, jump_b, life_b])
    if cid in dropout_ids:
        continue
    height_e = round(height_b + rng.uniform(0.3, 2.5), 1)
    weight_e = round(weight_b + rng.uniform(0.2, 3.0), 1)
    shuttle_e = round(shuttle_b + rng.uniform(-2.2, 0.8), 1)
    situps_e = situps_b + top_improver_delta.get(cid, rng.randint(-2, 9))
    jump_e = round(jump_b + rng.uniform(-5, 22), 1)
    life_e = min(20, life_b + rng.randint(0, 7))
    endline_rows.append([cid, name, gender, age, site, coach, height_e, weight_e, shuttle_e, situps_e, jump_e, life_e])
write_csv("sportathon_baseline.csv", sport_header, baseline_rows)
write_csv("sportathon_endline.csv", sport_header, endline_rows)

# ============================================================ fixture 2 ===
# Family-welfare household survey workbook, sheet "Survey".
fw_villages = ["Rampur", "Sherpur", "Islampur", "Nawada", "Barhi"]
fw_header = ["HH ID", "Head of Household", "Village", "Members", "Earners", "Monthly Income Rs",
             "Land Acres", "Has Ration Card", "Children in School", "Children Total",
             "Chronic Illness", "Roof Type", "Loan Outstanding Rs"]
fw_heads = unique_names(30)
blank_income_idx = set(rng.sample(range(30), 2))
fw_rows: list[list] = []
for i in range(30):
    members = rng.randint(3, 11)
    earners = rng.randint(1, min(members, 4))
    income = None if i in blank_income_idx else rng.randint(3000, 25000)
    land = round(rng.uniform(0, 3), 1)
    ration = rng.choices(["Yes", "No"], weights=[70, 30])[0]
    children_total = rng.randint(0, 5)
    children_school = rng.randint(0, children_total)
    chronic = rng.choices(["Yes", "No"], weights=[25, 75])[0]
    roof = rng.choices(["Kutcha", "Pucca"], weights=[40, 60])[0]
    loan = rng.choice([0, 0, 5000, 10000, 15000, 20000, 30000, 45000])
    fw_rows.append([f"FW-{i + 1:03d}", fw_heads[i], rng.choice(fw_villages), members, earners,
                     income, land, ration, children_school, children_total, chronic, roof, loan])
# The small-integer vulnerability composite (see the fw-vulnerability-ranking
# task below) will realistically tie across 30 households; the gold SQL's
# secondary "HH ID" sort key keeps the full ranking reproducible without
# distorting household sizes to force a unique score.

workbook = Workbook()
sheet = workbook.active
sheet.title = "Survey"
sheet.append(fw_header)
for row in fw_rows:
    sheet.append(row)
workbook.save(OUT / "fw_households.xlsx")

# ============================================================ fixture 3 ===
# Scholarship outreach vs applications, with messy school-name variants.
lpf_villages = [
    "Tetariya", "Bankat", "Chakand", "Lodipur", "Sonbarsa", "Karmauni", "Bhadeya", "Amas", "Khizarsarai", "Rampur",
    "Barhi", "Islampur", "Nawada", "Sherghati", "Dumraon", "Buxar", "Arwal", "Jehanabad", "Aurangabad", "Rafiganj",
    "Imamganj", "Wazirganj", "Belaganj", "Atri", "Barachatti", "Dobhi", "Fatehpur", "Konch", "Guraru", "Paraiya",
    "Tekari", "Modanganj", "Amba", "Neemchak", "Bathani", "Bodh Gaya", "Sherpur", "Manpur", "Domuhan", "Chandauti",
    "Muhra", "Sikaria", "Kothi", "Bishunpur", "Amawan", "Deorhi", "Mahuar", "Sarwan", "Nimi", "Panchgama",
]
lpf_blocks = ["Atri", "Barachatti", "Belaganj", "Dobhi", "Fatehpur", "Wazirganj"]
levels = ["Prathmik", "Madhya", "Uchcha Madhyamik", "Kanya", "Adarsh", "Navin", "Buniyadi", "Madhyamik"]
deities = ["Ganesh", "Saraswati", "Ram", "Krishna", "Durga", "Hanuman", "Shiv"]

templates = [
    lambda: f"{rng.choice(lpf_villages)} {rng.choice(levels)} Vidyalaya",
    lambda: f"{rng.choice(lpf_villages)} {rng.choice(levels)} Vidyalaya, Zilla Parishad",
    lambda: f"{rng.choice(lpf_villages)} Kanya Shala",
    lambda: f"Shri {rng.choice(deities)} Vidyalaya, {rng.choice(lpf_villages)}",
    lambda: f"{rng.choice(lpf_villages)} Prathmik Shala (Zilla Parishad)",
    lambda: f"Rashtriya {rng.choice(levels)} Vidyalaya {rng.choice(lpf_villages)}",
]
# A plain set's iteration order depends on Python's per-process string hash
# randomization, which would make the shuffled school order (and therefore
# every downstream rng draw) non-reproducible across runs. Build the pool as
# an insertion-ordered list instead so the fixed seed is the only source of
# randomness.
school_names: list[str] = []
seen_schools: set[str] = set()
while len(school_names) < 180:
    name = rng.choice(templates)()
    if name not in seen_schools:
        seen_schools.add(name)
        school_names.append(name)
rng.shuffle(school_names)

outreach_header = ["School Name", "Block", "Students Reached", "Applications Expected", "Contact Teacher", "Date"]
outreach_rows: list[list] = []
for name in school_names:
    students = rng.randint(20, 150)
    expected = rng.randint(2, 30)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    outreach_rows.append([name, rng.choice(lpf_blocks), students, expected, full_name(), f"2024-{month:02d}-{day:02d}"])
write_csv("lpf_outreach.csv", outreach_header, outreach_rows)


def messy_variant(name: str) -> str:
    r = rng.random()
    if r < 0.35:
        return name
    if r < 0.50:
        return name.upper() if rng.random() < 0.5 else name.lower()
    if r < 0.65 and "Vidyalaya" in name:
        return name.replace("Vidyalaya", "Vidyalay")
    if r < 0.80 and "Zilla Parishad" in name:
        return name.replace("Zilla Parishad", "Z.P.")
    if r < 0.90:
        return name + "  "
    chars = list(name)
    idxs = [i for i, c in enumerate(chars) if c.isalpha() and i > 4]
    i = rng.choice(idxs) if idxs else rng.randrange(len(chars))
    letters = "abcdefghijklmnopqrstuvwxyz"
    replacement = rng.choice([c for c in letters if c != chars[i].lower()])
    chars[i] = replacement.upper() if chars[i].isupper() else replacement
    return "".join(chars)


courses = ["ITI Electrician", "Nursing Assistant", "Computer Operator", "Tailoring & Fashion Design",
           "Beautician", "Diploma Civil Engineering", "Retail Sales Associate"]
statuses = ["Submitted", "Verified", "Rejected", "Incomplete"]
applicants = unique_names(150)
applications_header = ["Applicant", "School", "Course", "Status", "Marks"]
applications_rows: list[list] = []
for applicant in applicants:
    target_school = rng.choice(school_names)
    applications_rows.append([applicant, messy_variant(target_school), rng.choice(courses),
                               rng.choices(statuses, weights=[30, 35, 15, 20])[0], rng.randint(30, 95)])
write_csv("lpf_applications.csv", applications_header, applications_rows)

# ============================================================ fixture 4 ===
# Attendance registers: same concept, different headers across years.
centres = ["Dharavi Balwadi", "Govandi Balwadi", "Mankhurd Balwadi", "Kurla Balwadi",
           "Chembur Balwadi", "Wadala Balwadi", "Sion Balwadi", "Worli Balwadi"]
months = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
rate_2023 = {"Dharavi Balwadi": 72, "Govandi Balwadi": 78, "Mankhurd Balwadi": 65,
             "Kurla Balwadi": 84, "Chembur Balwadi": 70, "Wadala Balwadi": 88,
             "Sion Balwadi": 60, "Worli Balwadi": 80}
rate_2024 = dict(rate_2023)
for centre in centres:
    if centre == "Kurla Balwadi":
        rate_2024[centre] = rate_2023[centre] - 20  # deliberate, unambiguous biggest drop
    else:
        rate_2024[centre] = max(35, min(97, rate_2023[centre] + rng.uniform(-6, 4)))

header_2023 = ["Centre", "Month", "Enrolled Kids", "Avg Daily Present"]
header_2024 = ["centre_name", "month", "enrolment", "average_attendance"]
rows_2023: list[list] = []
rows_2024: list[list] = []
for centre in centres:
    base_enrol = rng.randint(40, 90)
    for month in months:
        enrol_23 = base_enrol + rng.randint(-3, 3)
        month_rate_23 = max(30, min(99, rate_2023[centre] + rng.uniform(-5, 5)))
        present_23 = round(enrol_23 * month_rate_23 / 100.0)
        rows_2023.append([centre, month, enrol_23, present_23])
        enrol_24 = base_enrol + rng.randint(-2, 6)
        month_rate_24 = max(30, min(99, rate_2024[centre] + rng.uniform(-5, 5)))
        present_24 = round(enrol_24 * month_rate_24 / 100.0)
        rows_2024.append([centre, month, enrol_24, present_24])
write_csv("attendance_2023.csv", header_2023, rows_2023)
write_csv("attendance_2024.csv", header_2024, rows_2024)

# ============================================================ fixture 5 ===
# Donations register with one-time and repeat donors.
donor_pool = unique_names(220)
cities = ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad"]
modes = ["Cash", "Cheque", "Online", "UPI"]
campaigns = ["Winter Relief", "Girl Child Education", "Sportathon Fund", "Health Camp", "General Fund"]
repeat_donors = donor_pool[:55]  # will be sampled 2-4 times each
one_time_donors = donor_pool[55:]
donor_sequence: list[str] = []
for donor in repeat_donors:
    donor_sequence.extend([donor] * rng.randint(2, 4))
remaining = 300 - len(donor_sequence)
donor_sequence.extend(rng.sample(one_time_donors, remaining))
rng.shuffle(donor_sequence)
donations_header = ["Receipt No", "Date", "Donor", "Amount", "Mode", "Campaign", "City"]
donations_rows: list[list] = []
for i, donor in enumerate(donor_sequence):
    year = rng.choice([2023, 2023, 2024, 2024, 2024])
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    amount = rng.choice([500, 1000, 1500, 2000, 2500, 5000, 7500, 10000, 15000, 25000])
    donations_rows.append([f"RCPT-{i + 1:05d}", f"{year}-{month:02d}-{day:02d}", donor, amount,
                            rng.choice(modes), rng.choice(campaigns), rng.choice(cities)])
write_csv("donations.csv", donations_header, donations_rows)

# ================================================================ tasks ===
LPF_BEST_MATCH_CTE = (
    'WITH best AS (SELECT a."Applicant" AS applicant, o."School Name" AS matched_school, '
    'jaro_winkler_similarity(lower(trim(a."School")), lower(trim(o."School Name"))) AS sim '
    'FROM lpf_applications AS a JOIN lpf_outreach AS o ON jaro_winkler_similarity(lower(trim(a."School")), '
    'lower(trim(o."School Name"))) >= 0.9 QUALIFY ROW_NUMBER() OVER '
    '(PARTITION BY a."Applicant" ORDER BY sim DESC, o."School Name") = 1) '
)
ATTENDANCE_CTE = (
    'WITH combined AS (SELECT "Centre" AS centre, 2023 AS year, "Avg Daily Present" / "Enrolled Kids" * 100.0 AS rate '
    'FROM attendance_2023 UNION ALL SELECT centre_name AS centre, 2024 AS year, '
    'average_attendance / enrolment * 100.0 AS rate FROM attendance_2024) '
)

tasks = [
    {"id": "sportathon-improvement-ranking", "order_matters": True,
     "pattern": "join two same-shape tables on an id, compute a delta, rank top five, dropouts fall out via inner join",
     "tables": ["sportathon_baseline", "sportathon_endline"],
     "gold_sql": 'SELECT b."Child Name", e."Sit Ups" - b."Sit Ups" AS situps_improvement FROM sportathon_baseline AS b '
                 'JOIN sportathon_endline AS e ON b."Child ID" = e."Child ID" '
                 'ORDER BY situps_improvement DESC, b."Child Name" LIMIT 5',
     "phrasings": ["top 5 kids who improved the most in situps from baseline to endline",
                   "which five children showed the biggest jump in situp count between the first and second fitness test",
                   "rank the top 5 by how much their situp count went up since baseline, best improver first"]},
    {"id": "sportathon-site-average-change",
     "pattern": "join on id, compute per-row delta, average by group",
     "tables": ["sportathon_baseline", "sportathon_endline"],
     "gold_sql": 'SELECT b."Location", AVG(e."Shuttle Run sec" - b."Shuttle Run sec") AS avg_shuttle_change '
                 'FROM sportathon_baseline AS b JOIN sportathon_endline AS e ON b."Child ID" = e."Child ID" '
                 'GROUP BY b."Location" ORDER BY b."Location"',
     "phrasings": ["site wise average change in shuttle run time from baseline to endline, negative means faster",
                   "for each centre how much did the shuttle sprint time change on average between the two tests",
                   "average shuttle run improvement or decline per location, endline minus baseline"]},
    {"id": "sportathon-dropouts",
     "pattern": "anti-join two same-shape tables on an id, project one column",
     "tables": ["sportathon_baseline", "sportathon_endline"],
     "gold_sql": 'SELECT b."Child Name" FROM sportathon_baseline AS b WHERE NOT EXISTS '
                 '(SELECT 1 FROM sportathon_endline AS e WHERE e."Child ID" = b."Child ID") ORDER BY b."Child Name"',
     "phrasings": ["which children were tested at baseline but missing from the endline",
                   "list kids who dropped out before the second round of testing",
                   "names of children present in the first fitness test but not in the follow up"]},
    {"id": "fw-vulnerability-ranking", "order_matters": False,
     "pattern": "weighted sum of a numeric difference and several yes/no flags, full ranking",
     "tables": ["fw_households"],
     "gold_sql": 'SELECT "HH ID", ("Members" - "Earners") + CASE WHEN "Has Ration Card" = \'No\' THEN 2 ELSE 0 END '
                 '+ CASE WHEN "Chronic Illness" = \'Yes\' THEN 2 ELSE 0 END '
                 '+ CASE WHEN "Roof Type" = \'Kutcha\' THEN 1 ELSE 0 END AS vulnerability_score '
                 'FROM fw_households ORDER BY vulnerability_score DESC, "HH ID"',
     "phrasings": ["score each household as members minus earners, plus 2 if they have no ration card, plus 2 if there is a chronic illness, plus 1 for a kutcha roof - rank highest score first with the household id",
                   "for every household add household size minus number of earners, 2 points for missing ration card, 2 points for chronic illness in the family, 1 point for a kutcha roof - show id and total, most vulnerable on top",
                   "compute a vulnerability score per household as (members - earners) + 2 times no ration card + 2 times chronic illness yes + 1 times kutcha roof, list household id and score sorted highest to lowest"]},
    {"id": "fw-income-per-member-missing", "order_matters": True,
     "pattern": "ratio of two columns excluding null rows, ascending rank",
     "tables": ["fw_households"],
     "gold_sql": 'SELECT "HH ID", "Monthly Income Rs" / "Members" AS income_per_member FROM fw_households '
                 'WHERE "Monthly Income Rs" IS NOT NULL ORDER BY income_per_member ASC, "HH ID"',
     "phrasings": ["monthly income divided by family size for each household, skip the ones with income not filled in, lowest first",
                   "per person monthly earning by household excluding blank income entries, ascending order",
                   "rank households by income per family member from lowest to highest, leave out households where income is missing"]},
    {"id": "lpf-reconciliation-fuzzy",
     "pattern": "fuzzy string join with best-match dedup, left join to include zero-count rows, group count",
     "tables": ["lpf_outreach", "lpf_applications"],
     "gold_sql": LPF_BEST_MATCH_CTE + 'SELECT o."School Name", COUNT(b.applicant) AS applications_received '
                 'FROM lpf_outreach AS o LEFT JOIN best AS b ON b.matched_school = o."School Name" '
                 'GROUP BY o."School Name" ORDER BY o."School Name"',
     "phrasings": ["for each school we contacted, how many applications came in - match school names loosely since spellings differ, include schools with none",
                   "school wise application count matching names approximately even with typos or short forms, zero counted for schools with no applications, alphabetical by school",
                   "how many applications landed per outreach school when we match names even if written a bit differently, show every school including those with zero"]},
    {"id": "lpf-gap",
     "pattern": "fuzzy string join with best-match dedup, group count compared against a stated column, threshold filter",
     "tables": ["lpf_outreach", "lpf_applications"],
     "gold_sql": LPF_BEST_MATCH_CTE + 'SELECT o."School Name", COUNT(b.applicant) AS applications_received, '
                 'o."Applications Expected" FROM lpf_outreach AS o LEFT JOIN best AS b ON b.matched_school = o."School Name" '
                 'GROUP BY o."School Name", o."Applications Expected" '
                 'HAVING COUNT(b.applicant) < o."Applications Expected" / 2.0 ORDER BY o."School Name"',
     "phrasings": ["which schools got less than half the applications we expected from them, matching names loosely",
                   "list schools where actual applications received, fuzzy matched, fall short of half the expected number",
                   "schools under-delivering on applications - received less than 50 percent of what was expected, loose name matching"]},
    {"id": "attendance-cross-year",
     "pattern": "union two differently-headered tables after renaming, pivot with conditional aggregation",
     "tables": ["attendance_2023", "attendance_2024"],
     "gold_sql": ATTENDANCE_CTE + 'SELECT centre, AVG(CASE WHEN year = 2023 THEN rate END) AS avg_rate_2023, '
                 'AVG(CASE WHEN year = 2024 THEN rate END) AS avg_rate_2024 FROM combined GROUP BY centre ORDER BY centre',
     "phrasings": ["centre wise attendance percentage for 2023 and 2024 side by side",
                   "for each centre show the average turnout rate in both years next to each other",
                   "compare average daily attendance rate per centre across the two years, one row each"]},
    {"id": "attendance-biggest-drop", "order_matters": True,
     "pattern": "union two differently-headered tables, pivot, compute a difference, rank",
     "tables": ["attendance_2023", "attendance_2024"],
     "gold_sql": ATTENDANCE_CTE + ', by_year AS (SELECT centre, AVG(CASE WHEN year = 2023 THEN rate END) AS avg_2023, '
                 'AVG(CASE WHEN year = 2024 THEN rate END) AS avg_2024 FROM combined GROUP BY centre) '
                 'SELECT centre, avg_2023 - avg_2024 AS drop_pp FROM by_year ORDER BY drop_pp DESC, centre LIMIT 1',
     "phrasings": ["which centre saw the biggest fall in attendance rate from 2023 to 2024",
                   "rank centres by how much their turnout percentage dropped between the two years, worst first",
                   "where did attendance percentage decline the most year on year"]},
    {"id": "donations-repeat-share",
     "pattern": "group by entity, conditional sum and count, single-row share calculation",
     "tables": ["donations"],
     "gold_sql": 'WITH counts AS (SELECT "Donor", COUNT(*) AS gifts, SUM("Amount") AS donor_total FROM donations '
                 'GROUP BY "Donor") SELECT 100.0 * SUM(CASE WHEN gifts > 1 THEN donor_total ELSE 0 END) / SUM(donor_total) '
                 'AS repeat_share_percent, SUM(CASE WHEN gifts > 1 THEN 1 ELSE 0 END) AS repeat_donor_count FROM counts',
     "phrasings": ["what percent of total donation value comes from people who gave more than once, and how many repeat donors are there",
                   "share of money raised from repeat givers versus one-time givers, in percent, plus a count of repeat givers",
                   "out of all donation rupees collected, what fraction came from donors who contributed on more than one occasion - give percent and the number of such donors"]},
]

manifest = {
    "schema_version": 2,
    "status": "frozen-anchor-before-first-model-run",
    "purpose": (
        "Frozen anchor benchmark for the text-to-SQL gate, mirroring three real NGO "
        "asks (a sportathon fitness cohort with dropouts, a family-welfare household "
        "survey workbook, and a scholarship outreach-vs-application reconciliation with "
        "messy school names needing a fuzzy string join) plus two generic patterns (a "
        "same-concept/different-header cross-year attendance join, and a repeat-donor "
        "share). Questions are terse and do not name columns verbatim. No router, "
        "prompt or evaluator rule may be changed after the first model run on this "
        "file; a changed rule requires a new anchor version."
    ),
    "built_by": f"benchmarks/v2/build_anchor_v1_fixtures.py (seed {SEED})",
    "frozen_at": "2026-08-22",
    "dialect_requested_from_model": "sqlite",
    "execution_dialect": "duckdb",
    "comparison": {
        "numeric_rel_tolerance": 1e-06,
        "numeric_abs_tolerance": 0.06,
        "tolerance_note": "Gold values are unrounded. A model answer rounded to one decimal is still equal; an answer off by more than 0.06 absolute is wrong.",
        "column_names_required": False,
        "required_columns_may_be_a_projection_of_a_wider_result": True,
        "equivalent_long_or_grouped_wide_results_accepted": True,
        "row_order_required_only_for_ranking_tasks": True,
    },
    "tables": [
        {"name": "sportathon_baseline", "kind": "csv", "path": "benchmarks/v2/anchor-v1/sportathon_baseline.csv"},
        {"name": "sportathon_endline", "kind": "csv", "path": "benchmarks/v2/anchor-v1/sportathon_endline.csv"},
        {"name": "fw_households", "kind": "xlsx", "path": "benchmarks/v2/anchor-v1/fw_households.xlsx", "sheet": "Survey"},
        {"name": "lpf_outreach", "kind": "csv", "path": "benchmarks/v2/anchor-v1/lpf_outreach.csv"},
        {"name": "lpf_applications", "kind": "csv", "path": "benchmarks/v2/anchor-v1/lpf_applications.csv"},
        {"name": "attendance_2023", "kind": "csv", "path": "benchmarks/v2/anchor-v1/attendance_2023.csv"},
        {"name": "attendance_2024", "kind": "csv", "path": "benchmarks/v2/anchor-v1/attendance_2024.csv"},
        {"name": "donations", "kind": "csv", "path": "benchmarks/v2/anchor-v1/donations.csv"},
    ],
    "tasks": tasks,
}
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print("wrote", sorted(p.name for p in OUT.iterdir()))
print("wrote", MANIFEST_PATH.relative_to(ROOT))

# ============================================================ self-check ===
if __name__ == "__main__" and "--no-verify" not in sys.argv:
    sys.path.insert(0, str(ROOT / "benchmarks" / "scripts"))
    from run_v2_query_gate import create_database, rows  # noqa: E402

    db, evidence = create_database(manifest)
    for table in evidence["tables"]:
        print(f"table {table['name']}: {table['rows']} rows")
    for task in tasks:
        result = rows(db, task["gold_sql"])
        print(f"task {task['id']}: {len(result)} rows; first={result[:3]}")
    db.close()
