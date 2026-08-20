#!/usr/bin/env python3
"""Hydrate the audited static dashboard from executed query-gate records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from run_v2_query_gate import create_database, write_json
from run_split_pipeline import render, write_csv


def clean(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def label(name: str) -> str:
    return name.replace("_", " ").strip().title()


def build_report(
    manifest: dict[str, Any],
    record: dict[str, Any],
    frame: pd.DataFrame,
) -> dict[str, Any]:
    question = record["question"]
    years = [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", question)]
    if not any("year" in str(column).casefold() for column in frame.columns):
        if len(set(years)) == 1:
            frame["year"] = years[0]
        elif len(set(years)) >= 2:
            frame["from_year"] = min(years)
            frame["to_year"] = max(years)

    source_specs = [table for table in manifest["tables"] if table["name"] in record["task_tables"]]
    source_names = [Path(table["path"]).name for table in source_specs]
    if "source" not in frame.columns:
        frame["source"] = "; ".join(source_names)

    time_columns = [
        str(column) for column in frame.columns
        if any(token in str(column).casefold() for token in ("year", "date", "period", "month", "quarter"))
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    numeric = [
        str(column) for column in frame.columns
        if pd.api.types.is_numeric_dtype(frame[column]) and str(column) not in time_columns
    ]
    dimensions = [
        str(column) for column in frame.columns
        if not pd.api.types.is_numeric_dtype(frame[column]) and str(column) != "source"
    ]
    if not numeric or not dimensions:
        raise ValueError("result needs at least one numeric measure and one categorical dimension")

    metric = numeric[0]
    if time_columns and frame[time_columns[0]].nunique(dropna=True) > 1:
        chart = "line"
        x = time_columns[0]
        series = dimensions[0]
    else:
        chart = "grouped_bar"
        x = dimensions[0]
        series = None
    unit = (
        "percent" if "percent" in metric.casefold() else
        "tonnes per hectare" if "tonnes_per_hectare" in metric.casefold() else
        "number"
    )
    title = f"{label(metric)} by {label(x)}"
    if series:
        title += f" and {label(series)}"
    insights = []
    valid = frame.dropna(subset=[metric])
    if not valid.empty:
        direction = "lowest" if any(word in question.casefold() for word in ("lowest", "smallest", "worst")) else "highest"
        chosen_index = valid[metric].idxmin() if direction == "lowest" else valid[metric].idxmax()
        chosen = valid.loc[chosen_index]
        insights.append({
            "kind": direction,
            "label": str(chosen[dimensions[0]]),
            "value": clean(chosen[metric]),
            "metric": metric,
        })

    rows = [{str(key): clean(value) for key, value in row.items()} for row in frame.to_dict("records")]
    combined_hash = hashlib.sha256()
    for table in source_specs:
        combined_hash.update((Path(__file__).resolve().parents[2] / table["path"]).read_bytes())
    return {
        "schema_version": 1,
        "case_id": "v2-agriculture-query-journey",
        "title": title,
        "question": question,
        "view": {
            "title": title,
            "chart": chart,
            "x": x,
            "y": numeric,
            "series": series,
            "unit": unit,
            "note": f"Computed locally from {', '.join(source_names)}. Values come from the executed query; no remote assets are used.",
        },
        "columns": list(map(str, frame.columns)),
        "rows": rows,
        "insight_specs": [],
        "insights": insights,
        "source": {
            "file": "; ".join(source_names),
            "sha256": combined_hash.hexdigest(),
            "provenance": "Synthetic cross-sector holdout fixture frozen before the journey run; no people or sensitive records.",
            "format": "csv",
            "tables": record["task_tables"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    tasks = {task["id"]: task for task in manifest["tasks"]}
    db, _ = create_database(manifest)
    for turn, record_path in enumerate(sorted((args.run / "samples").glob("*/record.json")), 1):
        record = json.loads(record_path.read_text())
        if not record["passed"]:
            raise ValueError(f"cannot render failed query record {record['id']}")
        cursor = db.execute(record["sql_duckdb"])
        columns = [description[0] for description in cursor.description]
        frame = pd.DataFrame(cursor.fetchall(), columns=columns)
        record["task_tables"] = tasks[record["task_id"]]["tables"]
        report = build_report(manifest, record, frame)
        turn_dir = args.output / f"turn-{turn}"
        workspace = turn_dir / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        write_json(turn_dir / "insight-report.json", report)
        render(report, workspace / "index.html")
        write_csv(workspace / "all-result-rows.csv", report)
        print(json.dumps({
            "turn": turn,
            "record": record["id"],
            "rows": len(report["rows"]),
            "chart": report["view"]["chart"],
            "workspace": str(workspace),
        }))
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
