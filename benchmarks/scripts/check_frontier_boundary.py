#!/usr/bin/env python3
"""Build value-free frontier envelopes and scan them against real report rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from frontier_boundary import find_forbidden_values, serialize_frontier_layout_request
from run_v2_query_gate import write_json


def kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for report_path in sorted(args.dashboard_run.glob("turn-*/insight-report.json")):
        report = json.loads(report_path.read_text())
        columns = []
        for name in report["columns"]:
            example = next((row.get(name) for row in report["rows"] if row.get(name) is not None), "")
            columns.append({"name": name, "type": kind(example)})
        envelope = serialize_frontier_layout_request(report["question"], columns)

        allowed_text = report["question"].casefold()
        column_names = {name.casefold() for name in report["columns"]}
        forbidden = []
        for row in report["rows"]:
            for name, value in row.items():
                rendered = str(value).strip()
                if not rendered or name.casefold() in column_names and rendered.casefold() in allowed_text:
                    continue
                if rendered.casefold() not in allowed_text:
                    forbidden.append(value)
        forbidden.extend([
            report["source"].get("file", ""),
            report["source"].get("sha256", ""),
            report["source"].get("provenance", ""),
        ])
        leaks = find_forbidden_values(envelope, forbidden)
        turn_dir = args.output / report_path.parent.name
        write_json(turn_dir / "frontier-layout-request-value-free.json", envelope)
        records.append({
            "turn": report_path.parent.name,
            "forbidden_values_scanned": len(set(map(str, forbidden))),
            "leaks": leaks,
            "passed": not leaks,
        })
    summary = {
        "schema_version": 1,
        "boundary": "user question + column name/type/role + fixed layout contract",
        "explicitly_absent": [
            "rows", "sample values", "distinct values", "row counts", "null counts",
            "minimums", "maximums", "aggregates", "computed insights", "source filenames",
            "hashes", "screenshots", "generated HTML",
        ],
        "records": records,
        "passed": bool(records) and all(record["passed"] for record in records),
    }
    write_json(args.output / "privacy-check.json", summary)
    print(json.dumps(summary))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
