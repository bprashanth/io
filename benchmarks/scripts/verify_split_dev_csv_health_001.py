#!/usr/bin/env python3
"""Verify the split-pipeline ANC4 development case against its oracle."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def metric(row: dict[str, object]) -> float:
    name = next(name for name in row if "coverage" in name and name not in ("source",))
    return round(float(row[name]), 1)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("run_dir", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args(); oracle = json.loads(Path("benchmarks/cases/dev-csv-health-001/oracle.json").read_text())
    checks: list[dict[str, object]] = []; failures: list[str] = []; shortfalls: list[str] = []
    reports = {turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text()) for turn in range(1, 6)}

    expected = {(district, int(year)): float(value) for district, years in oracle["expected_percentages"].items() for year, value in years.items()}
    for turn, expected_rows in ((1, 20), (2, 15), (3, 6), (4, 6), (5, 6)):
        rows = reports[turn]["rows"]; values = {(str(row["district"]), int(row["year"])): metric(row) for row in rows}
        relevant = {key: value for key, value in expected.items() if key in values}
        formula_passed = all(metric(row) == round(float(row["anc4_completed"]) / float(row["pregnancies_registered"]) * 100, 1) for row in rows)
        passed = len(rows) == expected_rows and formula_passed and all(values.get(key) == value for key, value in relevant.items())
        checks.append({"name": f"turn-{turn}-rows-and-values", "passed": passed})
        if not passed: failures.append(f"turn {turn} rows/values differ from oracle")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        checks.append({"name": f"turn-{turn}-browser", "passed": browser["passed"]})
        if not browser["passed"]: failures.append(f"turn {turn} browser check failed")

    changes = {(item["label"], float(item["value"])) for item in reports[3]["insights"] if item["kind"] == "change"}
    change_passed = changes == {("Gaya", 8.0), ("Nalanda", 7.0)}
    checks.append({"name": "turn-3-percentage-point-changes", "passed": change_passed})
    if not change_passed: failures.append("turn 3 change insights are wrong or missing")
    gap = [item for item in reports[3]["insights"] if item["kind"] == "difference" and int(item.get("time", -1)) == 2023]
    gap_passed = bool(gap and float(gap[0]["value"]) == 6.0)
    checks.append({"name": "turn-3-2023-gap-explicit", "passed": gap_passed, "critical": False})
    if not gap_passed: shortfalls.append("The page shows both 2023 values but does not explicitly state Nalanda minus Gaya = 6 pp.")

    for turn in (4, 5):
        caveat = any(item["kind"] == "causal_limit" for item in reports[turn]["insights"])
        checks.append({"name": f"turn-{turn}-causal-limit", "passed": caveat})
        if not caveat: failures.append(f"turn {turn} lost the causal limitation")

    download = args.run_dir / "turn-5/browser/downloads/filtered-dashboard.csv"
    with download.open(newline="") as handle: rows = list(csv.DictReader(handle))
    download_passed = len(rows) == 6 and {row["district"] for row in rows} == {"Gaya", "Nalanda"} and {row["year"] for row in rows} == {"2021", "2022", "2023"} and all(row["source"] == "synthetic Bihar ANC fixture" for row in rows)
    checks.append({"name": "turn-5-download", "passed": download_passed})
    if not download_passed: failures.append("turn 5 download is not the traceable six-row comparison")

    result = {"case_id": "dev-csv-health-001", "checks": checks, "critical_failures": failures, "noncritical_shortfalls": shortfalls, "passed_critical": not failures, "fully_satisfied_oracle": not failures and not shortfalls}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2) + "\n"); print(json.dumps(result)); return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())
