#!/usr/bin/env python3
"""Verify the connector-backed split Census case against the frozen oracle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("prepared_case", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    oracle = json.loads(Path("benchmarks/cases/dev-web-census-001/oracle.json").read_text())
    manifest = json.loads((args.prepared_case / "discovery-manifest.json").read_text())
    reports = {turn: json.loads((args.run_dir / f"turn-{turn}/insight-report.json").read_text()) for turn in range(1, 5)}
    checks: list[dict[str, object]] = []
    failures: list[str] = []

    workbook = args.prepared_case / "source-data/A01_2011.xlsx"
    connector_passed = (
        manifest["stage"] == "bounded official-source connector after URL discovery"
        and manifest["download_http_status"] == 200
        and digest(workbook) == manifest["raw_workbook_sha256"]
        and urlparse(manifest["download_url"]).hostname in oracle["citation"]["accepted_official_domains"]
        and manifest["publisher"] == oracle["citation"]["required_publisher"]
    )
    checks.append({"name": "official-connector-live-download-and-retained-hash", "passed": connector_passed})
    if not connector_passed:
        failures.append("official connector manifest, host, publisher, status or retained hash is invalid")

    expected = oracle["expected_population"]
    for turn in range(1, 5):
        report = reports[turn]
        values = {row["district"]: int(row["population"]) for row in report["rows"]}
        row_passed = len(report["rows"]) == 3 and values == expected
        traceable = all(
            int(row["census_year"]) == oracle["year"]
            and row["publisher"] == oracle["citation"]["required_publisher"]
            and urlparse(row["source_url"]).hostname in oracle["citation"]["accepted_official_domains"]
            and "A-01" in row["source_table"]
            for row in report["rows"]
        )
        checks.append({"name": f"turn-{turn}-exact-values-and-official-provenance", "passed": row_passed and traceable})
        if not row_passed or not traceable:
            failures.append(f"turn {turn} values, scope or official provenance differ from the oracle")
        browser = json.loads((args.run_dir / f"turn-{turn}/browser/browser-check.json").read_text())
        links_passed = bool(browser["outbound_links"]) and all(
            urlparse(url).hostname in oracle["citation"]["accepted_official_domains"]
            for url in browser["outbound_links"]
        )
        checks.append({"name": f"turn-{turn}-browser-and-official-links", "passed": browser["passed"] and links_passed})
        if not browser["passed"] or not links_passed:
            failures.append(f"turn {turn} browser failed or exposes a non-official link")

    ranked = [item for item in reports[2]["insights"] if item["kind"] == "highest"]
    difference = [item for item in reports[2]["insights"] if item["kind"] == "difference"]
    answer_passed = (
        bool(ranked and ranked[0]["label"] == oracle["turn_2"]["largest"])
        and bool(difference and int(difference[0]["value"]) == oracle["turn_2"]["Patna_minus_Gaya"])
        and difference[0]["unit"] == "number"
    )
    checks.append({"name": "turn-2-largest-and-exact-count-gap", "passed": answer_passed})
    if not answer_passed:
        failures.append("turn 2 largest district or exact count gap is wrong")

    final_browser = json.loads((args.run_dir / "turn-4/browser/browser-check.json").read_text())
    body = final_browser["body_text"]
    lakh_passed = all(f"{value:.2f} lakh" in body for value in oracle["expected_lakh_rounded_2dp"].values())
    exact_visible = all(f"{value:,}" in body for value in oracle["expected_population"].values())
    checks.append({"name": "turn-4-two-decimal-lakh-and-exact-counts-visible", "passed": lakh_passed and exact_visible})
    if not lakh_passed or not exact_visible:
        failures.append("final page does not retain both two-decimal lakh values and exact counts")

    with (args.run_dir / "turn-4/browser/downloads/filtered-dashboard.csv").open(newline="") as handle:
        downloaded = list(csv.DictReader(handle))
    required = set(oracle["turn_4_download"]["required_columns"])
    download_passed = (
        len(downloaded) == oracle["turn_4_download"]["required_row_count"]
        and required <= set(downloaded[0])
        and {row["district"]: int(row["population"]) for row in downloaded} == expected
        and all(int(row["census_year"]) == oracle["year"] for row in downloaded)
        and all(urlparse(row["source_url"]).hostname in oracle["citation"]["accepted_official_domains"] for row in downloaded)
    )
    checks.append({"name": "turn-4-traceable-three-row-download", "passed": download_passed})
    if not download_passed:
        failures.append("final download is not the exact traceable three-row table")

    result = {
        "case_id": "dev-web-census-001",
        "scope_warning": "The measured split stage begins after source discovery using a bounded Census A-01 connector; it is not a general web-search result.",
        "checks": checks,
        "critical_failures": failures,
        "passed_critical": not failures,
        "fully_satisfied_oracle": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
