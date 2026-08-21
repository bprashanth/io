#!/usr/bin/env python3
"""Independently recompute expected page values from women_livelihood_outcomes.csv."""
import csv, json, sys

with open("women_livelihood_outcomes.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

districts = []
for r in rows:
    if r["district"] not in districts:
        districts.append(r["district"])

def f1(x):
    return f"{round(x, 1):.1f}"

def get(d, y):
    for r in rows:
        if r["district"] == d and r["year"] == y:
            return r
    raise KeyError((d, y))

def rate_row(d, y):
    r = get(d, y)
    enr = int(r["women_enrolled"]); comp = int(r["completed_training"]); emp = int(r["employed_at_6_months"])
    return {
        "enrolled": enr, "completed": comp, "employed": emp,
        "completionRate": comp / enr * 100,
        "employedOfEnrolled": emp / enr * 100,
        "employedOfCompleted": emp / comp * 100,
    }

def display_year(year):
    return {d: {
        "enrolled": f"{rate_row(d, year)['enrolled']:,}",
        "completed": f"{rate_row(d, year)['completed']:,}",
        "employed": f"{rate_row(d, year)['employed']:,}",
        "completionRate": f1(rate_row(d, year)["completionRate"]),
        "employedOfEnrolled": f1(rate_row(d, year)["employedOfEnrolled"]),
        "employedOfCompleted": f1(rate_row(d, year)["employedOfCompleted"]),
    } for d in districts}

def display_change(main_year, cmp_year):
    keys = ["completionRate", "employedOfEnrolled", "employedOfCompleted"]
    out = {}
    for d in districts:
        out[d] = {}
        for k in keys:
            diff = rate_row(d, main_year)[k] - rate_row(d, cmp_year)[k]
            v = round(diff, 1)
            sign = "+" if v > 0 else ("-" if v < 0 else "")
            word = "rose" if v > 0 else ("fell" if v < 0 else "no change")
            out[d][k] = f"{sign}{abs(v):.1f} pp ({word})"
    return out

expected = {
    "districts": districts,
    "year2023": display_year("2023"),
    "year2022": display_year("2022"),
    "change_2022_to_2023": display_change("2023", "2022"),
    "change_2023_to_2022": display_change("2022", "2023"),
}
print(json.dumps(expected, indent=2))
