#!/usr/bin/env python3
"""Deterministically verify one three-turn split-pipeline smoke run."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def derived_percent_name(plan: dict[str, object]) -> str:
    steps = plan.get("steps", [])
    matches = [
        step["name"]
        for step in steps
        if isinstance(step, dict)
        and step.get("op") == "derive"
        and step.get("kind") == "percent"
        and step.get("numerator") == "children_fully_immunised"
        and step.get("denominator") == "children_due"
    ]
    if len(matches) != 1:
        raise AssertionError("plan does not contain exactly one expected derived percentage")
    return str(matches[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    oracle = json.loads(Path("benchmarks/cases/smoke-001/oracle.json").read_text())
    failures: list[str] = []
    checks: list[dict[str, object]] = []

    reports = {turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text()) for turn in (1, 2, 3)}
    for turn, expected_years in ((1, {2022, 2023}), (2, {2023}), (3, {2023})):
        plan = json.loads((args.run_dir / f"turn-{turn}/validated-plan.json").read_text())
        percentage_name = derived_percent_name(plan)
        rows = reports[turn]["rows"]
        years = {int(row["year"]) for row in rows}
        values = {
            (int(row["year"]), str(row["district"])): round(float(row[percentage_name]), 1)
            for row in rows
        }
        expected = {(int(year), district): float(value) for year, districts in oracle["expected_percentages"].items() if int(year) in expected_years for district, value in districts.items()}
        passed = years == expected_years and values == expected
        checks.append({"name": f"turn-{turn}-rows-and-values", "passed": passed})
        if not passed: failures.append(f"turn {turn} rows/values differ from oracle")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        checks.append({"name": f"turn-{turn}-browser", "passed": browser["passed"]})
        if not browser["passed"]: failures.append(f"turn {turn} browser check failed")

    lowest = [item for item in reports[2]["insights"] if item["kind"] == "lowest"]
    lowest_passed = len(lowest) == 1 and lowest[0]["label"] == "Purnia" and float(lowest[0]["value"]) == 76.0
    checks.append({"name": "turn-2-lowest", "passed": lowest_passed})
    if not lowest_passed: failures.append("turn 2 lowest-district insight is wrong")

    download = args.run_dir / "turn-3/browser/downloads/filtered-dashboard.csv"
    with download.open(newline="") as handle: downloaded = list(csv.DictReader(handle))
    download_passed = (len(downloaded) == 3 and {row["district"] for row in downloaded} == {"Gaya", "Nalanda", "Purnia"} and {row["year"] for row in downloaded} == {"2023"} and all(row["source"] == "synthetic smoke fixture" for row in downloaded))
    checks.append({"name": "turn-3-download", "passed": download_passed})
    if not download_passed: failures.append("turn 3 download is not the traceable 2023 table")

    result = {"case_id": "smoke-001", "checks": checks, "failures": failures, "passed": not failures}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
