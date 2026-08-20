#!/usr/bin/env python3
"""Verify the split-pipeline digital PDF case against its oracle."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def coverage(row: dict[str, object]) -> float:
    name = next(name for name in row if "facility_delivery_coverage" in name)
    return round(float(row[name]), 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    oracle = json.loads(Path("benchmarks/cases/dev-pdf-health-001/oracle.json").read_text())
    reports = {
        turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text())
        for turn in range(1, 5)
    }
    checks: list[dict[str, object]] = []
    failures: list[str] = []

    expected = {
        (district, int(year)): float(value)
        for district, years in oracle["expected_percentages"].items()
        for year, value in years.items()
    }
    for turn, expected_rows in ((1, 12), (2, 8), (3, 4), (4, 4)):
        rows = reports[turn]["rows"]
        values = {(str(row["district"]), int(row["year"])): coverage(row) for row in rows}
        values_passed = all(values[key] == expected[key] for key in values)
        citations_passed = all(
            int(row["source_page"]) == oracle["citation"]["page"]
            and row["source_table"] == oracle["citation"]["table"]
            and row["source"] == oracle["citation"]["label"]
            for row in rows
        )
        passed = len(rows) == expected_rows and values_passed and citations_passed
        checks.append({"name": f"turn-{turn}-rows-values-citations", "passed": passed})
        if not passed:
            failures.append(f"turn {turn} rows, values, or row-level citations differ from the oracle")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        checks.append({"name": f"turn-{turn}-browser", "passed": browser["passed"]})
        if not browser["passed"]:
            failures.append(f"turn {turn} browser check failed")

    year_scope = {int(row["year"]) for row in reports[4]["rows"]} == set(oracle["allowed_years_after_turn_2"])
    district_scope = {row["district"] for row in reports[4]["rows"]} == set(oracle["turn_3"]["districts"])
    checks.append({"name": "turn-4-durable-scope", "passed": year_scope and district_scope})
    if not year_scope or not district_scope:
        failures.append("turn 4 lost the two-year or two-district scope")

    differences = [item for item in reports[3]["insights"] if item["kind"] == "difference"]
    difference_passed = bool(
        differences
        and float(differences[0]["value"]) == float(oracle["turn_3"]["Purnia_minus_Kishanganj_percentage_points"])
        and int(differences[0]["time"]) == oracle["turn_3"]["year"]
        and differences[0]["unit"] == "percentage points"
    )
    checks.append({"name": "turn-3-six-percentage-point-gap", "passed": difference_passed})
    if not difference_passed:
        failures.append("turn 3 does not state the correct six-percentage-point 2023 gap")

    with (args.run_dir / "turn-4/browser/downloads/filtered-dashboard.csv").open(newline="") as handle:
        downloaded = list(csv.DictReader(handle))
    download_passed = (
        len(downloaded) == oracle["turn_4_download"]["required_district_year_observations"]
        and {row["district"] for row in downloaded} == set(oracle["turn_4_download"]["required_districts"])
        and {int(row["year"]) for row in downloaded} == set(oracle["turn_4_download"]["required_years"])
        and all(int(row["source_page"]) == oracle["turn_4_download"]["required_source_page"] for row in downloaded)
        and all(row["source_table"] == oracle["citation"]["table"] for row in downloaded)
        and all(row["source"] == oracle["citation"]["label"] for row in downloaded)
    )
    checks.append({"name": "turn-4-traceable-four-row-download", "passed": download_passed})
    if not download_passed:
        failures.append("turn 4 download is not the traceable four-row comparison")

    final_browser = json.loads((args.run_dir / "turn-4/browser/browser-check.json").read_text())
    source_text = final_browser["source_text"]
    page_visible = "page 2" in source_text.lower() or "Pages: 2" in source_text
    caveat_passed = "not official statistics" in source_text and page_visible and "Table 1" in source_text
    checks.append({"name": "turn-4-visible-citation-and-caveat", "passed": caveat_passed})
    if not caveat_passed:
        failures.append("final page omits the visible page/table citation or not-official caveat")

    result = {
        "case_id": "dev-pdf-health-001",
        "scope_warning": "This digital text PDF fixture does not validate scans, spanning headers, nested tables, or multiple candidate table regions.",
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
