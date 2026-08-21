#!/usr/bin/env python3
"""Replay a query run through generic local obligation checks and score routing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import expressions as exp

from run_v2_query_gate import create_database, sha256, write_json


def known_text_values(db: Any, table_names: list[str]) -> set[str]:
    values: set[str] = set()
    for table in table_names:
        columns = db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = ? AND data_type IN ('VARCHAR', 'TEXT')",
            [table],
        ).fetchall()
        for (column,) in columns:
            quoted_table = table.replace('"', '""')
            quoted_column = column.replace('"', '""')
            query = f'SELECT DISTINCT "{quoted_column}" FROM "{quoted_table}" WHERE "{quoted_column}" IS NOT NULL'
            values.update(str(row[0]).casefold() for row in db.execute(query).fetchall())
    return values


def unwrap_alias(expression: exp.Expression) -> exp.Expression:
    return expression.this if isinstance(expression, exp.Alias) else expression


def is_plain_column(expression: exp.Expression) -> bool:
    return isinstance(unwrap_alias(expression), exp.Column)


def has_division_ancestor(node: exp.Expression) -> bool:
    parent = node.parent
    while parent is not None and not isinstance(parent, exp.Select):
        if isinstance(parent, exp.Div):
            return True
        parent = parent.parent
    return False


def validate_obligations(
    question: str,
    sql: str,
    output_columns: list[str],
    output_rows: list[list[Any]],
    category_values: set[str],
) -> list[str]:
    errors: list[str] = []
    lowered = question.casefold()
    tree = sqlglot.parse_one(sql, read="duckdb")
    select = next(tree.find_all(exp.Select), None)
    if select is None:
        return ["no SELECT projection"]

    literals = [str(node.this).casefold() for node in tree.find_all(exp.Literal) if node.is_string]
    for literal in literals:
        if literal in category_values:
            continue
        pieces = [piece for piece in re.split(r"[\s,;/]+", literal) if piece]
        if len(pieces) > 1 and all(piece in category_values for piece in pieces):
            errors.append(f"combined categorical literal {literal!r} should be separate values")

    absence_query = any(marker in lowered for marker in (
        "missing", "blank", "not available", "have no", "has no",
    ))
    metric_terms = (
        "percent", "percentage", "rate", "ratio", "coverage", "average",
        "mean", "total", "sum", "change", "difference", "gap", "count",
    )
    requests_metric = not absence_query and any(term in lowered for term in metric_terms)
    numeric_output = any(
        any(isinstance(row[index], (int, float)) and not isinstance(row[index], bool) for row in output_rows)
        and not any(token in name.casefold() for token in (
            "year", "date", "period", "month", "quarter", "source", "page", "row", "rank",
        ))
        for index, name in enumerate(output_columns)
    )
    if requests_metric and all(is_plain_column(expression) for expression in select.expressions) and not numeric_output:
        errors.append("requested metric is not present in the SELECT output")

    output_names = {name.casefold() for name in output_columns}
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    if len(years) >= 2:
        asks_change = any(term in lowered for term in (
            "change", "difference", "growth", "increase", "decrease",
        ))
        time_indexes = [
            index for index, name in enumerate(output_columns)
            if any(token in name.casefold() for token in (
                "year", "date", "period", "month", "quarter",
            ))
        ]
        retained_periods = {
            str(value)
            for index in time_indexes
            for row in output_rows
            for value in [row[index]]
            if value is not None
        }
        has_long_endpoints = all(year in retained_periods for year in years)
        has_wide_endpoints = all(
            any(year in name for name in output_names) for year in years
        )
        if not has_long_endpoints and not has_wide_endpoints:
            qualifier = "change " if asks_change else "multi-period "
            errors.append(
                f"{qualifier}output omits the named comparison periods or their endpoint measures"
            )

    dimension_rules = {
        "district": (
            r"district[ -]?wise", r"each district", r"show[^.]*district",
            r"which districts", r"district list", r"compare districts",
        ),
        "region": (r"show region", r"region and period", r"give region"),
        "period": (r"region and period", r"give region[^.]*period"),
    }
    for dimension, patterns in dimension_rules.items():
        if any(re.search(pattern, lowered) for pattern in patterns) and dimension not in output_names:
            errors.append(f"requested grouping column {dimension!r} is absent from output")

    ascending = any(term in lowered for term in (
        "lowest", "ascending", "low to high", "smallest", "worst first",
    ))
    descending = any(term in lowered for term in (
        "highest", "descending", "top to bottom", "best first",
    )) or ("higher" in lowered and "in order" in lowered)
    if ascending or descending:
        order = select.args.get("order")
        if order is None or not order.expressions:
            errors.append("requested ranking has no ORDER BY")
        else:
            first = order.expressions[0]
            is_desc = bool(first.args.get("desc"))
            if ascending and is_desc:
                errors.append("requested ascending ranking is descending")
            if descending and not is_desc:
                errors.append("requested descending ranking is ascending")
            ordered_expression = first.this
            aliases = {
                expression.alias_or_name.casefold()
                for expression in select.expressions
                if not is_plain_column(expression) and expression.alias_or_name
            }
            if isinstance(ordered_expression, exp.Column):
                name = ordered_expression.name.casefold()
                if name not in aliases and name in {"district", "region", "period", "year"}:
                    errors.append("ranking is ordered by a grouping label instead of the requested metric")

    explicit_percent = "percent" in lowered or "percentage" in lowered
    if explicit_percent and not any(
        isinstance(node, exp.Literal) and not node.is_string and str(node.this) in {"100", "100.0"}
        for node in tree.walk()
    ):
        errors.append("percentage request has no visible scale-to-100 operation")

    if "percentage-point" in lowered or "percentage point" in lowered or re.search(r"\bpp\b", lowered):
        subtractions = list(tree.find_all(exp.Sub))
        if not subtractions:
            errors.append("percentage-point request has no subtraction")
        elif all(has_division_ancestor(node) for node in subtractions):
            errors.append("percentage-point difference is converted into relative percent change")

    if not output_rows and any(literal in category_values for literal in literals):
        errors.append("empty result despite filters containing known categorical values")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("benchmarks/v2/query-suite-v2.json"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    tasks = {task["id"]: task for task in manifest["tasks"]}
    db, _ = create_database(manifest)
    records = []
    for record_path in sorted((args.run / "samples").glob("*/record.json")):
        record = json.loads(record_path.read_text())
        task = tasks[record["task_id"]]
        sql = record.get("sql_duckdb")
        errors: list[str]
        output_columns: list[str] = []
        if not sql:
            errors = ["no executable SQL"]
        else:
            try:
                cursor = db.execute(sql)
                output_columns = [description[0] for description in cursor.description]
                output_rows = [list(row) for row in cursor.fetchall()]
                errors = validate_obligations(
                    record["question"],
                    sql,
                    output_columns,
                    output_rows,
                    known_text_values(db, task["tables"]),
                )
            except Exception as error:
                errors = [f"saved query is not executable: {type(error).__name__}: {error}"]
        records.append({
            "id": record["id"],
            "task_id": record["task_id"],
            "model_passed_hidden_oracle": record["passed"],
            "route": "qwen3.8-27b" if errors else "accept_local",
            "obligation_errors": errors,
            "output_columns": output_columns,
        })

    accepted = [record for record in records if record["route"] == "accept_local"]
    escalated = [record for record in records if record["route"] != "accept_local"]
    summary = {
        "schema_version": 1,
        "manifest": str(args.manifest),
        "manifest_sha256": sha256(args.manifest),
        "source_run": str(args.run),
        "samples": len(records),
        "accepted_local": len(accepted),
        "escalated": len(escalated),
        "accepted_correct": sum(record["model_passed_hidden_oracle"] for record in accepted),
        "accepted_wrong": sum(not record["model_passed_hidden_oracle"] for record in accepted),
        "escalated_wrong": sum(not record["model_passed_hidden_oracle"] for record in escalated),
        "escalated_correct": sum(record["model_passed_hidden_oracle"] for record in escalated),
        "records": records,
    }
    write_json(args.output, summary)
    print(json.dumps({key: summary[key] for key in (
        "samples", "accepted_local", "escalated", "accepted_correct",
        "accepted_wrong", "escalated_wrong", "escalated_correct",
    )}))
    db.close()
    return 0 if summary["accepted_wrong"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
