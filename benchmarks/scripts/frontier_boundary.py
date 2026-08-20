"""Value-free allowlist boundary for an optional frontier layout planner."""

from __future__ import annotations

import json
from typing import Any


ALLOWED_CHARTS = ["bar", "grouped_bar", "line", "slope", "scatter", "heatmap"]


def semantic_role(name: str, kind: str) -> str:
    lowered = name.casefold()
    if any(token in lowered for token in ("year", "date", "month", "quarter", "period")):
        return "time"
    if kind in {"integer", "number"}:
        return "measure"
    if any(token in lowered for token in ("source", "url", "file", "sheet", "page")):
        return "provenance"
    return "dimension"


def serialize_frontier_layout_request(question: str, columns: list[dict[str, str]]) -> dict[str, Any]:
    """Return only user prose, schema roles and the renderer contract.

    No caller-supplied rows, aggregates, samples, cardinalities or extrema are
    accepted by this function, so they cannot accidentally cross the boundary.
    """
    schema = [
        {
            "name": column["name"],
            "type": column["type"],
            "role": semantic_role(column["name"], column["type"]),
        }
        for column in columns
    ]
    return {
        "schema_version": 1,
        "task": "Choose a declarative desktop dashboard layout. Do not calculate or invent values.",
        "user_question": question,
        "result_schema_no_values": schema,
        "layout_contract": {
            "allowed_charts": ALLOWED_CHARTS,
            "required": ["title", "chart", "x", "y", "unit", "note"],
            "optional": ["series"],
            "rules": [
                "Use only supplied column names.",
                "Put measures in y, never in series.",
                "Use a time field on x for a trend.",
                "Return a specification only; local code hydrates real values.",
                "Do not include HTML, JavaScript, URLs, data rows or example values.",
            ],
        },
    }


def serialized_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def find_forbidden_values(payload: dict[str, Any], forbidden: list[Any]) -> list[str]:
    text = serialized_text(payload).casefold()
    leaks = []
    for value in forbidden:
        rendered = str(value).strip()
        if rendered and rendered.casefold() in text:
            leaks.append(rendered)
    return sorted(set(leaks))
