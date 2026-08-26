#!/usr/bin/env python3
"""Generate deterministic, fully synthetic NGO demo datasets."""

from __future__ import annotations

import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260825
random.seed(SEED)
np.random.seed(SEED)
RNG = random.Random(SEED)
ROOT = Path(__file__).resolve().parent


FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akash", "Amruta", "Ananya", "Aniket", "Anjali",
    "Arjun", "Avni", "Bhavna", "Chaitali", "Darshan", "Deepa", "Dev", "Diya",
    "Farhan", "Gauri", "Harsh", "Ira", "Ishaan", "Janhavi", "Kabir", "Kavya",
    "Kiran", "Krishna", "Lakshmi", "Manav", "Meera", "Mohit", "Nandini", "Neha",
    "Nikhil", "Omkar", "Pallavi", "Pooja", "Pranav", "Priya", "Rahul", "Rani",
    "Riya", "Rohan", "Sahil", "Sakshi", "Sameer", "Sana", "Shreya", "Siddharth",
    "Sneha", "Soham", "Tanvi", "Varun", "Ved", "Yash", "Zoya",
]
LAST_NAMES = [
    "Bhosale", "Chavan", "Deshmukh", "Gaikwad", "Jadhav", "Joshi", "Kadam",
    "Kale", "Kamble", "Khan", "Kulkarni", "Mane", "More", "Naik", "Patel",
    "Patil", "Pawar", "Raut", "Salunkhe", "Shaikh", "Shinde", "Singh", "Sonawane",
    "Thakur", "Wagh",
]


def all_names() -> list[str]:
    names = [f"{first} {last}" for first in FIRST_NAMES for last in LAST_NAMES]
    RNG.shuffle(names)
    return names


NAME_POOL = all_names()


def dmy(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def dates_between(start: date, end: date, count: int) -> list[date]:
    span = (end - start).days
    return [start + timedelta(days=RNG.randint(0, span)) for _ in range(count)]


def slug(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def phone(index: int) -> str:
    # Reserved-looking synthetic sequence; values are not sourced from real people.
    return f"+91 90000 {index % 100000:05d}"


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def generate_y_ultimate() -> dict[str, int]:
    folder = ROOT / "y-ultimate"
    folder.mkdir(exist_ok=True)

    sites = pd.DataFrame(
        [
            ("Yerawada Playfield", "Ward 6", 18.5526, 73.8877),
            ("Kondhwa Sports Hub", "Ward 27", 18.4648, 73.8942),
            ("Hadapsar Community Ground", "Ward 23", 18.5089, 73.9260),
            ("Warje Youth Centre", "Ward 13", 18.4865, 73.8078),
            ("Dhanori Activity Park", "Ward 4", 18.5941, 73.8962),
            ("Bibwewadi School Ground", "Ward 28", 18.4738, 73.8635),
        ],
        columns=["site", "ward", "lat", "lon"],
    )
    write_csv(sites, folder / "sites.csv")

    coaches = [
        "Neha Patil", "Sameer Shaikh", "Pooja Jadhav", "Akash More",
        "Kiran Gaikwad", "Sneha Pawar", "Rahul Mane", "Sana Khan",
    ]
    site_coaches = {
        site: [coaches[i % 8], coaches[(i + 3) % 8]]
        for i, site in enumerate(sites["site"])
    }
    session_dates = dates_between(date(2025, 7, 1), date(2026, 6, 30), 400)
    attendance_rows = []
    site_baseline = dict(zip(sites["site"], [34, 27, 39, 24, 31, 29]))
    for when in session_dates:
        site = RNG.choice(sites["site"].tolist())
        coach = RNG.choice(site_coaches[site])
        present = max(8, min(54, round(RNG.gauss(site_baseline[site], 7))))
        attendance_rows.append((site, when, coach, present))
    attendance_rows.sort(key=lambda row: (row[1], row[0]))
    attendance = pd.DataFrame(attendance_rows, columns=["site", "date", "coach_name", "children_present"])
    attendance["date"] = attendance["date"].map(dmy)
    write_csv(attendance, folder / "attendance_sessions.csv")

    child_names = NAME_POOL[:180]
    assessment_rows = []
    for i, child in enumerate(child_names):
        site = sites.iloc[i % len(sites)]["site"]
        age = RNG.randint(9, 17)
        fitness = RNG.gauss(0, 1)
        shuttle = round(max(8.2, min(19.8, 14.7 - fitness * 1.7 + RNG.gauss(0, 0.8))), 1)
        situps = max(6, min(48, round(23 + fitness * 6 + RNG.gauss(0, 4))))
        confidence = max(1, min(5, round(3.2 + fitness * 0.55 + RNG.gauss(0, 0.8))))
        assessment_rows.append((child, site, age, shuttle, situps, confidence))
    assessments = pd.DataFrame(
        assessment_rows,
        columns=["child_name", "site", "age", "shuttle_run_sec", "situps", "self_confidence_1to5"],
    )
    assessments.to_excel(folder / "assessments.xlsx", index=False, engine="openpyxl")

    donor_names = NAME_POOL[200:280]
    donor_rows = []
    modes = ["UPI", "Bank transfer", "Cheque", "Card"]
    donation_dates = dates_between(date(2025, 4, 1), date(2026, 3, 31), 120)
    for i, when in enumerate(donation_dates):
        donor = RNG.choice(donor_names)
        email = f"{slug(donor)}{donor_names.index(donor) + 1}@example.org"
        amount = RNG.choice([500, 1000, 1500, 2000, 2500, 5000, 7500, 10000, 15000, 25000])
        donor_rows.append((donor, email, amount, when, RNG.choices(modes, weights=[45, 32, 8, 15])[0]))
    donor_rows.sort(key=lambda row: row[3])
    donors = pd.DataFrame(donor_rows, columns=["donor_name", "email", "amount_inr", "date", "mode"])
    donors["date"] = donors["date"].map(dmy)
    write_csv(donors, folder / "donor_transactions.csv")
    return {
        "attendance_sessions.csv": len(attendance), "assessments.xlsx": len(assessments),
        "donor_transactions.csv": len(donors), "sites.csv": len(sites),
    }


def generate_foundation_without() -> dict[str, int]:
    folder = ROOT / "foundation-without"
    folder.mkdir(exist_ok=True)

    heads = NAME_POOL[300:330]
    clusters = [
        ("Janata Vasahat", 18.4914, 73.8438),
        ("Yerawada Ward", 18.5588, 73.8868),
        ("Kasewadi", 18.5010, 73.8751),
        ("Hadapsar Ward", 18.5019, 73.9251),
        ("Ramtekdi", 18.4912, 73.9128),
    ]
    household_rows = []
    vulnerabilities: dict[str, int] = {}
    for i, head in enumerate(heads):
        ward, base_lat, base_lon = clusters[i % len(clusters)]
        members = RNG.randint(2, 8)
        income = RNG.randrange(6500, 27001, 500)
        savings = RNG.randrange(0, 45001, 500)
        debts = RNG.randrange(0, 125001, 1000)
        raw_vulnerability = 3 + members * 0.45 + debts / 30000 - income / 10000 - savings / 30000
        vulnerability = max(1, min(10, round(raw_vulnerability + RNG.gauss(0, 1.2))))
        vulnerabilities[head] = vulnerability
        lat = round(base_lat + RNG.uniform(-0.0040, 0.0040), 6)
        lon = round(base_lon + RNG.uniform(-0.0040, 0.0040), 6)
        household_rows.append((head, ward, members, income, savings, debts, vulnerability, lat, lon))
    households = pd.DataFrame(
        household_rows,
        columns=[
            "household_head", "ward", "members", "monthly_income_inr", "savings_inr",
            "debts_inr", "vulnerability_score_1to10", "lat", "lon",
        ],
    )
    write_csv(households, folder / "households.csv")

    caseworkers = ["Meera Kulkarni", "Farhan Khan", "Chaitali Bhosale", "Omkar Shinde"]
    regular_notes = [
        "Bachat group meeting attended; next month ka target set.",
        "School fees paid on time, ghar ka budget stable hai.",
        "Tailoring orders improved; savings plan discuss kiya.",
        "Health camp referral diya; family will visit on Friday.",
        "Ration card update pending, documents collect karne hain.",
        "Debt payment on track; income thoda improve hua.",
        "Job interview scheduled; travel support chahiye.",
        "Vendor cart repair complete, kaam phir se shuru.",
        "Childcare issue discussed; neighbour support available.",
        "Monthly check-in done, koi urgent concern nahi.",
    ]
    slipped_notes = [
        "Income fell after work stopped; savings target miss hua.",
        "Unexpected medical kharcha; debt phir badh gaya.",
        "Two loan payments missed; urgent follow-up chahiye.",
        "Work hours reduced, household budget slip ho raha hai.",
    ]
    visit_rows = []
    visit_dates = dates_between(date(2025, 8, 1), date(2026, 7, 31), 150)
    for i, when in enumerate(visit_dates):
        head_index = i % len(heads)
        head = heads[head_index]
        if vulnerabilities[head] >= 7 and RNG.random() < 0.45:
            note = RNG.choice(slipped_notes)
        else:
            note = RNG.choice(regular_notes)
        if i % 13 == 0:
            note += f" Call family on {phone(51000 + head_index)}."
        visit_rows.append((head, when, caseworkers[head_index % len(caseworkers)], note))
    visit_rows.sort(key=lambda row: (row[1], row[0]))
    visits = pd.DataFrame(visit_rows, columns=["household_head", "date", "caseworker", "note"])
    visits["date"] = visits["date"].map(dmy)
    write_csv(visits, folder / "visits.csv")

    milestone_names = [
        "Emergency savings started", "Stable livelihood for three months",
        "High-cost debt reduced", "Social protection enrolled",
    ]
    milestone_rows = []
    for i, head in enumerate(heads):
        count = 2 + (i % 2)
        for j in range(count):
            milestone = milestone_names[(i + j) % len(milestone_names)]
            achieved = ""
            if RNG.random() > vulnerabilities[head] / 13:
                achieved = dmy(date(2025, 9, 1) + timedelta(days=RNG.randint(0, 300)))
            milestone_rows.append((head, milestone, achieved))
    milestones = pd.DataFrame(milestone_rows, columns=["household_head", "milestone", "achieved_date"])
    write_csv(milestones, folder / "milestones.csv")
    return {"households.csv": len(households), "visits.csv": len(visits), "milestones.csv": len(milestones)}


def applicant_rows(names: list[str], start_index: int, year: int) -> pd.DataFrame:
    cities = ["Pune", "Nagpur", "Nashik", "Aurangabad", "Kolhapur", "Solapur", "Mumbai", "Satara"]
    courses = ["BSc Nursing", "BCom", "BA Economics", "BTech", "Diploma in Pharmacy", "BCA", "LLB", "BEd"]
    rows = []
    for offset, name in enumerate(names):
        idx = start_index + offset
        rows.append(
            (
                name,
                cities[idx % len(cities)],
                courses[(idx * 3 + year) % len(courses)],
                RNG.randrange(72000, 480001, 1000),
                round(RNG.uniform(58.0, 96.5), 1),
                phone(10000 + idx),
                f"{slug(name)}{idx + 1}@example.org",
            )
        )
    return pd.DataFrame(
        rows,
        columns=["applicant_name", "city", "course", "family_income_inr", "marks_pct", "phone", "email"],
    )


def generate_lila() -> dict[str, int]:
    folder = ROOT / "lila-scholarships"
    folder.mkdir(exist_ok=True)

    names_2025 = NAME_POOL[400:600]
    applicants_2025 = applicant_rows(names_2025, 0, 2025)

    duplicate_indices = sorted(RNG.sample(range(200), 30))
    duplicate_rows = applicants_2025.iloc[duplicate_indices].copy()
    case_styles = [str.upper, str.lower, lambda value: value.swapcase()]
    duplicate_rows["applicant_name"] = [
        case_styles[i % len(case_styles)](name)
        for i, name in enumerate(duplicate_rows["applicant_name"])
    ]
    # Small legitimate year-to-year changes make the records useful for matching demos.
    duplicate_rows["marks_pct"] = (duplicate_rows["marks_pct"] + np.linspace(0.1, 1.5, 30)).round(1)

    new_names_2026 = NAME_POOL[600:790]
    new_rows_2026 = applicant_rows(new_names_2026, 200, 2026)
    applicants_2026 = pd.concat([duplicate_rows, new_rows_2026], ignore_index=True)
    applicants_2026 = applicants_2026.sample(frac=1, random_state=SEED).reset_index(drop=True)

    applicants_2025.to_excel(folder / "applicants_2025.xlsx", index=False, engine="openpyxl")
    applicants_2026.to_excel(folder / "applicants_2026.xlsx", index=False, engine="openpyxl")

    all_current_names = applicants_2026["applicant_name"].tolist()
    funded_names = RNG.sample(all_current_names, 145)
    disbursement_rows = []
    for i, name in enumerate(funded_names):
        installments = 2 if i < 78 else 1
        award = RNG.choice([18000, 24000, 30000, 36000, 48000, 60000])
        for installment in range(1, installments + 1):
            when = date(2026, 7, 15) + timedelta(days=RNG.randint(0, 180))
            amount = award // (2 if installments == 2 else 1)
            disbursement_rows.append((name, amount, when, installment))
    disbursement_rows.sort(key=lambda row: (row[2], row[0], row[3]))
    disbursements = pd.DataFrame(
        disbursement_rows,
        columns=["applicant_name", "amount_inr", "date", "installment"],
    )
    disbursements["date"] = disbursements["date"].map(dmy)
    write_csv(disbursements, folder / "disbursements.csv")

    normalized_2025 = set(applicants_2025["applicant_name"].str.casefold())
    overlap = applicants_2026["applicant_name"].str.casefold().isin(normalized_2025).sum()
    assert overlap == 30, f"Expected 30 cross-year duplicates, found {overlap}"
    return {
        "applicants_2025.xlsx": len(applicants_2025),
        "applicants_2026.xlsx": len(applicants_2026),
        "disbursements.csv": len(disbursements),
    }


def write_dialogs() -> None:
    dialogs = {
        "y-ultimate": [
            "Can you make me a simple dashboard showing attendance, fitness results and donations?",
            "Now show which participants, coaches and sites may need extra support to improve attendance, fitness or confidence.",
            "Please add a Pune map of our sites, sized or shaded by average attendance, with a quick way to compare them.",
        ],
        "foundation-without": [
            "Please make me a dashboard of household progress, visits, money pressures and milestones.",
            "Rank households by vulnerability and clearly show who seems to have slipped since recent visits or missed milestones.",
            "Add a map of households colored by vulnerability, with household details and recent visit notes when I select one.",
        ],
        "lila-scholarships": [
            "Can you make me a dashboard for this year's scholarship applicants and payments?",
            "Please flag likely duplicate applicants across 2025 and 2026, even when their name uses different capital letters.",
            "Add a clear disbursement-status view showing who is fully paid, partly paid or not yet paid, plus totals by installment.",
        ],
    }
    assert all(len(turn) < 220 for turns in dialogs.values() for turn in turns)
    (ROOT / "dialogs.json").write_text(json.dumps(dialogs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify(expected: dict[str, dict[str, int]]) -> pd.DataFrame:
    summaries = []
    for folder_name, files in expected.items():
        folder = ROOT / folder_name
        actual_files = sorted(path for path in folder.iterdir() if path.is_file())
        assert len(actual_files) < 20, f"{folder_name} has too many files"
        total_bytes = sum(path.stat().st_size for path in actual_files)
        assert total_bytes < 5 * 1024 * 1024, f"{folder_name} exceeds 5 MB"
        assert {path.name for path in actual_files} == set(files)
        for filename, expected_rows in files.items():
            path = folder / filename
            frame = pd.read_excel(path, engine="openpyxl") if path.suffix == ".xlsx" else pd.read_csv(path)
            assert len(frame) == expected_rows, f"{path}: expected {expected_rows}, got {len(frame)}"
            summaries.append(
                {
                    "folder": folder_name,
                    "file": filename,
                    "rows": len(frame),
                    "size_kb": round(path.stat().st_size / 1024, 1),
                }
            )
    dialogs = json.loads((ROOT / "dialogs.json").read_text(encoding="utf-8"))
    assert set(dialogs) == set(expected)
    assert all(len(turns) == 3 for turns in dialogs.values())
    return pd.DataFrame(summaries)


def main() -> None:
    expected = {
        "y-ultimate": generate_y_ultimate(),
        "foundation-without": generate_foundation_without(),
        "lila-scholarships": generate_lila(),
    }
    write_dialogs()
    summary = verify(expected)
    print(f"Synthetic NGO datasets generated and verified (seed={SEED}).")
    print(summary.to_string(index=False))
    print("\nFolder totals:")
    for folder_name in expected:
        paths = list((ROOT / folder_name).iterdir())
        size_kb = sum(path.stat().st_size for path in paths if path.is_file()) / 1024
        print(f"  {folder_name}: {len(paths)} files, {size_kb:.1f} KB")
    print(f"  dialogs.json: {(ROOT / 'dialogs.json').stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
