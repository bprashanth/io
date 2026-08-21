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


def reshape_wide_time(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    groups: dict[str, list[tuple[str, int]]] = {}
    for column in map(str, frame.columns):
        match = re.fullmatch(r"(.+)_((?:19|20)\d{2})", column)
        if match and pd.api.types.is_numeric_dtype(frame[column]):
            groups.setdefault(match.group(1), []).append((column, int(match.group(2))))
    candidate = next((item for item in groups.items() if len(item[1]) >= 2), None)
    if candidate is None:
        return frame, []
    metric, columns = candidate
    value_columns = [column for column, _year in sorted(columns, key=lambda item: item[1])]
    id_columns = [column for column in frame.columns if str(column) not in value_columns]
    reshaped = frame.melt(
        id_vars=id_columns,
        value_vars=value_columns,
        var_name="_wide_metric_year",
        value_name=metric,
    )
    reshaped["year"] = reshaped["_wide_metric_year"].str.extract(r"((?:19|20)\d{2})$").astype(int)
    reshaped = reshaped.drop(columns=["_wide_metric_year"])
    return reshaped, [f"reshaped year-suffixed metric columns into year + {metric}"]


def build_report(
    manifest: dict[str, Any],
    record: dict[str, Any],
    frame: pd.DataFrame,
) -> dict[str, Any]:
    question = record["question"]
    frame, normalizations = reshape_wide_time(frame)
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
    insight_specs = []
    insights = []
    valid = frame.dropna(subset=[metric])
    if not valid.empty:
        if series and x in frame.columns:
            entities = list(dict.fromkeys(map(str, valid[series].dropna())))
            insight_specs.append({
                "kind": "change",
                "metric": metric,
                "entity_column": series,
                "entities": entities,
                "time_column": x,
                "from": clean(valid[x].min()),
                "to": clean(valid[x].max()),
                "unit": unit,
            })
        else:
            direction = "lowest" if any(word in question.casefold() for word in ("lowest", "smallest", "worst")) else "highest"
            chosen_index = valid[metric].idxmin() if direction == "lowest" else valid[metric].idxmax()
            chosen = valid.loc[chosen_index]
            insight_specs.append({
                "kind": direction,
                "metric": metric,
                "label_column": dimensions[0],
            })
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
        "insight_specs": insight_specs,
        "insights": insights,
        "normalizations": normalizations,
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
    parser.add_argument("--router-replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    tasks = {task["id"]: task for task in manifest["tasks"]}
    routes = {
        record["id"]: record
        for record in json.loads(args.router_replay.read_text())["records"]
    }
    db, _ = create_database(manifest)
    for turn, record_path in enumerate(sorted((args.run / "samples").glob("*/record.json")), 1):
        record = json.loads(record_path.read_text())
        route = routes.get(record["id"])
        if route is None or route["route"] != "accept_local":
            raise ValueError(f"query record {record['id']} was not accepted by the frozen local router")
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
