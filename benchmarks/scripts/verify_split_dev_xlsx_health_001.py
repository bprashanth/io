#!/usr/bin/env python3
"""Verify the split-pipeline maternal-health workbook case against its oracle."""

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
    oracle = json.loads(Path("benchmarks/cases/dev-xlsx-health-001/oracle.json").read_text())
    reports = {
        turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text())
        for turn in range(1, 5)
    }
    checks: list[dict[str, object]] = []
    failures: list[str] = []
    shortfalls: list[str] = []

    metrics = oracle["metrics"]
    for turn, expected_rows in ((1, 9), (2, 6), (3, 4), (4, 4)):
        rows = reports[turn]["rows"]
        expected_names = list(metrics) if turn < 3 else ["postnatal_check_48h_coverage"]
        values_passed = True
        for row in rows:
            district, year = str(row["district"]), str(row["year"])
            for name in expected_names:
                expected = float(metrics[name]["expected"][district][year])
                values_passed &= round(float(row[name]), 1) == expected
        row_passed = len(rows) == expected_rows and values_passed
        checks.append({"name": f"turn-{turn}-rows-and-values", "passed": row_passed})
        if not row_passed:
            failures.append(f"turn {turn} rows or calculated coverage differ from the oracle")

        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        checks.append({"name": f"turn-{turn}-browser", "passed": browser["passed"]})
        if not browser["passed"]:
            failures.append(f"turn {turn} browser check failed")

    turn_2_years = {int(row["year"]) for row in reports[2]["rows"]}
    years_passed = turn_2_years == set(oracle["allowed_years_after_turn_2"])
    checks.append({"name": "turn-2-durable-year-set", "passed": years_passed})
    if not years_passed:
        failures.append("turn 2 did not retain exactly 2022 and 2023")

    final_rows = reports[4]["rows"]
    final_scope = (
        {row["district"] for row in final_rows} == set(oracle["turn_3"]["districts"])
        and {int(row["year"]) for row in final_rows} == {2022, 2023}
        and reports[4]["view"]["y"] == [oracle["turn_3"]["indicator"]]
    )
    checks.append({"name": "turn-4-durable-comparison", "passed": final_scope})
    if not final_scope:
        failures.append("turn 4 lost the requested indicator, districts, or years")

    changes = {
        (item["label"], float(item["value"]))
        for item in reports[3]["insights"]
        if item["kind"] == "change"
    }
    expected_changes = {
        ("Gaya", float(oracle["turn_3"]["Gaya_change_2022_to_2023_percentage_points"])),
        ("Nalanda", float(oracle["turn_3"]["Nalanda_change_2022_to_2023_percentage_points"])),
    }
    changes_passed = changes == expected_changes
    checks.append({"name": "turn-3-percentage-point-changes", "passed": changes_passed})
    if not changes_passed:
        failures.append("turn 3 percentage-point changes are wrong or missing")

    gap = [item for item in reports[3]["insights"] if item["kind"] == "difference"]
    gap_passed = bool(gap and float(gap[0]["value"]) == float(oracle["turn_3"]["Nalanda_minus_Gaya_2023_percentage_points"]))
    checks.append({"name": "turn-3-2023-gap-explicit", "passed": gap_passed, "critical": False})
    if not gap_passed:
        shortfalls.append("The page shows both 2023 values but does not explicitly state the 7 pp Nalanda–Gaya gap.")

    html = (args.run_dir / "turn-4/workspace/index.html").read_text()
    traceable = all(sheet in html for sheet in oracle["citation"]["required_sheets"])
    traceable &= all(item["formula"] in html for item in metrics.values())
    traceable &= "not official statistics" in html
    checks.append({"name": "turn-4-source-sheets-formulas-caveat", "passed": traceable})
    if not traceable:
        failures.append("the final page does not visibly preserve source sheets, formulas, and fixture caveat")

    download = args.run_dir / "turn-4/browser/downloads/filtered-dashboard.csv"
    with download.open(newline="") as handle:
        downloaded = list(csv.DictReader(handle))
    download_passed = (
        len(downloaded) == oracle["turn_4_download"]["required_district_year_observations"]
        and {row["district"] for row in downloaded} == set(oracle["turn_4_download"]["required_districts"])
        and {int(row["year"]) for row in downloaded} == set(oracle["turn_4_download"]["required_years"])
        and all(row["source_sheet"] == oracle["sheets"]["data"] for row in downloaded)
        and all(row["source"] == oracle["citation"]["label"] for row in downloaded)
    )
    checks.append({"name": "turn-4-traceable-download", "passed": download_passed})
    if not download_passed:
        failures.append("turn 4 download is not the traceable four-row comparison")

    result = {
        "case_id": "dev-xlsx-health-001",
        "scope_warning": "This clean two-sheet rectangular fixture does not validate merged headers, stacked subtables, or cross-sheet extraction.",
        "checks": checks,
        "critical_failures": failures,
        "noncritical_shortfalls": shortfalls,
        "passed_critical": not failures,
        "fully_satisfied_oracle": not failures and not shortfalls,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
