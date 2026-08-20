#!/usr/bin/env python3
"""Prepare a traceable district table from an official Census A-01 workbook.

This is a bounded official-source connector after discovery, not a general web
search system. It deliberately takes the discovered official URLs as inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download-url", required=True)
    parser.add_argument("--catalog-url", required=True)
    parser.add_argument("--district", action="append", required=True)
    parser.add_argument("--year", type=int, default=2011)
    parser.add_argument("--publisher", required=True)
    parser.add_argument("--source-table", required=True)
    args = parser.parse_args()

    for url in (args.download_url, args.catalog_url):
        host = (urlparse(url).hostname or "").lower()
        if host not in ("censusindia.gov.in", "www.censusindia.gov.in"):
            raise SystemExit(f"refusing non-Census host: {host}")

    request = urllib.request.Request(args.download_url, headers={"User-Agent": "ngo-dashboard-benchmark/1"})
    tls = ssl._create_unverified_context()  # Host chain is not accepted by this machine; retained in manifest.
    with urllib.request.urlopen(request, context=tls, timeout=60) as response:
        workbook_bytes = response.read()
        status = response.status
        content_type = response.headers.get("Content-Type")
    if status != 200 or not workbook_bytes.startswith(b"PK"):
        raise SystemExit(f"official download was not an XLSX: status={status}, type={content_type}")

    source_dir = args.output / "source-data"
    workbook_path = source_dir / "A01_2011.xlsx"
    source_dir.mkdir(parents=True, exist_ok=True)
    workbook_path.write_bytes(workbook_bytes)

    raw = pd.read_excel(workbook_path, sheet_name=0, header=None)
    district_rows = raw[(raw[3] == "DISTRICT") & (raw[5] == "Total")].copy()
    district_rows[4] = district_rows[4].astype(str).str.strip()
    wanted = {name.casefold(): name for name in args.district}
    selected = district_rows[district_rows[4].str.casefold().isin(wanted)].copy()
    found = {name.casefold() for name in selected[4]}
    missing = sorted(set(wanted) - found)
    if missing:
        raise SystemExit(f"districts absent from official district-total rows: {missing}")

    rows = []
    for _, row in selected.iterrows():
        district = wanted[str(row[4]).casefold()]
        population = int(row[10])
        rows.append({
            "district": district,
            "population": population,
            "population_lakh": round(population / 100000, 5),
            "census_year": args.year,
            "source_url": args.download_url,
            "catalog_url": args.catalog_url,
            "publisher": args.publisher,
            "source_table": args.source_table,
            "source": f"{args.publisher}, Census {args.year}",
        })
    frame = pd.DataFrame(rows).sort_values("district").reset_index(drop=True)
    input_dir = args.output / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    csv_path = input_dir / "census_district_population.csv"
    frame.to_csv(csv_path, index=False)

    original_case = json.loads((args.case_dir / "case.json").read_text())
    original_case["inputs"] = [{
        "path": "inputs/census_district_population.csv",
        "sha256": sha256(csv_path.read_bytes()),
        "bytes": csv_path.stat().st_size,
        "provenance": (
            f"Derived without model-authored values from official Census A-01 workbook {args.download_url}; "
            f"catalog {args.catalog_url}; publisher {args.publisher}; raw workbook retained with SHA-256 {sha256(workbook_bytes)}."
        ),
    }]
    write_json(args.output / "case.json", original_case)
    write_json(args.output / "discovery-manifest.json", {
        "stage": "bounded official-source connector after URL discovery",
        "download_url": args.download_url,
        "catalog_url": args.catalog_url,
        "publisher": args.publisher,
        "source_table": args.source_table,
        "census_year": args.year,
        "requested_districts": args.district,
        "download_http_status": status,
        "download_content_type": content_type,
        "raw_workbook_bytes": len(workbook_bytes),
        "raw_workbook_sha256": sha256(workbook_bytes),
        "derived_csv_sha256": sha256(csv_path.read_bytes()),
        "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tls_note": "Certificate verification disabled because the host chain is not accepted by this machine; URL host was allowlisted and bytes/hash were retained.",
        "scope_warning": "This connector parses Census A-01 district-total rows only; it is not general online dataset discovery.",
    })
    print(json.dumps({"rows": len(frame), "csv": str(csv_path), "workbook_sha256": sha256(workbook_bytes)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
