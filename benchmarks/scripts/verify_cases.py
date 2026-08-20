#!/usr/bin/env python3
"""Verify benchmark case manifests, hashes and simple smoke oracles."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_case(case_dir: Path, fix: bool) -> list[str]:
    errors: list[str] = []
    manifest_path = case_dir / "case.json"
    manifest = json.loads(manifest_path.read_text())
    case_schema = json.loads((ROOT / "schemas/case.schema.json").read_text())
    try:
        jsonschema.validate(manifest, case_schema)
    except jsonschema.ValidationError as error:
        errors.append(f"{manifest.get('case_id', case_dir.name)}: schema: {error.message}")

    for item in manifest["inputs"]:
        input_path = case_dir / item["path"]
        if not input_path.is_file():
            errors.append(f"{manifest['case_id']}: missing {item['path']}")
            continue
        actual_hash = sha256(input_path)
        actual_bytes = input_path.stat().st_size
        if fix:
            item["sha256"] = actual_hash
            item["bytes"] = actual_bytes
        else:
            if item["sha256"] != actual_hash:
                errors.append(f"{manifest['case_id']}: hash mismatch for {item['path']}")
            if item["bytes"] != actual_bytes:
                errors.append(f"{manifest['case_id']}: byte count mismatch for {item['path']}")

    oracle_path = case_dir / manifest["oracle"]
    if not oracle_path.is_file():
        errors.append(f"{manifest['case_id']}: missing oracle {manifest['oracle']}")

    if manifest["case_id"] == "smoke-001" and oracle_path.is_file():
        oracle = json.loads(oracle_path.read_text())
        csv_path = case_dir / "inputs/district_immunisation.csv"
        with csv_path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        calculated = {
            row["district"]: round(
                int(row["children_fully_immunised"]) / int(row["children_due"]) * 100,
                1,
            )
            for row in rows
            if row["year"] == "2023"
        }
        if calculated != oracle["expected_percentages"]["2023"]:
            errors.append("smoke-001: 2023 oracle does not match CSV")

    if manifest["case_id"] == "dev-csv-health-001" and oracle_path.is_file():
        oracle = json.loads(oracle_path.read_text())
        csv_path = case_dir / "inputs/anc4_coverage.csv"
        with csv_path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        calculated: dict[str, dict[str, float]] = {}
        for row in rows:
            if int(row["year"]) not in oracle["allowed_years_after_turn_2"]:
                continue
            calculated.setdefault(row["district"], {})[row["year"]] = round(
                int(row["anc4_completed"])
                / int(row["pregnancies_registered"])
                * 100,
                1,
            )
        if calculated != oracle["expected_percentages"]:
            errors.append("dev-csv-health-001: percentages do not match CSV")
        for district in ("Gaya", "Nalanda"):
            change = round(
                calculated[district]["2023"] - calculated[district]["2021"], 1
            )
            expected = oracle["turn_3"][
                f"{district}_change_2021_to_2023_percentage_points"
            ]
            if change != expected:
                errors.append(
                    f"dev-csv-health-001: {district} percentage-point change mismatch"
                )

    if fix and not errors:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="refresh input hashes and byte counts")
    args = parser.parse_args()

    errors: list[str] = []
    for manifest in sorted((ROOT / "cases").glob("*/case.json")):
        errors.extend(verify_case(manifest.parent, args.fix))

    if errors:
        for error in errors:
            print(error)
        return 1
    print("benchmark cases verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
