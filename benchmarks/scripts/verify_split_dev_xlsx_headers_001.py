#!/usr/bin/env python3
"""Verify the merged-header, stacked-subtable workbook journey."""

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
    oracle = json.loads(Path("benchmarks/cases/dev-xlsx-headers-001/oracle.json").read_text())
    reports = {turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text()) for turn in range(1, 5)}
    checks: list[dict[str, object]] = []
    failures: list[str] = []

    def check(name: str, passed: bool, failure: str) -> None:
        checks.append({"name": name, "passed": passed})
        if not passed:
            failures.append(failure)

    expected = oracle["metrics"]
    for turn, row_count in ((1, 6), (2, 6), (3, 2), (4, 2)):
        rows = reports[turn]["rows"]
        values_passed = True
        for row in rows:
            for metric, blocks in expected.items():
                values_passed &= float(row[metric]) == float(blocks[row["block"]][str(row["year"])])
        check(f"turn-{turn}-rows-and-values", len(rows) == row_count and values_passed,
              f"turn {turn} scope or values differ from the oracle")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        check(f"turn-{turn}-browser", bool(browser["passed"]), f"turn {turn} browser check failed")

    check("turn-1-primary-metrics", set(reports[1]["view"]["y"]) == set(oracle["turn_1"]["required_metrics"]),
          "turn 1 did not focus on both primary attendance measures")
    check("turn-2-recovers-second-subtable", set(reports[2]["view"]["y"]) == set(oracle["turn_2"]["required_metrics"]),
          "turn 2 did not add both secondary measures while retaining primary")

    for turn in (3, 4):
        rows = reports[turn]["rows"]
        scope = (
            {row["block"] for row in rows} == set(oracle["turn_3"]["required_blocks"])
            and {int(row["year"]) for row in rows} == {oracle["turn_3"]["required_year"]}
            and reports[turn]["view"]["y"] == [oracle["turn_3"]["required_metric"]]
        )
        check(f"turn-{turn}-durable-secondary-girls-scope", scope,
              f"turn {turn} lost the secondary-girls, year or block focus")

    gaps = [item for item in reports[3]["insights"] if item["kind"] == "difference"]
    gap_passed = bool(
        gaps and gaps[0].get("metric") == oracle["turn_3"]["required_metric"]
        and float(gaps[0]["value"]) == float(oracle["turn_3"]["gap_percentage_points"])
        and gaps[0].get("unit") == "percentage points"
    )
    check("turn-3-seven-percentage-point-gap", gap_passed, "turn 3 does not state the exact 7 pp gap")

    html = (args.run_dir / "turn-4/workspace/index.html").read_text()
    citation_passed = (
        oracle["required_sheet"] in html
        and all(table in html for table in oracle["required_tables"])
        and all(cell_range in html for cell_range in oracle["required_ranges"])
        and "not official statistics" in html
    )
    check("turn-4-sheet-table-range-citation", citation_passed,
          "final page does not preserve exact sheet, table, ranges and caveat")

    with (args.run_dir / "turn-4/browser/downloads/filtered-dashboard.csv").open(newline="") as handle:
        downloaded = list(csv.DictReader(handle))
    download_passed = (
        len(downloaded) == oracle["turn_4_download"]["required_rows"]
        and {row["block"] for row in downloaded} == set(oracle["turn_4_download"]["required_blocks"])
        and {int(row["year"]) for row in downloaded} == {oracle["turn_4_download"]["required_year"]}
        and oracle["turn_4_download"]["required_metric"] in downloaded[0]
        and all(row["source_sheet"] == oracle["required_sheet"] for row in downloaded)
        and all(table in row["source_table"] for row in downloaded for table in oracle["required_tables"])
        and all(cell_range in row["source_range"] for row in downloaded for cell_range in oracle["required_ranges"])
    )
    check("turn-4-traceable-two-row-download", download_passed,
          "final download is not the traceable two-row comparison")

    result = {
        "case_id": "dev-xlsx-headers-001",
        "scope_warning": "This tests one bounded merged-header and stacked-table pattern, not arbitrary spreadsheet understanding.",
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
