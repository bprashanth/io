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
    """Return only a value-free intent outline, schema roles and renderer contract.

    No caller-supplied rows, aggregates, samples, cardinalities or extrema are
    accepted by this function. The raw question is not serialized because it
    can contain values copied from the participant's data.
    """
    lowered = question.casefold()
    intents = []
    for intent, markers in (
        ("trend", ("trend", "over time", "year by year")),
        ("change", ("change", "difference", "increase", "decrease", "growth")),
        ("comparison", ("compare", "comparison", "versus", " vs ")),
        ("ranking", ("highest", "lowest", "top", "bottom", "rank", "order")),
        ("distribution", ("distribution", "spread", "histogram")),
        ("relationship", ("correlation", "relationship", "scatter")),
    ):
        if any(marker in lowered for marker in markers):
            intents.append(intent)
    if not intents:
        intents.append("overview")
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
        "intent_outline_no_values": {
            "analysis": intents,
            "source_visible": any(term in lowered for term in ("source", "citation", "cite")),
            "download_required": any(term in lowered for term in ("download", "export")),
        },
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
