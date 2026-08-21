#!/usr/bin/env python3
"""Aggregate secret-free OpenRouter proxy records into replay evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.log.read_text().splitlines() if line.strip()]
    completed = [record for record in records if record.get("status") == 200]
    providers: Counter[str] = Counter()
    models: Counter[str] = Counter()
    generation_ids: list[str] = []
    totals: dict[str, float] = {
        "cost_usd": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "duration_seconds": 0.0,
    }
    for record in completed:
        for provider in record.get("providers", []):
            providers[provider] += 1
        for model in record.get("response_models", []):
            models[model] += 1
        generation_ids.extend(record.get("generation_ids", []))
        usage: dict[str, Any] = record.get("usage") or {}
        totals["cost_usd"] += float(usage.get("cost") or 0)
        totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        totals["reasoning_tokens"] += int(
            (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
        )
        totals["cached_tokens"] += int(
            (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        )
        totals["duration_seconds"] += float(record.get("duration_seconds") or 0)
    totals["cost_usd"] = round(totals["cost_usd"], 8)
    totals["duration_seconds"] = round(totals["duration_seconds"], 3)
    result = {
        "schema_version": 1,
        "request_count": len(records),
        "successful_request_count": len(completed),
        "failed_request_count": len(records) - len(completed),
        "reasoning_efforts": sorted(
            {record.get("reasoning_effort_injected") for record in records}
        ),
        "requested_models": sorted({record.get("requested_model") for record in records}),
        "resolved_models": dict(models),
        "providers": dict(providers),
        "generation_ids": generation_ids,
        "totals": totals,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
