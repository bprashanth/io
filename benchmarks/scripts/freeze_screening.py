#!/usr/bin/env python3
"""Create a content-addressed manifest for the measured screening phase."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
CASE_IDS = (
    "dev-csv-health-001",
    "dev-xlsx-health-001",
    "dev-pdf-health-001",
    "dev-safe-programme-001",
    "dev-web-census-001",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def docker_value(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["docker", *args], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks/config/screening-freeze-v3.json",
    )
    parser.add_argument("--benchmark-version", default="screening-v3")
    parser.add_argument("--requested-model", default="qwen/qwen3.5-9b:nitro")
    parser.add_argument("--underlying-model", default="qwen/qwen3.5-9b")
    parser.add_argument("--weights", default="Qwen/Qwen3.5-9B")
    parser.add_argument(
        "--weights-revision",
        default="c202236235762e1c871ad0ccb60c8ee5ba337b9a",
    )
    parser.add_argument(
        "--reasoning",
        default="xhigh (explicitly injected and logged by the controlled proxy)",
    )
    parser.add_argument("--harness-prompt-file", type=Path)
    parser.add_argument("--change-note", default="new candidate or named harness track")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing freeze manifest: {output}; pass --force deliberately")

    cases: list[dict[str, object]] = []
    for case_id in CASE_IDS:
        case_root = ROOT / "benchmarks/cases" / case_id
        files = [
            path
            for path in sorted(case_root.rglob("*"))
            if path.is_file() and "oracle-sources" not in path.parts
        ]
        cases.append({"case_id": case_id, "files": [file_record(path) for path in files]})

    image_config = json.loads(
        (ROOT / "benchmarks/config/agent-tools-image.json").read_text()
    )
    tag = image_config["tag"]
    live_image_id = docker_value("image", "inspect", tag, "--format", "{{.Id}}")
    if live_image_id != image_config["image_id"]:
        raise SystemExit(
            f"tool image mismatch: manifest={image_config['image_id']} live={live_image_id}"
        )

    manifest = {
        "schema_version": 1,
        "benchmark_version": args.benchmark_version,
        "frozen_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
        "pilot_runs_excluded": [
            "benchmarks/runs/2026-08-20-screening-pilot/dev-csv-health-001",
            "benchmarks/runs/2026-08-20-screening-v1"
        ],
        "baseline": {
            "product": "Antigravity",
            "version": "1.1.15",
            "model_policy": "untouched default, resolved and recorded per run",
            "pilot_resolution": "gemini-3.7-flash-high",
            "pilot_effort": "high",
        },
        "candidate": {
            "product": "Cline ACP",
            "version": "3.0.55",
            "provider": "OpenRouter OpenAI-compatible endpoint",
            "requested_model": args.requested_model,
            "asserted_underlying_model": args.underlying_model,
            "reasoning": args.reasoning,
            "weights": args.weights,
            "weights_revision": args.weights_revision,
            "harness_prompt": str(args.harness_prompt_file.resolve()) if args.harness_prompt_file else None,
            "harness_prompt_sha256": sha256(args.harness_prompt_file) if args.harness_prompt_file else None,
        },
        "tool_environment": image_config,
        "live_tool_image_id": live_image_id,
        "protocol": {
            "conversation": "all case turns in one live session and workspace",
            "primary_browser_mode": "workshop-online",
            "secondary_browser_mode": "offline-resilience",
            "application_review": "actual served desktop and 390x844 narrow pages",
            "repetitions": 1,
            "futility": "after >=3 pairs only; >=20 point gap or >=2 excess critical failures",
            "early_success": False,
            "change_note": args.change_note,
        },
        "frozen_files": [
            file_record(ROOT / "benchmarks/DESIGN.md"),
            file_record(ROOT / "benchmarks/config/scoring.json"),
            file_record(ROOT / "benchmarks/config/model-ladder.json"),
            file_record(ROOT / "benchmarks/config/agent-tools-image.json"),
            file_record(ROOT / "benchmarks/docker/agent-tools.Dockerfile"),
            file_record(ROOT / "benchmarks/schemas/case.schema.json"),
            file_record(ROOT / "benchmarks/schemas/run-record.schema.json"),
            file_record(ROOT / "benchmarks/scripts/antigravity_container_runner.py"),
            file_record(ROOT / "benchmarks/scripts/cline_acp_runner.py"),
            file_record(ROOT / "benchmarks/scripts/openrouter_proxy.py"),
            file_record(ROOT / "benchmarks/scripts/verify_cases.py"),
            file_record(ROOT / "benchmarks/scripts/smoke_browser.py"),
        ],
        "cases": cases,
    }
    if args.harness_prompt_file:
        manifest["frozen_files"].append(file_record(args.harness_prompt_file.resolve()))
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {output}")
    print(f"sha256 {sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
