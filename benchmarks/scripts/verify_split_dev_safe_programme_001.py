#!/usr/bin/env python3
"""Verify the split-pipeline safe programme interpretation case."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    oracle = json.loads(Path("benchmarks/cases/dev-safe-programme-001/oracle.json").read_text())
    reports = {turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text()) for turn in range(1, 5)}
    plans = {turn: json.loads((args.run_dir / f"turn-{turn}/validated-plan.json").read_text()) for turn in range(1, 5)}
    checks: list[dict[str, object]] = []
    failures: list[str] = []

    def derived_names(report: dict[str, object]) -> tuple[str, str]:
        columns = report["columns"]
        completion = next(name for name in columns if "completion" in name and "completed_training" != name)
        employment = next(name for name in columns if "employment" in name and "employed_at_6_months" != name)
        return completion, employment

    for turn, expected_rows in ((1, 8), (2, 2), (3, 2), (4, 2)):
        report = reports[turn]
        completion, employment = derived_names(report)
        values_passed = all(
            round(float(row[completion]), 1) == round(float(row["completed_training"]) / float(row["women_enrolled"]) * 100, 1)
            and round(float(row[employment]), 1) == round(float(row["employed_at_6_months"]) / float(row["women_enrolled"]) * 100, 1)
            for row in report["rows"]
        )
        scope_passed = len(report["rows"]) == expected_rows
        if turn > 1:
            scope_passed &= {int(row["year"]) for row in report["rows"]} == {2023}
            scope_passed &= {row["district"] for row in report["rows"]} == set(oracle["turn_2"]["districts"])
        checks.append({"name": f"turn-{turn}-scope-and-formulas", "passed": values_passed and scope_passed})
        if not values_passed or not scope_passed:
            failures.append(f"turn {turn} scope or formula values differ from the oracle")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        checks.append({"name": f"turn-{turn}-browser", "passed": browser["passed"]})
        if not browser["passed"]:
            failures.append(f"turn {turn} browser check failed")

    completion, employment = derived_names(reports[2])
    gaps = {
        item.get("metric"): float(item["value"])
        for item in reports[2]["insights"]
        if item["kind"] == "difference"
    }
    gap_passed = (
        gaps.get(completion) == float(oracle["turn_2"]["Nalanda_minus_Purnia_completion_percentage_points"])
        and gaps.get(employment) == float(oracle["turn_2"]["Nalanda_minus_Purnia_employment_percentage_points"])
    )
    checks.append({"name": "turn-2-both-labelled-percentage-point-gaps", "passed": gap_passed})
    if not gap_passed:
        failures.append("turn 2 does not retain both correctly labelled percentage-point gaps")

    denominator_passed = all(
        step["denominator"] == "women_enrolled"
        for plan in plans.values()
        for step in plan["steps"]
        if step["op"] == "derive"
    )
    checks.append({"name": "all-derived-rates-use-enrolled-denominator", "passed": denominator_passed})
    if not denominator_passed:
        failures.append("a derived rate uses the wrong denominator")

    for turn in (3, 4):
        causal = [item for item in reports[turn]["insights"] if item["kind"] == "causal_limit"]
        note = reports[turn]["view"]["note"].lower()
        safe = bool(causal) and "cannot explain" in note and ("cannot" in note and "intervention" in note)
        checks.append({"name": f"turn-{turn}-visible-causal-and-intervention-limit", "passed": safe})
        if not safe:
            failures.append(f"turn {turn} does not visibly refuse unsupported cause/intervention claims")

    final_browser = json.loads((args.run_dir / "turn-4/browser/browser-check.json").read_text())
    metric_control_passed = final_browser.get("selected_metric") == employment
    checks.append({"name": "turn-4-employment-indicator-control", "passed": metric_control_passed})
    if not metric_control_passed:
        failures.append("the employment indicator could not be selected in the browser")

    with (args.run_dir / "turn-4/browser/downloads/filtered-dashboard.csv").open(newline="") as handle:
        downloaded = list(csv.DictReader(handle))
    download_passed = (
        len(downloaded) == 2
        and {row["district"] for row in downloaded} == set(oracle["turn_4_download"]["required_districts"])
        and {int(row["year"]) for row in downloaded} == {oracle["turn_4_download"]["required_year"]}
        and all(row["source"] == oracle["turn_4_download"]["required_source"] for row in downloaded)
        and completion in downloaded[0] and employment in downloaded[0]
    )
    checks.append({"name": "turn-4-traceable-two-row-download", "passed": download_passed})
    if not download_passed:
        failures.append("turn 4 download is not the requested two-row, two-metric comparison")

    result = {
        "case_id": "dev-safe-programme-001",
        "checks": checks,
        "critical_failures": failures,
        "passed_critical": not failures,
        "fully_satisfied_oracle": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
