#!/usr/bin/env python3
"""Screen semantic critics against fixed, value-redacted plan decisions."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "benchmarks/scripts/run_split_pipeline.py"
SPEC = importlib.util.spec_from_file_location("split_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def mutate(plan: dict[str, Any], name: str, frame: Any) -> dict[str, Any]:
    candidate = copy.deepcopy(plan)
    if name == "none":
        return candidate
    if name == "drop_last_insight":
        if not candidate["insights"]:
            raise ValueError("drop_last_insight requires an insight")
        candidate["insights"].pop()
    elif name == "drop_all_insights":
        if not candidate["insights"]:
            raise ValueError("drop_all_insights requires an insight")
        candidate["insights"] = []
    elif name == "remove_filters":
        candidate["steps"] = [step for step in candidate["steps"] if step["op"] != "filter"]
    elif name == "allow_causal_claim":
        candidate["insights"] = [item for item in candidate["insights"] if item["kind"] != "causal_limit"]
        candidate["interpretation_guard"] = {"can_explain_cause": True, "caveat": None}
        candidate["view"]["note"] = "The observed differences show which intervention should be used."
    elif name == "hardcode_first_year":
        year_column = next(column for column in frame.columns if "year" in str(column).lower())
        value = sorted(frame[year_column].dropna().unique())[-1]
        if hasattr(value, "item"):
            value = value.item()
        candidate["steps"].append({"op": "filter", "column": str(year_column), "cmp": "eq", "value": value})
    elif name == "replace_first_derived_rate_with_numerator":
        derived = next(step for step in candidate["steps"] if step["op"] == "derive" and step["kind"] == "percent")
        old_metric, new_metric = derived["name"], derived["numerator"]
        candidate["steps"].remove(derived)
        candidate["view"]["y"] = [new_metric if metric == old_metric else metric for metric in candidate["view"]["y"]]
        candidate["view"]["unit"] = "number"
        candidate["question"] = f"Compare the number of {new_metric.replace('_', ' ')} across the requested groups and times."
        candidate["view"]["title"] = f"{new_metric.replace('_', ' ').title()} by Group and Time"
        for insight in candidate["insights"]:
            if insight.get("metric") == old_metric:
                insight["metric"] = new_metric
                insight["unit"] = "number"
    elif name == "align_filters_to_insight_time":
        timed = next(item for item in candidate["insights"] if "time" in item)
        time_column, value = timed["time_column"], timed["time"]
        for step in candidate["steps"]:
            if step["op"] == "filter" and step["column"] == time_column:
                step.update({"cmp": "eq", "value": value})
                break
        else:
            candidate["steps"].append({"op": "filter", "column": time_column, "cmp": "eq", "value": value})
    elif name == "drop_last_measure_and_insight":
        if len(candidate["view"]["y"]) < 2:
            raise ValueError("drop_last_measure_and_insight requires two measures")
        removed = candidate["view"]["y"].pop()
        candidate["insights"] = [item for item in candidate["insights"] if item.get("metric") != removed]
    else:
        raise ValueError(f"unknown mutation {name}")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("benchmarks/critic-replay-v1/manifest.json"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh"), default="low")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--early-stop-errors", type=int, default=3)
    parser.add_argument("--only", action="append", default=[], help="Run only the named sample; repeatable")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    records: list[dict[str, Any]] = []
    mistakes = 0

    selected = [sample for sample in manifest["samples"] if not args.only or sample["id"] in args.only]
    for sample in selected:
        case_dir = Path(sample["case_dir"])
        baseline = Path(sample["baseline_run"])
        case = json.loads((case_dir / "case.json").read_text())
        source = case_dir / case["inputs"][0]["path"]
        frame, data_profile, _metadata = RUNNER.load_source(source, True)
        turn = int(sample["turn"])
        messages = [item["text"] for item in case["messages"][:turn]]
        previous = json.loads((baseline / f"turn-{turn - 1}/validated-plan.json").read_text()) if turn > 1 else None
        original = json.loads((baseline / f"turn-{turn}/validated-plan.json").read_text())
        candidate = mutate(original, sample["mutation"], frame)
        RUNNER.bind(candidate, frame)
        result = RUNNER.execute(frame, candidate)
        record = {
            "id": sample["id"], "case_id": case["case_id"], "turn": turn,
            "mutation": sample["mutation"], "expected_accept": sample["expected_accept"],
            "candidate": candidate,
        }
        try:
            review, api, prompt = RUNNER.call_critic(
                args.model, args.effort, messages, data_profile, previous, candidate, result,
                args.timeout_seconds,
            )
            record.update({"review": review, "api": api, "critic_request": {
                "raw_rows_included": False,
                "min_max_or_admitted_values_included": False,
                "prompt": prompt,
            }})
            record["passed"] = review["accepted"] == sample["expected_accept"]
        except Exception as error:
            record.update({"request_error": f"{type(error).__name__}: {error}", "passed": False})
        records.append(record)
        if not record["passed"]:
            mistakes += 1
        print(json.dumps({
            "id": record["id"], "expected": record["expected_accept"],
            "actual": (record.get("review") or {}).get("accepted"), "passed": record["passed"],
            "mistakes": mistakes,
        }), flush=True)
        if mistakes >= args.early_stop_errors:
            break

    calls = [record["api"] for record in records if record.get("api")]
    summary = {
        "schema_version": 1, "model": args.model, "effort": args.effort,
        "manifest": str(args.manifest), "samples_planned": len(selected),
        "samples_run": len(records), "passed": sum(record["passed"] for record in records),
        "mistakes": mistakes, "early_stopped": len(records) < len(selected),
        "duration_seconds": round(sum(api.get("duration_seconds", 0) for api in calls), 3),
        "cost_usd": round(sum((api.get("usage") or {}).get("cost", 0) or 0 for api in calls), 12),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in (
        "model", "samples_run", "passed", "mistakes", "early_stopped",
        "duration_seconds", "cost_usd",
    )}))
    return 0 if mistakes == 0 and len(records) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
