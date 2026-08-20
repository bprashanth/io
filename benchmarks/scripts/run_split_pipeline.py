#!/usr/bin/env python3
"""Development runner: model plan -> validated DuckDB -> static dashboard.

The model never writes SQL, displayed numbers, HTML or JavaScript. Phase one
accepts one CSV; later input adapters will produce the same table contract.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import signal
import time
import urllib.request
from pathlib import Path
from typing import Any

import duckdb
import jsonschema
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "benchmarks/schemas/analysis-plan.schema.json"
KEY_PATH = Path.home() / ".config/idlisseus/openrouter.json"


class PlanError(ValueError):
    pass


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def clean(value: Any) -> Any:
    if pd.isna(value):
        return None
    value = value.item() if hasattr(value, "item") else value
    return None if isinstance(value, float) and not math.isfinite(value) else value


def profile(frame: pd.DataFrame, include_values: bool) -> dict[str, Any]:
    columns = []
    for name in frame.columns:
        series = frame[name]
        item: dict[str, Any] = {
            "name": str(name), "type": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "distinct_count": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series) and len(series.dropna()):
            item.update(minimum=clean(series.min()), maximum=clean(series.max()))
        elif include_values and item["distinct_count"] <= 30:
            item["admitted_values"] = [clean(v) for v in series.dropna().drop_duplicates().head(30)]
        columns.append(item)
    return {"row_count": len(frame), "columns": columns}


def make_prompt(case: dict[str, Any], data_profile: dict[str, Any], messages: list[str], previous: Any) -> str:
    rules = [
        "Plan a safe analysis of one local table. Never calculate or invent values.",
        "Use supplied column names exactly. The executor applies steps in order.",
        "For coverage use derive kind percent, numerator/denominator, unit percent.",
        "Subtracting percentages is percentage points, not percent growth.",
        "Keep rows unless aggregation is requested. Never invent bands or targets.",
        "For an initial request asking for a webpage selector, keep all requested rows; webpage controls are added separately. Never emit placeholders such as {{selected_year}}.",
        "Do not group when there is already one row per entity and time. If aggregation is needed for a rate, use weighted_percent rather than sum or mean of a percent.",
        "The view series is a category such as district, never a numeric metric. Put metrics only in view y.",
        "For a district coverage trend use x=year, y=[derived coverage], series=district, unit=percent.",
        "Source and provenance are rendered separately; do not group or sort merely to display the source.",
        "Write question, title and note for a nontechnical participant. Never mention renderer, SQL, JSON, DuckDB, placeholders or other implementation details.",
        "If data cannot explain why, set can_explain_cause false and add causal_limit.",
        "When the user explicitly asks for a highest, lowest, change or difference, add the matching insight specification so the answer is stated, not left for the user to infer from a chart.",
        "Use line/slope for time, bars for categories, scatter for two measures.",
        "Return only one JSON object matching the response schema.",
    ]
    sections = {
        "DATASET_ID": case["case_id"], "DATASET_PROFILE": data_profile,
        "INPUT_PROVENANCE": case["inputs"], "CONVERSATION_SO_FAR": messages,
        "PREVIOUS_VALID_PLAN": previous,
    }
    return "\n".join(rules) + "\n\n" + "\n".join(
        f"{key}:\n{json.dumps(value, ensure_ascii=False)}" for key, value in sections.items()
    )


def repair_prompt(prompt: str, plan: Any, error: Exception) -> str:
    return prompt + "\n\nREJECTED_PLAN:\n" + json.dumps(plan, ensure_ascii=False) + \
        "\nVALIDATOR_ERROR:\n" + str(error) + \
        "\nReturn a complete corrected plan. Do not explain the correction."


def call_model(model: str, effort: str, prompt: str, schema: dict[str, Any], timeout_seconds: int) -> tuple[dict[str, Any], dict[str, Any]]:
    credential = json.loads(KEY_PATH.read_text())["api_key"]
    document = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a constrained tabular analysis-plan compiler."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "reasoning": {"effort": effort},
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "analysis_plan", "strict": True, "schema": schema,
        }},
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(document).encode(), method="POST",
        headers={"Authorization": f"Bearer {credential}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/bprashanth/io",
                 "X-Title": "NGO split pipeline benchmark"},
    )
    started = time.monotonic()
    def timed_out(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"model response exceeded {timeout_seconds} seconds")
    previous_handler = signal.signal(signal.SIGALRM, timed_out)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = json.load(response)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    duration = round(time.monotonic() - started, 3)
    content = raw["choices"][0]["message"].get("content") or ""
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        raise PlanError("model returned no JSON object")
    return json.loads(match.group()), {
        "requested_model": model, "resolved_model": raw.get("model"),
        "generation_id": raw.get("id"), "duration_seconds": duration,
        "finish_reason": raw["choices"][0].get("finish_reason"),
        "usage": raw.get("usage"), "reasoning_effort": effort,
    }


def quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def bind(plan: dict[str, Any], frame: pd.DataFrame) -> None:
    available = set(map(str, frame.columns))
    for index, step in enumerate(plan["steps"]):
        op = step["op"]
        needed = []
        if op == "filter": needed = [step["column"]]
        elif op == "derive": needed = [step["numerator"], step["denominator"]]
        elif op == "group":
            needed = step["by"] + [a[k] for a in step["aggregates"] for k in
                                    ("column", "weight_column", "denominator_column") if a.get(k)]
        elif op == "sort": needed = [step["column"]]
        missing = [name for name in needed if name not in available]
        if missing:
            raise PlanError(f"step {index} names missing columns: {missing}")
        if op == "derive":
            if step["name"] in available: raise PlanError("derived column already exists")
            available.add(step["name"])
        elif op == "group":
            available = set(step["by"]) | {a["name"] for a in step["aggregates"]}
        if op == "filter" and isinstance(step["value"], str) and ("{{" in step["value"] or "}}" in step["value"]):
            raise PlanError("UI placeholders are not data filter values")
    references = [plan["view"]["x"], *plan["view"]["y"]]
    if plan["view"].get("series"): references.append(plan["view"]["series"])
    if plan["view"].get("series") in plan["view"]["y"]:
        raise PlanError("view series must be a category column, not a y metric")
    if plan["view"].get("series") == plan["view"]["x"]:
        raise PlanError("view series must not duplicate the x column")
    if plan["view"]["chart"] in ("line", "slope") and plan["view"]["x"] in frame.columns:
        x_name = plan["view"]["x"]
        time_named = any(token in x_name.lower() for token in ("year", "date", "time", "month", "quarter"))
        if not time_named and not pd.api.types.is_numeric_dtype(frame[x_name]):
            raise PlanError("line and slope charts require an ordered numeric or time x column")
        if len(plan["view"]["y"]) != 1:
            raise PlanError("line and slope charts currently require exactly one y metric")
    participant_text = " ".join(str(value or "") for value in (
        plan["question"], plan["view"]["title"], plan["view"].get("note")))
    if re.search(r"\b(renderer|duckdb|sql|json|placeholder)\b", participant_text, flags=re.IGNORECASE):
        raise PlanError("participant-facing text contains implementation jargon")
    for insight in plan["insights"]:
        references += [insight[k] for k in ("metric", "label_column", "entity_column", "time_column") if insight.get(k)]
    missing = [name for name in references if name not in available]
    if missing: raise PlanError(f"view/insight names missing columns: {missing}")
    admitted = {str(c): set(frame[c].dropna().astype(str)) for c in frame.columns
                if not pd.api.types.is_numeric_dtype(frame[c])}
    for insight in plan["insights"]:
        column = insight.get("entity_column")
        for entity in insight.get("entities", []):
            if column in admitted and str(entity) not in admitted[column]:
                raise PlanError(f"absent {column} value: {entity}")


def aggregate(item: dict[str, Any]) -> str:
    name, column = quoted(item["name"]), quoted(item["column"])
    if item["fn"] == "weighted_percent":
        denominator = item.get("denominator_column")
        if not denominator: raise PlanError("weighted_percent needs denominator_column")
        return f"100.0*SUM({column})/NULLIF(SUM({quoted(denominator)}),0) AS {name}"
    function = {"mean": "AVG", "count": "COUNT"}.get(item["fn"], item["fn"].upper())
    return f"{function}({column}) AS {name}"


def execute(frame: pd.DataFrame, plan: dict[str, Any]) -> pd.DataFrame:
    db = duckdb.connect(":memory:")
    db.register("input_frame", frame)
    sql, params = "SELECT * FROM input_frame", []
    for step in plan["steps"]:
        op = step["op"]
        if op == "derive":
            a, b = quoted(step["numerator"]), quoted(step["denominator"])
            expression = (f"100.0*{a}/NULLIF({b},0)" if step["kind"] == "percent" else
                          f"{a}/NULLIF({b},0)" if step["kind"] == "ratio" else f"{a}-{b}")
            sql = f"SELECT *,{expression} AS {quoted(step['name'])} FROM ({sql}) q"
        elif op == "filter":
            column, cmp, value = quoted(step["column"]), step["cmp"], step["value"]
            if cmp == "in":
                if not isinstance(value, list): raise PlanError("in needs an array")
                condition = f"{column} IN ({','.join('?' for _ in value)})"; params += value
            elif cmp == "between":
                if not isinstance(value, list) or len(value) != 2: raise PlanError("between needs two values")
                condition = f"{column} BETWEEN ? AND ?"; params += value
            elif cmp == "contains":
                condition = f"LOWER(CAST({column} AS VARCHAR)) LIKE LOWER(?)"; params += [f"%{value}%"]
            else:
                operator = {"eq": "=", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">="}[cmp]
                condition = f"{column} {operator} ?"; params += [value]
            sql = f"SELECT * FROM ({sql}) q WHERE {condition}"
        elif op == "group":
            by = ",".join(map(quoted, step["by"])); selections = ([by] if by else []) + list(map(aggregate, step["aggregates"]))
            sql = f"SELECT {','.join(selections)} FROM ({sql}) q" + (f" GROUP BY {by}" if by else "")
        elif op == "sort": sql = f"SELECT * FROM ({sql}) q ORDER BY {quoted(step['column'])} {step['direction'].upper()}"
        elif op == "limit": sql = f"SELECT * FROM ({sql}) q LIMIT {int(step['rows'])}"
    try: result = db.execute(sql, params).fetchdf()
    except Exception as error: raise PlanError(f"DuckDB failed: {error}") from error
    finally: db.close()
    if result.empty: raise PlanError("plan produced no rows")
    return result


def check_conversation_constraints(messages: list[str], plan: dict[str, Any], result: pd.DataFrame) -> None:
    """Reject executable plans that silently ignore explicit durable filters.

    This is intentionally small and deterministic. It does not try to understand
    arbitrary language; it protects the benchmark's declared year-only/range
    phrasing. More constraint extractors must be frozen before additional cases.
    """
    text = "\n".join(messages).lower()
    for word, kind in (("lowest", "lowest"), ("highest", "highest")):
        if re.search(rf"\b{word}\b", text) and not any(item["kind"] == kind for item in plan["insights"]):
            raise PlanError(f"explicit {word} request requires a named {kind} insight")
    asks_for_pp_change = ("percentage point" in text or re.search(r"\bpp\b", text)) and re.search(r"\bchange\b", text)
    if asks_for_pp_change and not any(item["kind"] == "change" for item in plan["insights"]):
        raise PlanError("explicit percentage-point change request requires a change insight")
    if (re.search(r"\bwhy\b", text) or "don't guess reason" in text or "dont guess reason" in text) and not any(item["kind"] == "causal_limit" for item in plan["insights"]):
        raise PlanError("causal question requires a visible causal_limit insight")
    year_columns = [str(column) for column in result.columns if "year" in str(column).lower()]
    if not year_columns:
        return
    years = {int(value) for value in result[year_columns[0]].dropna()}
    ranges = re.findall(r"only\s+((?:19|20)\d{2})\s+(?:to|through|-)\s+((?:19|20)\d{2})", text)
    singles = re.findall(r"only\s+((?:19|20)\d{2})(?!\s+(?:to|through|-))", text)
    if ranges:
        start, end = map(int, ranges[-1]); allowed = set(range(start, end + 1))
        if not years or not years <= allowed:
            raise PlanError(f"durable year-range constraint ignored: expected {start}-{end}, got {sorted(years)}")
    elif singles:
        expected = int(singles[-1])
        if years != {expected}:
            raise PlanError(f"durable year-only constraint ignored: expected {expected}, got {sorted(years)}")


def compute_insights(plan: dict[str, Any], frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = [{str(k): clean(v) for k, v in row.items()} for row in frame.to_dict("records")]
    output = []
    for spec in plan["insights"]:
        kind = spec["kind"]
        if kind in ("highest", "lowest"):
            valid = [r for r in rows if isinstance(r.get(spec["metric"]), (int, float))]
            if valid:
                chosen = (max if kind == "highest" else min)(valid, key=lambda r: r[spec["metric"]])
                output.append({"kind": kind, "label": str(chosen[spec["label_column"]]),
                               "value": chosen[spec["metric"]], "metric": spec["metric"]})
        elif kind == "change":
            for entity in spec["entities"]:
                subset = [r for r in rows if str(r.get(spec["entity_column"])) == str(entity)]
                start = next((r for r in subset if str(r.get(spec["time_column"])) == str(spec["from"])), None)
                end = next((r for r in subset if str(r.get(spec["time_column"])) == str(spec["to"])), None)
                if start and end: output.append({"kind": kind, "label": str(entity), "value": end[spec["metric"]]-start[spec["metric"]], "unit": spec["unit"], "from": spec["from"], "to": spec["to"]})
        elif kind == "difference":
            subset = [r for r in rows if str(r.get(spec["time_column"])) == str(spec["time"])]
            found = [next((r for r in subset if str(r.get(spec["entity_column"])) == str(e)), None) for e in spec["entities"]]
            if all(found): output.append({"kind": kind, "label": f"{spec['entities'][1]} minus {spec['entities'][0]}", "value": found[1][spec["metric"]]-found[0][spec["metric"]], "unit": spec["unit"], "time": spec["time"]})
        elif kind == "causal_limit":
            output.append({"kind": kind, "label": "What this data cannot answer", "text": "This file shows differences and changes, but it has no explanatory variables and cannot establish why they occurred."})
    return output


def make_report(case: dict[str, Any], source: Path, plan: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    rows = [{str(k): clean(v) for k, v in row.items()} for row in frame.to_dict("records")]
    return {"schema_version": 1, "case_id": case["case_id"], "title": plan["view"]["title"],
            "question": plan["question"], "view": plan["view"], "columns": list(map(str, frame.columns)),
            "rows": rows, "insight_specs": plan["insights"], "insights": compute_insights(plan, frame),
            "source": {"file": source.name, "sha256": file_hash(source), "provenance": case["inputs"][0]["provenance"]}}


def write_csv(path: Path, report: dict[str, Any]) -> None:
    def safe(value: Any) -> Any:
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=report["columns"]); writer.writeheader()
        writer.writerows({key: safe(value) for key, value in row.items()} for row in report["rows"])


def render(report: dict[str, Any], output: Path) -> None:
    data = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    title = html.escape(report["title"])
    template_path = ROOT / "benchmarks/event/static-dashboard-template.html"
    template = template_path.read_text()
    output.write_text(template.replace("__DASHBOARD_TITLE__", title).replace("__DASHBOARD_DATA__", data))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True); parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True); parser.add_argument("--effort", choices=("low","medium","high","xhigh"), default="medium")
    parser.add_argument("--through-turn", type=int); parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--model-timeout-seconds", type=int, default=300)
    args = parser.parse_args()
    case = json.loads((args.case_dir / "case.json").read_text()); source = args.case_dir / case["inputs"][0]["path"]
    if source.suffix.lower() != ".csv": raise SystemExit("prototype accepts one CSV")
    frame = pd.read_csv(source); schema = json.loads(SCHEMA_PATH.read_text()); jsonschema.Draft202012Validator.check_schema(schema)
    data_profile = profile(frame, not args.schema_only); dump(args.output / "dataset-profile.json", data_profile)
    dump(args.output / "run-config.json", {"case_id": case["case_id"], "model": args.model, "effort": args.effort, "schema_only": args.schema_only, "source_sha256": file_hash(source)})
    messages, previous = [], None
    for turn in case["messages"][:args.through_turn or len(case["messages"])]:
        messages.append(turn["text"]); turn_dir = args.output / f"turn-{turn['turn']}"
        prompt = make_prompt(case, data_profile, messages, previous); dump(turn_dir / "plan-request.json", {"model": args.model, "effort": args.effort, "prompt": prompt})
        attempts, attempt_prompt, plan, result = [], prompt, None, None
        for attempt in range(1, 4):
            try:
                candidate, api = call_model(args.model, args.effort, attempt_prompt, schema, args.model_timeout_seconds)
            except Exception as error:
                failure = {"attempt": attempt, "request_error": f"{type(error).__name__}: {error}"}
                attempts.append(failure); dump(turn_dir / f"plan-attempt-{attempt}.json", failure)
                dump(turn_dir / "plan-error.json", {"status": "model_request_failed", "attempts": attempts})
                raise
            record = {"attempt": attempt, "plan": candidate, "api": api}
            try:
                jsonschema.validate(candidate, schema); bind(candidate, frame); candidate_result = execute(frame, candidate)
                check_conversation_constraints(messages, candidate, candidate_result)
            except Exception as error:
                record["validation_error"] = f"{type(error).__name__}: {error}"; attempts.append(record)
                dump(turn_dir / f"plan-attempt-{attempt}.json", record)
                if attempt == 3: raise
                attempt_prompt = repair_prompt(prompt, candidate, error); continue
            attempts.append(record); dump(turn_dir / f"plan-attempt-{attempt}.json", record)
            plan, result = candidate, candidate_result; break
        assert plan is not None and result is not None
        dump(turn_dir / "plan-response.json", {"plan": plan, "api": attempts[-1]["api"], "attempts": attempts})
        dump(turn_dir / "validated-plan.json", plan)
        report = make_report(case, source, plan, result); dump(turn_dir / "insight-report.json", report)
        workspace = turn_dir / "workspace"; workspace.mkdir(parents=True, exist_ok=True); write_csv(workspace / "all-result-rows.csv", report); render(report, workspace / "index.html")
        previous = plan; print(json.dumps({"turn": turn["turn"], "rows": len(result), "chart": plan["view"]["chart"], "attempts": len(attempts), "seconds": sum(a["api"]["duration_seconds"] for a in attempts), "workspace": str(workspace)}), flush=True)
    return 0


if __name__ == "__main__": raise SystemExit(main())
