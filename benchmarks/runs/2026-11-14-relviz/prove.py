#!/usr/bin/env python3
"""Read the XLSX fixtures, validate joins/patterns, and render all seven skill templates."""
import copy
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import openpyxl
import pandas as pd
import vl_convert as vlc

HERE = Path(__file__).resolve().parent
COWORK = HERE.parent / "2026-11-06-oss-desktop-independent/cowork"
SKILL = COWORK / "idli/claude-skills/relationship-visuals"
OUT = HERE / "out"
SOURCES = [
    ("households.xlsx", "Households", "household_id"),
    ("groups.xlsx", "Groups", "group_id"),
    ("groups.xlsx", "Members", "member_id"),
    ("loans.xlsx", "Loans", "loan_id"),
    ("loans.xlsx", "Repayments", "repayment_id"),
    ("field_visits.xlsx", "Visits", "visit_id"),
    ("trainings.xlsx", "Trainings", "training_id"),
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_sources():
    frames, audit = {}, {}
    for filename, sheet, key in SOURCES:
        frame = pd.read_excel(HERE / "fixtures" / filename, sheet_name=sheet)
        require(frame[key].notna().all() and frame[key].is_unique, f"Invalid primary key: {sheet}.{key}")
        frames[sheet] = frame
        audit[sheet] = {"file": filename, "rows_read": len(frame), "columns": list(frame.columns),
                        "blank_cells": {c: int(frame[c].isna().sum()) for c in frame if frame[c].isna().any()}}
    return frames, audit


def join(left, right, keys, validate="many_to_one"):
    keys = [keys] if isinstance(keys, str) else keys
    require(left[keys].notna().all().all(), f"Blank join keys: {keys}")
    result = left.merge(right, on=keys, how="left", validate=validate, indicator=True)
    require(result["_merge"].eq("both").all(), f"Unmatched join keys: {keys}")
    require(len(result) == len(left), f"Unexpected row multiplication: {keys}")
    return result.drop(columns="_merge")


def money(series):
    text = series.astype("string").str.replace("₹", "", regex=False).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="raise")


def rates(frame, keys):
    # Exclude unknown paid amounts from both numerator AND denominator.
    known = frame.dropna(subset=["paid_rs", "due_rs"])
    result = known.groupby(keys, as_index=False).agg(paid_rs=("paid_rs", "sum"), due_rs=("due_rs", "sum"),
                                                  installments=("loan_id", "size"))
    require(result["due_rs"].gt(0).all(), "Repayment denominator must be positive")
    result["repayment_rate"] = result["paid_rs"] / result["due_rs"]
    return result


def chart_family(spec):
    """Classify the composition itself, independently of its filename or claimed label."""
    if "facet" in spec:
        return "small-multiples"
    marks = [layer["mark"] for layer in spec.get("layer", [])] or [spec.get("mark")]
    kinds = {mark if isinstance(mark, str) else mark["type"] for mark in marks}
    if "rect" in kinds:
        return "matrix"
    if "rule" in kinds and "point" in kinds:
        return "ranked-dot"
    if kinds == {"point"} and spec["encoding"]["x"]["type"] == "temporal":
        return "event-strip"
    if kinds == {"line"} and spec["encoding"]["x"]["type"] == "ordinal":
        return "slope"
    if kinds == {"bar"} and spec["encoding"]["x"].get("stack") == "zero":
        return "layered-bars"
    if kinds == {"text"}:
        return "cohort-table"
    raise ValueError("Unrecognised chart composition")


def check_fields(node, columns):
    if isinstance(node, dict):
        require("url" not in node and "transform" not in node and "data" not in node,
                "Templates must use a local CSV and precomputed rows")
        if "field" in node:
            require(node["field"] in columns, f"Spec references absent CSV field: {node['field']}")
        for value in node.values():
            check_fields(value, columns)
    elif isinstance(node, list):
        for value in node:
            check_fields(value, columns)


def render(family, number, question, title, data, sources, finding):
    stem = f"{number:02}-{family}"
    spec = json.loads((SKILL / "templates" / f"{family}.vl.json").read_text())
    require(chart_family(spec) == family, "Claimed family differs from composition")
    check_fields(spec, set(data.columns))
    spec["title"] = title
    csv_path = OUT / f"{stem}.csv"
    data.to_csv(csv_path, index=False, float_format="%.6f")
    # Exactly the same string-valued record loading as lib/home.py:view().
    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(bool(rows), "Chart data must not be empty")
    preview = copy.deepcopy(spec)
    preview["data"] = {"values": rows}
    svg = vlc.vegalite_to_svg(json.dumps(preview))  # Fail loudly; no fallback renderer.
    root = ET.fromstring(svg)
    # A valid SVG with only axes is not evidence of a populated chart.
    mark_elements = sum(len(list(node)) for node in root.iter()
                        if "role-mark" in node.attrib.get("class", "").split())
    require(mark_elements > 0, f"Chart rendered no data marks: {stem}")
    (OUT / f"{stem}.svg").write_text(svg)
    (OUT / f"{stem}.vl.json").write_text(json.dumps(spec, indent=2) + "\n")
    return {"stem": stem, "question": question, "chart": family, "csv_rows": len(rows),
            "rendered_mark_elements": mark_elements, "sources": sources, "finding": finding}


def main():
    OUT.mkdir(exist_ok=True)
    f, audit = read_sources()
    h, g, m, loans, p, visits, t = (f[s] for _, s, _ in SOURCES)
    h["ward"] = h["ward"].str.strip().str.title()
    require(m["household_id"].is_unique and loans["household_id"].is_unique,
            "Fixture contract: one membership and loan per household")
    mh = join(m, h, "household_id", "one_to_one")
    membership = join(mh, g[["group_id", "group_name"]], "group_id")
    lg = join(loans, m[["household_id", "group_id"]], ["household_id", "group_id"], "one_to_one")
    lg = join(lg, g[["group_id", "group_name"]], "group_id")
    joined_payments = join(p, lg[["loan_id", "household_id", "group_id", "group_name"]], "loan_id")
    joined_visits = join(visits, h[["household_id", "assigned_officer"]], "household_id")
    require(joined_visits["officer"].eq(joined_visits["assigned_officer"]).all(), "Unexpected visit officer")
    t = join(t, g[["group_id", "group_name"]], "group_id")
    counts = m.groupby("group_id", as_index=False).agg(eligible_members=("household_id", "nunique"))
    t = join(t, counts, "group_id")
    t["status"] = t["status"].str.strip().str.lower()
    require(t["status"].isin(["held", "missed"]).all(), "Unknown training status")
    require(t.loc[t["status"].eq("missed"), "attended_members"].eq(0).all(), "Missed training must be zero")
    require(t["attended_members"].dropna().ge(0).all() and
            (t["attended_members"].dropna() <= t.loc[t["attended_members"].notna(), "eligible_members"]).all(),
            "Attendance exceeds eligible members")
    p = joined_payments
    p["paid_rs"], p["due_rs"] = money(p["paid_rs"]), money(p["due_rs"])
    require(p["due_rs"].gt(0).all() and p["paid_rs"].dropna().ge(0).all(), "Invalid repayment inputs")
    p["due_on"] = pd.to_datetime(p["due_on"], format="mixed", errors="raise")
    visits["visited_on"] = pd.to_datetime(visits["visited_on"], errors="raise")
    t["scheduled_on"] = pd.to_datetime(t["scheduled_on"], errors="raise")
    p["month"] = p["due_on"].dt.strftime("%Y-%m-01")
    require(p["due_on"].dt.to_period("M").nunique() == 18, "Need 18 months of repayment observations")
    missing_paid = int(p["paid_rs"].isna().sum())
    require(missing_paid == 2, "Fixture should have two deliberately unknown repayment amounts")
    require(int(t["attended_members"].isna().sum()) == 1, "Fixture should have one unknown attendance count")
    monthly = rates(p, ["group_name", "month"]).rename(columns={"group_name": "group"})
    charts = []

    # Q1: complete the grid so absence of a connection is explicitly shown as zero.
    matrix = h.groupby(["ward", "assigned_officer"]).size().reindex(
        pd.MultiIndex.from_product([sorted(h["ward"].unique()), sorted(h["assigned_officer"].unique())],
                                   names=["ward", "assigned_officer"]), fill_value=0).reset_index(name="households")
    matrix = matrix.rename(columns={"assigned_officer": "officer"})
    ward_counts = h.groupby("ward").size()
    require(ward_counts["Ward 04"] == 24 and len(h) == 48, "Ward cluster disappeared")
    charts.append(render("matrix", 1, "Where are household/officer connections concentrated?",
                         "Ward 04 contains half the assigned households", matrix,
                         ["Households: household_id, ward, assigned_officer"], "Ward 04 has 24 of 48 households."))

    # Q2: aggregate visits before joining; count each visited household once.
    workload = h.groupby("assigned_officer", as_index=False).agg(households=("household_id", "nunique"))
    june = visits[visits["visited_on"].dt.to_period("M").eq(pd.Period("2026-06"))]
    visited = june.groupby("officer", as_index=False).agg(visited=("household_id", "nunique"))
    workload = workload.rename(columns={"assigned_officer": "officer"}).merge(visited, on="officer", how="left", validate="one_to_one")
    workload["visited"] = workload["visited"].fillna(0).astype(int)
    workload["unvisited"] = workload["households"] - workload["visited"]
    workload["capacity"] = 16  # Illustrative planning reference; documented in workbook Notes.
    workload = workload.sort_values("households", ascending=False)
    require(sorted(workload["households"]) == [9, 9, 30], "Officer overload disappeared")
    require(workload.iloc[0]["unvisited"] == 20, "Expected 20 unvisited assigned households for Kiran in June")
    charts.append(render("ranked-dot", 2, "Who has the largest caseload and how many households went unvisited in June?",
                         {"text": "Kiran has 30 assigned households; 20 unvisited in June",
                          "subtitle": "Ticks mark an illustrative capacity of 16 households"}, workload,
                         ["Households: household_id, assigned_officer", "Visits: household_id, officer, visited_on"],
                         "Caseloads are 30, 9, 9; the 16-household reference is illustrative, not an NGO policy."))

    payment_sources = ["Repayments: loan_id, due_on, due_rs, paid_rs", "Loans: loan_id, household_id, group_id",
                       "Members: household_id, group_id", "Groups: group_id, group_name"]
    charts.append(render("small-multiples", 3, "Which group's monthly repayment diverges from the others?",
                         "Sakhi repayment falls after October 2025", monthly[["group", "month", "repayment_rate"]],
                         payment_sources, f"18 months per group; exclude {missing_paid} unknown paid amounts from both sums."))

    # Q4: one entity, two fact sheets; concatenate already aggregated events, never cross-join them.
    sakhi = monthly[monthly["group"].eq("Sakhi")].copy()
    sakhi["date"], sakhi["lane"] = sakhi["month"].str[:7] + "-28", "Repayment due"
    sakhi["outcome"] = sakhi["repayment_rate"].map(lambda x: "Repayment at least 80%" if x >= .8 else "Repayment below 80%")
    sakhi["details"] = sakhi["repayment_rate"].map(lambda x: f"{x:.1%} of known amount due repaid")
    training = t[t["group_id"].eq("G03")].copy()
    training["date"], training["lane"] = training["scheduled_on"].dt.strftime("%Y-%m-%d"), "Group training"
    training["outcome"] = training["status"].map({"held": "Training held", "missed": "Training missed"})
    training["details"] = training["topic"]
    missed = training.loc[training["status"].eq("missed"), "date"].tolist()
    require(missed == ["2025-10-15"], "Expected one missed Sakhi training")
    cols = ["date", "lane", "outcome", "details"]
    events = pd.concat([sakhi[cols], training[cols]], ignore_index=True).sort_values("date")
    charts.append(render("event-strip", 4, "How does Sakhi's missed training line up with its repayment change?",
                         "Missed October training precedes November repayment drop", events,
                         payment_sources + ["Trainings: group_id, scheduled_on, topic, status"],
                         "Sakhi missed 15 October 2025; repayment below 80% starts in November. Sequence does not prove causation."))

    # Q5: equal three-month windows, excluding October (event month).
    windows = p[p["month"].between("2025-07-01", "2025-09-01") |
                p["month"].between("2025-11-01", "2026-01-01")].copy()
    windows["period"] = windows["month"].map(lambda x: "Before" if x < "2025-10-01" else "After")
    slope = rates(windows, ["group_name", "period"]).rename(columns={"group_name": "group"})
    comparison = slope.pivot(index="group", columns="period", values="repayment_rate")
    drop = float(comparison.loc["Sakhi", "Before"] - comparison.loc["Sakhi", "After"])
    require(drop > .4, "Sakhi repayment drop should exceed 40 percentage points")
    other = comparison.drop(index="Sakhi")
    require((other["Before"] - other["After"]).abs().max() < .02, "Comparison groups should remain stable")
    charts.append(render("slope", 5, "Which groups changed between July–September and November–January?",
                         {"text": "Sakhi changes most across equal three-month windows",
                          "subtitle": "Before: Jul–Sep 2025; after: Nov 2025–Jan 2026"}, slope[["group", "period", "repayment_rate"]],
                         payment_sources + ["Trainings: group_id, scheduled_on, status (defines event month)"],
                         f"Before: Jul–Sep 2025; after: Nov 2025–Jan 2026. Sakhi falls {drop*100:.1f} percentage points."))

    links = membership.groupby(["group_name", "ward"], as_index=False).agg(households=("household_id", "nunique"))
    links = links.rename(columns={"group_name": "group"})
    require(links["households"].sum() == len(h), "Membership chart double-counts households")
    charts.append(render("layered-bars", 6, "How do member households connect self-help groups to wards?",
                         "Three groups are entirely connected to Ward 04", links,
                         ["Members: household_id, group_id", "Households: household_id, ward", "Groups: group_id, group_name"],
                         "Pragati, Ujjwal and Sakhi each connect eight member households to Ward 04; each household counted once."))

    # Q7: first scheduled training, including missed sessions, defines entry cohort.
    t["quarter"] = t["scheduled_on"].dt.to_period("Q")
    first = t.groupby("group_id")["quarter"].min()
    t["entry"] = t["group_id"].map(first)
    t["elapsed_quarter"] = [q.ordinal - e.ordinal for q, e in zip(t["quarter"], t["entry"])]
    t["cohort"] = t["entry"].astype(str)
    totals = t.groupby(["cohort", "elapsed_quarter"], as_index=False).agg(planned_sessions=("training_id", "size"))
    known = t.dropna(subset=["attended_members"]).groupby(["cohort", "elapsed_quarter"], as_index=False).agg(
        attendance=("attended_members", "sum"), eligible=("eligible_members", "sum"), observed_sessions=("training_id", "size"))
    cohorts = totals.merge(known, on=["cohort", "elapsed_quarter"], how="left", validate="one_to_one")
    cohorts["attendance_label"] = ["Unknown" if pd.isna(a) else f"{a/e:.0%}" for a, e in zip(cohorts["attendance"], cohorts["eligible"])]
    cohorts["observed_sessions"] = cohorts["observed_sessions"].fillna(0).astype(int)
    charts.append(render("cohort-table", 7, "Do first-training cohorts sustain attendance at comparable stages?",
                         "Attendance by cohort and quarters since first training", cohorts[["cohort", "elapsed_quarter", "attendance_label", "observed_sessions", "planned_sessions"]],
                         ["Trainings: training_id, group_id, scheduled_on, attended_members", "Members: household_id, group_id"],
                         "Known attendance / eligible member-session slots. One unknown attendance count excluded from both sums; missed session stays zero. Future periods blank."))

    families = [c["chart"] for c in charts]
    require(len(set(families)) == 7 and all(a != b for a, b in zip(families, families[1:])), "Chart types must vary")
    report = {"status": "passed", "versions": {"python": sys.version.split()[0], "pandas": pd.__version__,
               "openpyxl": openpyxl.__version__, "vl_convert": vlc.__version__}, "sources": audit,
              "checks": {"unique_primary_keys": True, "all_foreign_keys_match": True, "no_fact_row_multiplication": True,
                         "blank_paid_amounts_excluded": missing_paid, "unknown_attendance_counts_excluded": 1,
                         "ward_04_households": 24, "officer_caseloads": [30, 9, 9], "sakhi_drop_percentage_points": round(drop * 100, 2),
                         "distinct_chart_families": len(set(families)), "all_svg_have_data_marks": True}, "charts": charts}
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: five workbooks, validated joins and planted patterns, {len(charts)} SVGs, seven distinct chart families")


if __name__ == "__main__":
    main()
