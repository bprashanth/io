#!/usr/bin/env python3
"""Sheltered-mode conversation: pseudonymise locally, query a remote model with tokens,
execute locally, rehydrate, and carry follow-ups that mention people by name.

Every outbound payload is checked against the local pseudonym map: if any real
display value appears in it the run aborts. This is the leak test.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "scripts"))
sys.path.insert(0, str(ROOT / "benchmarks" / "pii"))
from run_v2_query_gate import call_model, extract_sql, write_json, known_categories, make_shell_prompt  # noqa: E402
from detect import build_engine  # noqa: E402
from columns import classify_columns  # noqa: E402
from pseudonymize import PseudonymMap, pseudonymise_frame, redact_question  # noqa: E402


def leak_check(payload: str, pmap: PseudonymMap) -> None:
    for token, value in pmap.display.items():
        if token.split("_")[0] in {"AGE", "NUMBER"}:
            continue
        if len(value) >= 4 and re.search(re.escape(value), payload, flags=re.I):
            raise SystemExit(f"LEAK: {value!r} ({token}) found in outbound payload")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--sheet")
    parser.add_argument("--question", action="append", required=True)
    parser.add_argument("--model", default="qwen/qwen3.5-27b")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--span-engine", default="gliner:knowledgator/gliner-pii-edge-v1.0")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    key = json.loads(Path("~/.config/idlisseus/openrouter.json").expanduser().read_text())["api_key"]

    frame = pd.read_csv(args.data) if args.data.suffix == ".csv" else pd.read_excel(args.data, sheet_name=args.sheet or 0)
    engine = build_engine(args.span_engine)
    classes = classify_columns(frame, engine)
    write_json(args.output / "column-classes.json", classes)
    pmap = PseudonymMap(args.output / "pseudonym-map-local-only.json")
    shadow = pseudonymise_frame(frame, {c: v["class"] for c, v in classes.items()}, pmap, engine)
    pmap.save()
    shadow.to_csv(args.output / "shadow-sent-to-model.csv", index=False)

    db = duckdb.connect(":memory:")
    table = re.sub(r"[^a-z0-9]+", "_", args.data.stem.casefold()).strip("_")
    db.register("shadow_frame", shadow)
    db.execute(f'CREATE TABLE "{table}" AS SELECT * FROM shadow_frame')
    cols = db.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position", [table]).fetchall()
    schema = f'CREATE TABLE "{table}" (' + ", ".join(f'"{c}" {t}' for c, t in cols) + ");"
    categories = known_categories(db, {"tables": [{"name": table}]})

    transcript = []
    prior: list[dict] = []
    for turn, question in enumerate(args.question, 1):
        red = redact_question(question, pmap, engine)
        record = {"turn": turn, "question_local": question, "question_sent": red["redacted"], "ambiguous": red["ambiguous"]}
        if red["ambiguous"]:
            record["status"] = "needs_clarification"
            transcript.append(record)
            print(json.dumps(record, ensure_ascii=False))
            continue
        prompt = make_shell_prompt(red["redacted"], schema, categories)
        if prior:
            prompt = prompt.replace("CURRENT QUESTION:", "PRIOR TURNS:\n" + json.dumps(prior[-3:]) + "\n\nCURRENT QUESTION:")
        leak_check(prompt, pmap)
        response, api = call_model("https://openrouter.ai/api/v1", args.model, prompt, 120, key, 2048, "none", 0.0)
        sql = extract_sql(response)
        cur = db.execute(sql)
        out_cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        shown = [[pmap.rehydrate(v) if isinstance(v, str) else v for v in r] for r in rows][:10]
        record.update({"status": "ok", "sql": sql, "columns": out_cols, "rows_tokens": [list(r) for r in rows[:5]],
                       "rows_rehydrated_local": shown, "model": api.get("model"), "seconds": api.get("duration_seconds")})
        prior.append({"question": red["redacted"], "sql": sql, "output_columns": out_cols})
        transcript.append(record)
        print(json.dumps(record, ensure_ascii=False, default=str))
    write_json(args.output / "transcript.json", transcript)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
