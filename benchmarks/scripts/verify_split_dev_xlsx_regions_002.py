#!/usr/bin/env python3
"""Verify a side-by-side, mixed-unit workbook journey."""

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
    oracle = json.loads(Path("benchmarks/cases/dev-xlsx-regions-002/oracle.json").read_text())
    reports = {turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text()) for turn in range(1, 5)}
    checks: list[dict[str, object]] = []
    failures: list[str] = []

    def check(name: str, passed: bool, failure: str) -> None:
        checks.append({"name": name, "passed": passed})
        if not passed:
            failures.append(failure)

    for turn, row_count in ((1, 6), (2, 6), (3, 2), (4, 2)):
        rows = reports[turn]["rows"]
        exact = len(rows) == row_count and all(
            float(row[metric]) == float(oracle["metrics"][metric][row["block"]][str(row["year"])])
            for row in rows for metric in oracle["metrics"]
        )
        check(f"turn-{turn}-exact-values-and-scope", exact, f"turn {turn} scope or values differ")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        check(f"turn-{turn}-browser", bool(browser["passed"]), f"turn {turn} browser failed")
        if turn >= 2:
            selected = browser.get("selected_body_text") or ""
            check(f"turn-{turn}-referral-count-unit", "150%" not in selected and "160%" not in selected,
                  f"turn {turn} formats referral counts as percentages")

    check("turn-1-left-region-focus", reports[1]["view"]["y"] == oracle["turn_1"]["required_metrics"],
          "turn 1 did not focus on the requested left-hand screening table")
    check("turn-2-adds-right-region", set(reports[2]["view"]["y"]) == set(oracle["turn_2"]["required_metrics"]),
          "turn 2 did not add referrals while retaining screening")

    for turn in (3, 4):
        rows = reports[turn]["rows"]
        scope = (
            {row["block"] for row in rows} == set(oracle["turn_3"]["required_blocks"])
            and {int(row["year"]) for row in rows} == {oracle["turn_3"]["required_year"]}
            and set(reports[turn]["view"]["y"]) == set(oracle["turn_3"]["required_metrics"])
        )
        check(f"turn-{turn}-durable-two-metric-scope", scope, f"turn {turn} lost the year, blocks or metrics")

    gaps = {item.get("metric"): item for item in reports[3]["insights"] if item["kind"] == "difference"}
    check("turn-3-screening-gap", bool(
        gaps.get("screening_coverage_percent")
        and float(gaps["screening_coverage_percent"]["value"]) == oracle["turn_3"]["screening_gap_percentage_points"]
        and gaps["screening_coverage_percent"].get("unit") == "percentage points"
    ), "turn 3 does not state the exact screening percentage-point gap")
    check("turn-3-referral-gap", bool(
        gaps.get("referrals_completed")
        and float(gaps["referrals_completed"]["value"]) == oracle["turn_3"]["referral_gap_children"]
        and gaps["referrals_completed"].get("unit") == "number"
    ), "turn 3 does not state the exact referral-count gap")

    html = (args.run_dir / "turn-4/workspace/index.html").read_text()
    check("turn-4-sheet-table-range-citation", bool(
        oracle["required_sheet"] in html
        and all(table in html for table in oracle["required_tables"])
        and all(cell_range in html for cell_range in oracle["required_ranges"])
        and "not official statistics" in html
    ), "final page omits exact workbook provenance or caveat")

    with (args.run_dir / "turn-4/browser/downloads/filtered-dashboard.csv").open(newline="") as handle:
        downloaded = list(csv.DictReader(handle))
    check("turn-4-traceable-two-row-download", bool(
        len(downloaded) == oracle["turn_4_download"]["required_rows"]
        and {row["block"] for row in downloaded} == set(oracle["turn_4_download"]["required_blocks"])
        and {int(row["year"]) for row in downloaded} == {oracle["turn_4_download"]["required_year"]}
        and all(metric in downloaded[0] for metric in oracle["turn_3"]["required_metrics"])
        and all(row["source_sheet"] == oracle["required_sheet"] for row in downloaded)
        and all(table in row["source_table"] for row in downloaded for table in oracle["required_tables"])
        and all(cell_range in row["source_range"] for row in downloaded for cell_range in oracle["required_ranges"])
    ), "final download is not the exact traceable two-row comparison")

    result = {
        "case_id": "dev-xlsx-regions-002",
        "scope_warning": "This adds a second layout family; it still does not establish arbitrary workbook understanding.",
        "checks": checks, "critical_failures": failures,
        "passed_critical": not failures, "fully_satisfied_oracle": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
