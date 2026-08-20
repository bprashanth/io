#!/usr/bin/env python3
"""Local-first, replayable data-to-dashboard prototype.

The small and 27B models only propose one read-only DuckDB query. Local code
loads the files, validates and executes the query, builds insights, renders the
page, and writes the download. The optional frontier envelope is value-free and
is persisted for audit; this prototype does not need to send it when the local
renderer succeeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import sqlglot
from sqlglot import expressions as exp

from frontier_boundary import serialize_frontier_layout_request
from replay_query_router import validate_obligations
from run_split_pipeline import load_source, render, write_csv
from run_v2_query_gate import call_model, extract_sql, write_json


def safe_name(path: Path, used: set[str]) -> str:
    base = re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", path.stem.casefold())).strip("_")
    base = base or "data"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def clean(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tables(paths: list[Path]) -> tuple[duckdb.DuckDBPyConnection, list[dict[str, Any]], set[str]]:
    db = duckdb.connect(":memory:")
    tables: list[dict[str, Any]] = []
    category_values: set[str] = set()
    used: set[str] = set()
    for path in paths:
        frame, local_profile, metadata = load_source(path, include_values=True)
        name = safe_name(path, used)
        db.register(name, frame)
        categories: dict[str, list[str]] = {}
        for column in frame.columns:
            series = frame[column]
            if pd.api.types.is_numeric_dtype(series):
                continue
            values = [str(value) for value in series.dropna().drop_duplicates().head(50)]
            if len(values) <= 50:
                categories[str(column)] = values
                category_values.update(value.casefold() for value in values)
        tables.append({
            "name": name,
            "path": str(path.resolve()),
            "file": path.name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "columns": [{"name": str(column), "type": str(frame[column].dtype)} for column in frame.columns],
            "known_categories_local_or_27b_only": categories,
            "structure": metadata,
            "profile_local_or_27b_only": local_profile,
        })
    return db, tables, category_values


def ddl(db: duckdb.DuckDBPyConnection, tables: list[dict[str, Any]]) -> str:
    statements = []
    for table in tables:
        columns = db.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table["name"]],
        ).fetchall()
        rendered = ", ".join(f'"{name.replace(chr(34), chr(34) * 2)}" {kind}' for name, kind in columns)
        statements.append(f'CREATE TABLE "{table["name"]}" ({rendered});')
    return "\n".join(statements)


def make_prompt(question: str, conversation: list[dict[str, Any]], schema: str,
                tables: list[dict[str, Any]], repair: str | None = None) -> str:
    categories = {
        table["name"]: table["known_categories_local_or_27b_only"]
        for table in tables
    }
    prior = [
        {"question": turn["question"], "sql": turn["sql"], "output_columns": turn["output_columns"]}
        for turn in conversation[-4:]
    ]
    sections = [
        "You translate ordinary questions into exactly one read-only DuckDB SELECT or WITH query.",
        "Return SQL only. Never write files, install software, calculate values yourself, or invent columns.",
        "Use only the supplied schema. Preserve relevant scope from earlier turns unless the newest question changes it.",
        "A requested rate must use its stated numerator and denominator. Percentage-point change means later percentage minus earlier percentage, not relative growth.",
        "When the user explicitly asks for percent or percentage, multiply numerator divided by denominator by 100.",
        "When the user asks to compare years or groups without asking for a change, keep those year/group columns and requested measures in the output.",
        "When several known category values are named, filter them separately with IN rather than concatenating them.",
        "Use NULLIF for denominators. Missing values remain missing and are not zero.",
        f"SCHEMA:\n{schema}",
        f"KNOWN CATEGORICAL VALUES (local or trusted 27B tier only):\n{json.dumps(categories, ensure_ascii=False)}",
        f"PRIOR TURNS:\n{json.dumps(prior, ensure_ascii=False)}",
        f"CURRENT QUESTION:\n{question}",
    ]
    if repair:
        sections.append(f"REJECTED QUERY ERROR:\n{repair}\nReturn a complete corrected query.")
    return "\n\n".join(sections)


def output_columns(db: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[list[Any]]]:
    cursor = db.execute(sql)
    columns = [description[0] for description in cursor.description]
    return columns, [list(row) for row in cursor.fetchall()]


def extra_obligations(question: str, sql: str, columns: list[str], rows: list[list[Any]],
                      tables: list[dict[str, Any]]) -> list[str]:
    """Generic shape checks not tied to a fixture, sector, or expected answer."""
    errors: list[str] = []
    lowered = question.casefold()
    names = {column.casefold() for column in columns}
    tree = sqlglot.parse_one(sql, read="duckdb")
    selected = next(tree.find_all(exp.Select), None)
    if selected is None:
        return ["no SELECT projection"]
    computed_percent_aliases_without_percent_inputs = {
        expression.alias_or_name.casefold()
        for expression in selected.expressions
        if isinstance(expression, exp.Alias)
        and not isinstance(expression.this, exp.Column)
        and expression.alias_or_name
        and re.search(r"percent(?:age)?|(?:^|_)pp(?:_|$)", expression.alias_or_name.casefold())
        and not any(
            re.search(r"percent(?:age)?|(?:^|_)pp(?:_|$)", column.name.casefold())
            for column in expression.this.find_all(exp.Column)
        )
    }
    asks_percent = bool(re.search(r"\bpercent(?:age)?\b|\bpp\b|percentage[ -]point", lowered))
    unrequested_percent_outputs = [
        column for column in columns
        if re.search(r"percent(?:age)?|(?:^|_)pp(?:_|$)", column.casefold())
        and column.casefold() in computed_percent_aliases_without_percent_inputs
        and not asks_percent
    ]
    if unrequested_percent_outputs:
        errors.append(
            "output claims an unrequested percentage unit: "
            + ", ".join(unrequested_percent_outputs)
        )
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    asks_change = any(term in lowered for term in ("change", "difference", "growth", "increase", "decrease"))
    if len(years) >= 2 and not asks_change:
        has_time_column = any(
            token in name for name in names
            for token in ("year", "date", "period", "month", "quarter")
        )
        has_one_metric_column_per_period = all(
            any(year in name for name in names) for year in years
        )
        if not has_time_column and not has_one_metric_column_per_period:
            errors.append("multiple requested periods are collapsed into an output without a time column")

    output_index = {name.casefold(): index for index, name in enumerate(columns)}
    for table in tables:
        for column, admitted in table["known_categories_local_or_27b_only"].items():
            named = [value for value in admitted if re.search(
                rf"(?<![\w]){re.escape(value.casefold())}(?![\w])", lowered
            )]
            if len(named) < 2 or column.casefold() not in output_index:
                continue
            index = output_index[column.casefold()]
            shown = {str(row[index]).casefold() for row in rows}
            missing = [value for value in named if value.casefold() not in shown]
            if missing:
                errors.append(f"named categories are absent from output: {missing}")
    return errors


def query_tier(*, endpoint: str, model: str, api_key: str | None, question: str,
               conversation: list[dict[str, Any]], schema: str, tables: list[dict[str, Any]],
               db: duckdb.DuckDBPyConnection, category_values: set[str], timeout: int,
               max_tokens: int, reasoning_effort: str | None) -> dict[str, Any]:
    prompt = make_prompt(question, conversation, schema, tables)
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 3):
        started = time.monotonic()
        record: dict[str, Any] = {"attempt": attempt, "prompt": prompt}
        try:
            response, api = call_model(
                endpoint, model, prompt, timeout, api_key, max_tokens,
                reasoning_effort, 0.0,
            )
            sql = extract_sql(response)
            columns, rows = output_columns(db, sql)
            errors = validate_obligations(question, sql, columns, rows, category_values)
            errors += extra_obligations(question, sql, columns, rows, tables)
            record.update({
                "response": response, "api": api, "sql": sql,
                "output_columns": columns, "rows": rows,
                "obligation_errors": errors,
                "duration_seconds": round(time.monotonic() - started, 3),
            })
            attempts.append(record)
            if not errors:
                return {"accepted": True, "attempts": attempts, **record}
            return {"accepted": False, "attempts": attempts, **record}
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            record.update({"error": message, "duration_seconds": round(time.monotonic() - started, 3)})
            attempts.append(record)
            if attempt == 2:
                return {"accepted": False, "attempts": attempts, "error": message}
            prompt = make_prompt(question, conversation, schema, tables, message)
    raise AssertionError("unreachable")


def human(name: str) -> str:
    return name.replace("_", " ").strip().title()


def frontier_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    return "string"


def build_report(question: str, columns: list[str], rows: list[list[Any]],
                 tables: list[dict[str, Any]], session_id: str) -> dict[str, Any]:
    frame = pd.DataFrame(rows, columns=columns)
    time_columns = [
        str(column) for column in frame.columns
        if any(token in str(column).casefold() for token in ("year", "date", "period", "month", "quarter"))
    ]
    numeric = [
        str(column) for column in frame.columns
        if pd.api.types.is_numeric_dtype(frame[column]) and str(column) not in time_columns
    ]
    dimensions = [
        str(column) for column in frame.columns
        if str(column) not in numeric and str(column) not in time_columns
        and "source" not in str(column).casefold()
    ]
    if not numeric:
        raise ValueError("the executed result contains no numeric measure to visualize")
    preferred = [
        column for column in numeric
        if any(token in column.casefold() for token in ("rate", "percent", "coverage", "change", "difference", "yield", "average"))
    ]
    measures = (preferred or numeric)[:4]
    usable_time = next(
        (column for column in time_columns if frame[column].nunique(dropna=True) >= 2),
        None,
    )
    if usable_time:
        x = usable_time
        chart = "line"
        series = dimensions[0] if dimensions else None
    else:
        if not dimensions:
            frame.insert(0, "result", [f"Result {index + 1}" for index in range(len(frame))])
            dimensions = ["result"]
        x = dimensions[0]
        chart = "grouped_bar"
        series = None
    title = f"{', '.join(human(item) for item in measures)} by {human(x)}"
    unit = "percent" if re.search(
        r"\bpercent(?:age)?\b|\bpp\b|percentage[ -]point",
        question.casefold(),
    ) or all(re.search(r"percent(?:age)?|(?:^|_)pp(?:_|$)", item.casefold()) for item in measures) else "number"
    insight_specs: list[dict[str, Any]] = []
    if chart == "line" and series and len(frame[x].dropna().unique()) >= 2:
        insight_specs.append({
            "kind": "change", "metric": measures[0], "entity_column": series,
            "entities": [clean(value) for value in frame[series].dropna().drop_duplicates()],
            "time_column": x, "from": clean(frame[x].min()), "to": clean(frame[x].max()),
            "unit": "percentage points" if unit == "percent" else "number",
        })
    elif not frame.dropna(subset=[measures[0]]).empty:
        direction = "lowest" if any(term in question.casefold() for term in ("lowest", "smallest", "worst")) else "highest"
        insight_specs.append({"kind": direction, "metric": measures[0], "label_column": x})
    report_rows = [
        {str(key): clean(value) for key, value in row.items()}
        for row in frame.to_dict("records")
    ]
    combined = hashlib.sha256("".join(table["sha256"] for table in tables).encode()).hexdigest()
    return {
        "schema_version": 1,
        "case_id": session_id,
        "title": title,
        "question": question,
        "view": {
            "title": title, "chart": chart, "x": x, "y": measures,
            "series": series, "unit": unit,
            "note": "Computed locally from the selected file data. The displayed values come from the executed read-only query.",
        },
        "columns": list(map(str, frame.columns)),
        "rows": report_rows,
        "insight_specs": insight_specs,
        "insights": [],
        "source": {
            "file": "; ".join(table["file"] for table in tables),
            "sha256": combined,
            "provenance": "User-supplied local file(s); no external factual claims were added.",
            "format": "; ".join(sorted({str(table["structure"].get("format", "unknown")) for table in tables})),
            "tables": [table["name"] for table in tables],
        },
    }


def read_api_key(path: Path | None) -> str | None:
    return json.loads(path.expanduser().read_text())["api_key"] if path else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, action="append", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--small-endpoint", default="http://127.0.0.1:8022/v1")
    parser.add_argument("--small-model", default="Snowflake/Arctic-Text2SQL-R1-7B-Q5_K_M")
    parser.add_argument("--fallback-endpoint")
    parser.add_argument("--fallback-model", default="qwen/qwen3.8-27b")
    parser.add_argument("--fallback-api-key-file", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args()

    args.session.mkdir(parents=True, exist_ok=True)
    state_path = args.session / "session.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"schema_version": 1, "turns": []}
    db, tables, category_values = load_tables(args.data)
    schema = ddl(db, tables)
    turn_number = len(state["turns"]) + 1
    turn_dir = args.session / f"turn-{turn_number}"
    turn_dir.mkdir(parents=True, exist_ok=True)

    small = query_tier(
        endpoint=args.small_endpoint, model=args.small_model, api_key=None,
        question=args.question, conversation=state["turns"], schema=schema,
        tables=tables, db=db, category_values=category_values,
        timeout=args.timeout_seconds, max_tokens=args.max_tokens, reasoning_effort=None,
    )
    write_json(turn_dir / "small-tier.json", small)
    route = "small"
    selected = small
    if not small.get("accepted"):
        if not args.fallback_endpoint:
            write_json(turn_dir / "route.json", {
                "route": "stopped", "reason": small.get("obligation_errors") or small.get("error"),
            })
            print(json.dumps({"status": "needs_fallback", "turn": turn_number, "evidence": str(turn_dir)}))
            return 2
        route = "qwen3.8-27b"
        selected = query_tier(
            endpoint=args.fallback_endpoint, model=args.fallback_model,
            api_key=read_api_key(args.fallback_api_key_file), question=args.question,
            conversation=state["turns"], schema=schema, tables=tables, db=db,
            category_values=category_values, timeout=args.timeout_seconds,
            max_tokens=max(args.max_tokens, 2048), reasoning_effort="low",
        )
        write_json(turn_dir / "fallback-tier.json", selected)
        if not selected.get("accepted"):
            write_json(turn_dir / "route.json", {
                "route": "stopped", "reason": selected.get("obligation_errors") or selected.get("error"),
            })
            print(json.dumps({"status": "failed_closed", "turn": turn_number, "evidence": str(turn_dir)}))
            return 3

    report = build_report(
        args.question, selected["output_columns"], selected["rows"], tables,
        args.session.name,
    )
    workspace = turn_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    render(report, workspace / "index.html")
    render(report, args.session / "index.html")
    write_csv(workspace / "all-result-rows.csv", report)
    write_csv(args.session / "all-result-rows.csv", report)
    selected_frame = pd.DataFrame(selected["rows"], columns=selected["output_columns"])
    frontier_envelope = serialize_frontier_layout_request(
        args.question,
        [{"name": column, "type": frontier_type(selected_frame[column])}
         for column in selected["output_columns"]],
    )
    write_json(turn_dir / "frontier-layout-envelope-not-sent.json", frontier_envelope)
    write_json(turn_dir / "report.json", report)
    turn = {
        "turn": turn_number, "question": args.question, "route": route,
        "model": selected["api"].get("model") or selected["api"].get("requested_model"),
        "sql": selected["sql"], "output_columns": selected["output_columns"],
        "row_count": len(selected["rows"]), "workspace": str(workspace),
        "data_hashes": {table["file"]: table["sha256"] for table in tables},
    }
    state["turns"].append(turn)
    write_json(state_path, state)
    write_json(turn_dir / "route.json", {"route": route, "accepted": True})
    db.close()
    print(json.dumps({
        "status": "ok", "turn": turn_number, "route": route,
        "rows": len(selected["rows"]), "dashboard": str(args.session / "index.html"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
