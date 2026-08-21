#!/usr/bin/env python3
"""PII detection engines and a benchmark over benchmarks/pii/corpus.

Engines are deliberately small and CPU-bound so the result says something about
an 8 GB (or smaller) laptop. Every engine exposes the same call:

    spans = engine(text) -> [(start, end, label, score)]

Tabular files are scored at column level (the redaction unit for spreadsheets),
free text at span level with overlap matching. Run:

    .venv-pii/bin/python benchmarks/pii/detect.py --engine regex --engine gliner:knowledgator/gliner-pii-edge-v1.0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import resource
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks" / "pii" / "corpus"
PII_CLASSES = {
    "person_name", "phone", "email", "aadhaar", "pan", "bank_account", "ifsc", "upi_id",
    "dob", "age", "address", "village", "gps", "caste_category", "ration_card", "voter_id",
    "vehicle_number", "free_text_with_pii",
}
NON_PII = {"none", "record_id_non_pii"}
Span = tuple[int, int, str, float]

# ----------------------------------------------------------------- regex engine
def verhoeff_ok(number: str) -> bool:
    d = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],
         [4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],
         [8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]]
    p = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],
         [9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = d[c][p[i % 8][int(ch)]]
    return c == 0


REGEXES: list[tuple[str, re.Pattern[str], Callable[[str], bool] | None]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None),
    ("aadhaar", re.compile(r"(?<!\d)([2-9]\d{3}[ -]?\d{4}[ -]?\d{4})(?!\d)"),
     lambda s: verhoeff_ok(re.sub(r"\D", "", s))),
    ("pan", re.compile(r"(?<![A-Z])[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z](?![A-Z])"), None),
    ("ifsc", re.compile(r"(?<![A-Z])[A-Z]{4}0[A-Z0-9]{6}(?![A-Z0-9])"), None),
    ("upi_id", re.compile(r"\b[\w.-]{2,}@(?:ybl|okaxis|oksbi|okicici|okhdfcbank|paytm|upi|apl|ibl|axl|icici|sbi|hdfcbank)\b"), None),
    ("phone", re.compile(r"(?<!\d)(?:\+91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)"), None),
    ("vehicle_number", re.compile(r"\b[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4}\b"), None),
    ("voter_id", re.compile(r"\b[A-Z]{3}\d{7}\b"), None),
    ("gps", re.compile(r"(?<![\d.])-?\d{1,2}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}(?![\d.])"), None),
    ("dob", re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"), None),
]


def regex_engine(text: str) -> list[Span]:
    spans: list[Span] = []
    for label, pattern, check in REGEXES:
        for match in pattern.finditer(text):
            if check and not check(match.group(0)):
                continue
            spans.append((match.start(), match.end(), label, 1.0))
    return spans


def long_digits_engine(text: str) -> list[Span]:
    """User-selectable blunt rule: any run of 8+ digits (optionally spaced) is private."""
    return [(m.start(), m.end(), "long_number", 1.0)
            for m in re.finditer(r"(?<!\d)(?:\d[ -]?){8,}\d(?!\d)", text)]


# ---------------------------------------------------------------- gliner engine
GLINER_LABELS = [
    "person name", "phone number", "email address", "aadhaar number", "pan card number",
    "bank account number", "ifsc code", "upi id", "date of birth", "age", "street address",
    "village or town", "gps coordinates", "caste or religion", "ration card number",
    "voter id", "vehicle registration number",
]
GLINER_TO_CLASS = {
    "person name": "person_name", "phone number": "phone", "email address": "email",
    "aadhaar number": "aadhaar", "pan card number": "pan", "bank account number": "bank_account",
    "ifsc code": "ifsc", "upi id": "upi_id", "date of birth": "dob", "age": "age",
    "street address": "address", "village or town": "village", "gps coordinates": "gps",
    "caste or religion": "caste_category", "ration card number": "ration_card", "voter id": "voter_id",
    "vehicle registration number": "vehicle_number",
}


def make_gliner(model_id: str, threshold: float = 0.4, chunk_chars: int = 1500) -> Callable[[str], list[Span]]:
    import torch
    from gliner import GLiNER
    torch.set_num_threads(int(os.environ.get("PII_THREADS", "4")))
    model = GLiNER.from_pretrained(model_id, map_location="cpu")
    model.eval()

    def run(text: str) -> list[Span]:
        spans: list[Span] = []
        # chunk on line boundaries so offsets stay exact
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_chars)
            if end < len(text):
                cut = text.rfind("\n", start, end)
                if cut > start:
                    end = cut + 1
            piece = text[start:end]
            for ent in model.predict_entities(piece, GLINER_LABELS, threshold=threshold):
                spans.append((start + ent["start"], start + ent["end"],
                              GLINER_TO_CLASS.get(ent["label"], ent["label"]), float(ent["score"])))
            start = end
        return spans
    return run


# -------------------------------------------------------------- presidio engine
def make_presidio() -> Callable[[str], list[Span]]:
    from presidio_analyzer import AnalyzerEngine
    analyzer = AnalyzerEngine()
    mapping = {"PERSON": "person_name", "PHONE_NUMBER": "phone", "EMAIL_ADDRESS": "email",
               "IN_AADHAAR": "aadhaar", "IN_PAN": "pan", "IN_VOTER": "voter_id", "IN_VEHICLE_REGISTRATION": "vehicle_number",
               "LOCATION": "village", "DATE_TIME": "dob", "IBAN_CODE": "bank_account", "CREDIT_CARD": "bank_account"}

    def run(text: str) -> list[Span]:
        return [(r.start, r.end, mapping.get(r.entity_type, r.entity_type.lower()), float(r.score))
                for r in analyzer.analyze(text=text, language="en")]
    return run


# ------------------------------------------------------------------ llm engine
def make_llm(model: str, endpoint: str = "https://openrouter.ai/api/v1") -> Callable[[str], list[Span]]:
    """Remote or DGX 27B as a span extractor. Only for synthetic/public text."""
    sys.path.insert(0, str(ROOT / "benchmarks" / "scripts"))
    from run_v2_query_gate import endpoint_json  # noqa: E402
    key = json.loads(Path("~/.config/idlisseus/openrouter.json").expanduser().read_text())["api_key"] \
        if "openrouter" in endpoint else None
    classes = sorted(PII_CLASSES - {"free_text_with_pii"})

    def run(text: str) -> list[Span]:
        spans: list[Span] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + 6000)
            if end < len(text):
                cut = text.rfind("\n", start, end)
                if cut > start:
                    end = cut + 1
            piece = text[start:end]
            prompt = (
                "Extract every personally identifying or sensitive value from the text below, Indian context. "
                f"Classes: {', '.join(classes)}. Return ONLY a JSON array of objects "
                '{"text": exact substring, "class": class}. Include every occurrence, names of people (any script or casing), '
                "phone numbers in any format, Aadhaar/PAN/bank/voter/ration identifiers, emails, UPI ids, dates of birth, ages, "
                "villages/towns/addresses, GPS pairs, caste or religion labels, vehicle numbers. Do not include amounts, counts, percentages, scheme names.\n\nTEXT:\n" + piece
            )
            body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0,
                    "max_tokens": 8000, "reasoning": {"enabled": False}}
            raw = endpoint_json(endpoint.rstrip("/") + "/chat/completions", body, 180, key)
            content = raw["choices"][0]["message"].get("content") or "[]"
            match = re.search(r"\[.*\]", content, flags=re.S)
            try:
                items = json.loads(match.group(0)) if match else []
            except json.JSONDecodeError:
                items = []
            for item in items:
                value = str(item.get("text", ""))
                if not value:
                    continue
                for m in re.finditer(re.escape(value), piece):
                    spans.append((start + m.start(), start + m.end(), str(item.get("class", "unknown")), 1.0))
            start = end
        return spans
    return run


def build_engine(spec: str) -> Callable[[str], list[Span]]:
    if spec.startswith("textv2:"):
        return make_text_v2(spec.split(":", 1)[1])
    if spec == "regex":
        return regex_engine
    if spec == "regex+digits":
        return lambda t: regex_engine(t) + long_digits_engine(t)
    if spec.startswith("gliner:"):
        return make_gliner(spec.split(":", 1)[1])
    if spec == "presidio":
        return make_presidio()
    if spec.startswith("llm:"):
        return make_llm(spec.split(":", 1)[1])
    raise ValueError(spec)


# -------------------------------------------------------------------- scoring
def overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def score_text(gold: list[dict[str, Any]], pred: list[Span]) -> dict[str, Any]:
    gold_hit = [any(overlap((g["start"], g["end"]), (p[0], p[1])) for p in pred) for g in gold]
    pred_hit = [any(overlap((g["start"], g["end"]), (p[0], p[1])) for g in gold) for p in pred]
    per_class: dict[str, list[int]] = {}
    for g, hit in zip(gold, gold_hit):
        per_class.setdefault(g["class"], [0, 0])
        per_class[g["class"]][0] += hit
        per_class[g["class"]][1] += 1
    missed = [g["text"] for g, hit in zip(gold, gold_hit) if not hit][:15]
    return {
        "gold_spans": len(gold), "pred_spans": len(pred),
        "recall": round(sum(gold_hit) / len(gold), 3) if gold else None,
        "precision": round(sum(pred_hit) / len(pred), 3) if pred else None,
        "per_class_recall": {k: f"{v[0]}/{v[1]}" for k, v in sorted(per_class.items())},
        "missed_examples": missed,
    }


def load_table(path: Path) -> dict[str, pd.DataFrame]:
    if path.suffix == ".csv":
        return {"": pd.read_csv(path, dtype=str, keep_default_na=False)}
    return {name: frame for name, frame in pd.read_excel(path, sheet_name=None, dtype=str).items()}


def column_verdict(engine: Callable[[str], list[Span]], values: list[str], min_fraction: float) -> tuple[bool, str | None, float]:
    """Run the engine on each sampled cell separately; a column is PII when at least
    min_fraction of non-empty sampled cells contain a detected entity covering most of the cell
    (identifier columns) or any entity at all (free-text columns)."""
    hits = 0
    labels: dict[str, int] = {}
    sampled = [v for v in values if v.strip()]
    for value in sampled:
        spans = engine(value)
        if spans:
            hits += 1
            best = max(spans, key=lambda s: s[1] - s[0])
            labels[best[2]] = labels.get(best[2], 0) + 1
    fraction = hits / len(sampled) if sampled else 0.0
    label = max(labels, key=labels.get) if labels else None
    return fraction >= min_fraction, label, round(fraction, 3)


def score_table(engine: Callable[[str], list[Span]], path: Path, gold: dict[str, Any], sample: int,
                min_fraction: float) -> dict[str, Any]:
    frames = load_table(path)
    rows: list[dict[str, Any]] = []
    for sheet, frame in frames.items():
        for column in frame.columns:
            truth = gold.get(str(column))
            truth_set = set(truth) if isinstance(truth, list) else ({truth} if truth else set())
            is_pii = bool(truth_set - NON_PII)
            values = frame[column].dropna().astype(str)
            values = values[values.str.strip() != ""].drop_duplicates().head(sample).tolist()
            flagged, label, fraction = column_verdict(engine, values, min_fraction)
            rows.append({"sheet": sheet, "column": str(column), "gold": truth, "gold_pii": is_pii,
                         "flagged": flagged, "label": label, "fraction": fraction})
        break  # sheets share structure; one sheet is enough for column verdicts
    pii_cols = [r for r in rows if r["gold_pii"]]
    clean_cols = [r for r in rows if not r["gold_pii"]]
    return {
        "columns": len(rows),
        "pii_columns": len(pii_cols),
        "recall": round(sum(r["flagged"] for r in pii_cols) / len(pii_cols), 3) if pii_cols else None,
        "false_positive_columns": [r["column"] for r in clean_cols if r["flagged"]],
        "missed_columns": [f'{r["column"]} ({r["gold"]})' for r in pii_cols if not r["flagged"]],
        "detail": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", action="append", required=True)
    parser.add_argument("--sample", type=int, default=25, help="distinct cells sampled per column")
    parser.add_argument("--min-fraction", type=float, default=0.2)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "runs" / "2026-08-21-pii-detection" / "results.json")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()
    results: dict[str, Any] = {}
    for spec in args.engine:
        t0 = time.monotonic()
        engine = build_engine(spec)
        load_seconds = round(time.monotonic() - t0, 2)
        per_file: dict[str, Any] = {}
        for path in sorted(CORPUS.iterdir()):
            if path.suffix not in {".csv", ".xlsx", ".txt"} or path.name == "README.md":
                continue
            if args.only and path.stem not in args.only:
                continue
            started = time.monotonic()
            if path.suffix == ".txt":
                gold = json.loads((CORPUS / f"{path.stem}.spans.json").read_text())
                text = path.read_text()
                pred = engine(text)
                record = score_text(gold, pred)
                record["chars"] = len(text)
            else:
                gold = json.loads((CORPUS / f"{path.stem}.columns.json").read_text())
                record = score_table(engine, path, gold, args.sample, args.min_fraction)
            record["seconds"] = round(time.monotonic() - started, 2)
            per_file[path.name] = record
            print(json.dumps({"engine": spec, "file": path.name, "recall": record.get("recall"),
                              "precision": record.get("precision"), "fp_cols": record.get("false_positive_columns"),
                              "seconds": record["seconds"]}), flush=True)
        results[spec] = {
            "load_seconds": load_seconds,
            "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
            "threads": os.environ.get("PII_THREADS", "4"),
            "files": per_file,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(args.output.read_text()) if args.output.exists() else {}
    existing.update(results)
    args.output.write_text(json.dumps(existing, indent=2))
    return 0



# ------------------------------------------------- composed text engine (v2)
CHAT_LINE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}(?::\d{2})?(?: [AP]M)?\]? ?- )([^:\n]{2,60}):", re.M)


def make_text_v2(base_spec: str) -> Callable[[str], list[Span]]:
    """Structural chat-sender rule + regex validators + span model on original AND
    title-cased text (same offsets) + propagation of every detected name/place to all
    of its case-insensitive occurrences in the document."""
    base = build_engine(base_spec)

    def run(text: str) -> list[Span]:
        spans: list[Span] = list(regex_engine(text))
        for m in CHAT_LINE.finditer(text):
            spans.append((m.start(2), m.end(2), "person_name", 1.0))
        spans += base(text)
        spans += base(text.title())
        found = {text[s:e] for s, e, lab, _ in spans if lab in {"person_name", "village", "address"} and e - s >= 4}
        for value in found:
            for m in re.finditer(re.escape(value), text, flags=re.I):
                spans.append((m.start(), m.end(), "person_name", 0.9))
        return spans
    return run



if __name__ == "__main__":
    raise SystemExit(main())
