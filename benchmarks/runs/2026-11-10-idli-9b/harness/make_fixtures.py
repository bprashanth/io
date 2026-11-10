"""Build the benchmark's fake Drive: spreadsheets in fixtures/drive, fixtures/drive.json, and the Drive index
(fixtures/drive-index.duckdb) in the same schema lib/driveindex.py writes.

Sources (all fake or public): the taught skills' mock.xlsx files (fake values made by Idli's own mock maker),
totalrecall's synthetic Valparai livelihoods tables, and two public Valparai ecology datasets (road kills on
roads, tree plots in rainforest fragments), cut down to the columns an NGO sheet would have. A few mistakes
are put in on purpose so the checks have something to find. The summaries are written here, not by a model,
so finding a file doesn't depend on the model under test.

  python harness/make_fixtures.py
"""
import hashlib
import json
import os
import shutil

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
FX = os.path.join(BENCH, "fixtures")
DRIVE = os.path.join(FX, "drive")
TR = os.path.expanduser("~/src/" + "github.com/bprashanth/totalrecall/")
LIV = TR + "dss/sites/valparai_livelihoods/raw/"
ECO = TR + "dss/sites/valparai/raw/"


def fid(name):
    return "1" + hashlib.sha1(name.encode()).hexdigest()[:32]


def peek_of(df):
    head = df.head(4).astype(str)
    return " | ".join(map(str, df.columns)) + "\n" + "\n".join(" | ".join(map(str, r)) for r in head.values.tolist())


def main():
    os.makedirs(DRIVE, exist_ok=True)
    rnd = np.random.default_rng(7)
    sheets = []  # (name, folder, modified, summary, {tab: df})

    sk = os.path.join(FX, "skills")
    for skill, name, folder, mod, summ in [
        ("households", "Household survey 2025.xlsx", "Livelihoods", "2025-10-02",
         "Household survey: head of household, ward, members, monthly income, savings, debts, vulnerability score."),
        ("households", "Household survey 2024 (old).xlsx", "Livelihoods/Archive", "2024-09-14",
         "Last year's household survey: wards, income, savings, debts per household."),
        ("field_programme_tracker", "Field programme tracker Q3.xlsx", "Programmes/Monitoring", "2025-10-20",
         "Field visits by officers to villages: status, households visited, amount disbursed; officer and village lists."),
        ("tech_reimbursement_form", "Tech reimbursement form (Responses).xlsx", "Finance", "2025-10-28",
         "Form responses: staff claims for phones, laptops and internet, amounts, status, approver."),
        ("volunteer_register", "Volunteer register 2025.xlsx", "Volunteers", "2025-09-30",
         "Volunteers: name, city, skills, hours given, joined date, status."),
    ]:
        tabs = pd.read_excel(os.path.join(sk, skill, "mock.xlsx"), sheet_name=None)
        tabs = {k: v for k, v in tabs.items() if not k.startswith("_idli")}
        sheets.append((name, folder, mod, summ, tabs))

    # livelihoods: MGNREGA works (taught below), migration and estates (not taught)
    w = pd.read_csv(LIV + "syn-mgnrega/works.csv")
    works = pd.DataFrame({"Work ID": w.work_id, "Date": w.eventDate, "Work type": w.work_label, "Village": w.village,
                          "Persondays": w.persondays, "Households engaged": w.households_engaged})
    works.loc[5, "Persondays"] = -40           # a typo the checks should catch
    works.loc[17, "Village"] = "thonimalai village"  # case slip
    sheets.append(("MGNREGA works Valparai 2019-2023.xlsx", "Livelihoods/Public works", "2025-08-11",
                   "MGNREGA (job work) works per village: work type, persondays, households engaged, 2019-2023.",
                   {"Works": works}))
    m = pd.read_csv(LIV + "syn-migration/migration_events.csv")
    mig = pd.DataFrame({"Record": m.record_id, "Date": m.eventDate, "Occupation": m.occupation_label,
                        "Village": m.origin_village, "People who left": m.persons_moved, "Went to": m.destination})
    sheets.append(("Out-migration records.xlsx", "Livelihoods", "2025-07-02",
                   "People leaving villages for work: occupation, village, how many, destination.", {"Sheet1": mig}))
    e = pd.read_csv(LIV + "syn-estate-labour/estate_headcount.csv")
    est = pd.DataFrame({"Year": pd.to_datetime(e.eventDate).dt.year, "Estate": e.estate_name, "Workers": e.worker_count,
                        "Women workers": e.women_workers, "Workers per ha": e.workers_per_ha})
    sheets.append(("Estate labour census.xlsx", "Livelihoods/Estates", "2025-03-19",
                   "Tea estate labour census by year: workers, women workers, workers per hectare.", {"Census": est}))
    wg = pd.read_csv(LIV + "syn-wages/wage_monthly.csv")
    sheets.append(("Wage register monthly.xlsx", "Finance/Payroll", "2025-01-08",
                   "Monthly tea estate wages: daily wage, overtime rate, paid days, 2017-2024.",
                   {"Wages": wg.rename(columns={"year": "Year", "month": "Month", "daily_wage": "Daily wage (Rs)",
                                                "overtime_rate": "Overtime rate (Rs)",
                                                "paid_days_per_month": "Paid days"})}))

    # transport / roads: road kills on Valparai roads (public data), by transect and season
    r = pd.read_csv(ECO + "zenodo-7060430/road_events.csv", encoding="latin-1", low_memory=False)
    r = r[r.season.isin(["monsoon", "summer"])].copy()
    road = pd.DataFrame({"S.No": r.sno, "Season": r.season.str.title(), "Road stretch": r.transect,
                         "Stretch length (km)": r.tlength, "Date": r.eventDate, "Animal": r.vernacularName,
                         "Animal group": r.taxonRemarks.str.title(), "Count": r.individualCount})
    road = road.sample(900, random_state=5).sort_values("S.No").reset_index(drop=True)
    road.loc[12, "Count"] = None
    road.loc[40, "Road stretch"] = "Nallamudi "
    sheets.append(("Road kill survey 2011-12.xlsx", "Ecology/Roads", "2024-11-30",
                   "Animals found killed on roads: road stretch, season, date, animal, group, count.", {"Roadkill": road}))

    # ecology: trees in rainforest fragments, native vs alien
    t = pd.read_csv(ECO + "zenodo-10077040/trees.csv", encoding="latin-1", low_memory=False)
    trees = pd.DataFrame({"Year": t.Year, "Fragment": t.Fragment, "Plot": t.Point_name, "Tree no": t.Tree_no,
                          "Species": t.scientificName, "Native or alien": t.nativeAlien, "Girth (cm)": t.Girth_eff,
                          "Height (m)": t.TreeHeight})
    trees = trees.sample(1200, random_state=3).sort_values(["Year", "Fragment", "Plot"]).reset_index(drop=True)
    trees.loc[30, "Girth (cm)"] = 9999
    trees.loc[77, "Native or alien"] = "alien "
    sheets.append(("Fragment tree plots 2000-2019.xlsx", "Ecology/Restoration", "2025-06-21",
                   "Trees in rainforest fragment plots: year, fragment, plot, species, native or alien, girth, height.",
                   {"Trees": trees}))

    # a small budget sheet nobody taught
    bud = pd.DataFrame({"Line item": ["Field staff", "Travel", "Seedlings", "Training", "Admin", "Monitoring"],
                        "Budget 2025-26 (Rs)": [1800000, 420000, 350000, 260000, 300000, 180000],
                        "Spent to Sep (Rs)": [910000, 260000, 340000, 90000, 160000, 30000]})
    sheets.append(("Budget 2025-26.xlsx", "Finance", "2025-10-01", "Programme budget by line item: budget and spent to date.",
                   {"Budget": bud}))

    files = []
    for name, folder, mod, summ, tabs in sheets:
        path = name
        with pd.ExcelWriter(os.path.join(DRIVE, path)) as xw:
            for tab, df in tabs.items():
                df.to_excel(xw, sheet_name=tab[:31], index=False)
        first = next(iter(tabs.values()))
        files.append({"id": fid(name), "name": name, "kind": "Microsoft Excel", "folder": folder, "path": path,
                      "modified": mod, "summary": summ, "peek": peek_of(first)})
    for name, kind, folder, mod, summ in [
        ("Tree plots - field notes.docx", "Microsoft Word", "Ecology/Restoration", "2025-06-22",
         "Field notes from the 2019 tree plot resurvey: who went, weather, plots skipped."),
        ("Annual report 2024.pdf", "PDF", "Reports", "2025-04-02", "Annual report 2024: programmes, reach, finances."),
        ("Donor proposal - water bodies.docx", "Microsoft Word", "Fundraising", "2025-09-12",
         "Proposal to restore village water bodies using MGNREGA works."),
        ("Kolkata volunteer meetup group photo.jpg", "JPEG image", "Volunteers/Photos", "2024-12-14", "Group photo."),
        ("Road kill survey - methods.pdf", "PDF", "Ecology/Roads", "2024-11-02", "How the road kill survey was done."),
        ("Household survey questionnaire.docx", "Microsoft Word", "Livelihoods", "2025-05-02",
         "The questions asked in the household survey."),
    ]:
        files.append({"id": fid(name), "name": name, "kind": kind, "folder": folder, "path": None, "modified": mod,
                      "summary": summ, "peek": ""})

    with open(os.path.join(FX, "drive.json"), "w") as f:
        json.dump({"files": files}, f, indent=1)
    db = os.path.join(FX, "drive-index.duckdb")
    if os.path.exists(db):
        os.remove(db)
    con = duckdb.connect(db)
    con.execute("""CREATE TABLE files (id VARCHAR PRIMARY KEY, name VARCHAR, kind VARCHAR, path VARCHAR, where_ VARCHAR,
                   peek VARCHAR, summary VARCHAR, indexed_at TIMESTAMP, modified DATE)""")
    for x in files:
        con.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?, now(), ?)",
                    [x["id"], x["name"], x["kind"], " / ".join(["My Drive"] + x["folder"].split("/")), "my_drive", x["peek"], x["summary"],
                     x["modified"]])
    con.close()
    print(len(files), "files;", sum(1 for x in files if x["path"]), "spreadsheets")


if __name__ == "__main__":
    main()
