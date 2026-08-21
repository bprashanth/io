#!/usr/bin/env python3
"""Run a replayable Antigravity conversation inside an outer Docker boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def hash_workspace(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in path.parts):
            continue
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def parse_events(path: Path) -> tuple[str | None, dict[str, Any] | None]:
    conversation_id: str | None = None
    final_result: dict[str, Any] | None = None
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "init":
            conversation_id = event.get("conversation_id")
        elif event.get("event") == "result":
            final_result = event.get("result")
    return conversation_id, final_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="io-benchmark-agent-tools:2026-08-20-v2")
    parser.add_argument("--agy-binary", type=Path, default=Path.home() / ".local/bin/agy")
    parser.add_argument(
        "--oauth-token",
        type=Path,
        default=Path.home() / ".gemini/antigravity-cli/antigravity-oauth-token",
    )
    parser.add_argument("--turn-timeout", type=float, default=1200)
    args = parser.parse_args()

    case = json.loads(args.case.read_text())
    args.workspace = args.workspace.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    state_root = Path(tempfile.mkdtemp(prefix="io-agy-container-state-"))
    cli_state = state_root / "antigravity-cli"
    cli_state.mkdir()
    token_copy = cli_state / "antigravity-oauth-token"
    shutil.copyfile(args.oauth_token, token_copy)
    token_copy.chmod(0o600)

    started = time.time()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case["case_id"],
        "agent": "antigravity",
        "agent_version": subprocess.check_output(
            [str(args.agy_binary), "--version"], text=True
        ).strip(),
        "model_policy": "untouched-default",
        "outer_container_image": args.image,
        "workspace": str(args.workspace),
        "state_root": str(state_root),
        "started_at_unix": started,
        "turns": [],
    }
    image_info = subprocess.run(
        [
            "docker", "image", "inspect", args.image, "--format",
            "{{json .Id}}|{{json .RepoDigests}}|{{json .Os}}/{{json .Architecture}}",
        ],
        text=True,
        capture_output=True,
    )
    if image_info.returncode == 0:
        image_id, repo_digests, platform = image_info.stdout.strip().split("|", 2)
        summary["outer_container_image_id"] = json.loads(image_id)
        summary["outer_container_repo_digests"] = json.loads(repo_digests)
        summary["outer_container_platform"] = platform.replace('"', "")
    else:
        summary["outer_container_image_inspect_error"] = image_info.stderr.strip()

    conversation_id: str | None = None
    exit_code = 1
    try:
        for message in case["messages"]:
            turn = int(message["turn"])
            stdout_path = args.output / f"agent-turn-{turn:02d}.ndjson"
            stderr_path = args.output / f"agent-turn-{turn:02d}.stderr.txt"
            container_name = f"io-agy-{os.getpid()}-turn{turn}"
            command = [
                "docker",
                "run",
                "--rm",
                "--name",
                container_name,
                "--memory",
                "1g",
                "--cpus",
                "2",
                "--pids-limit",
                "256",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "-e",
                "HOME=/home/benchmark",
                "-w",
                "/workspace",
                "-v",
                "/etc/ssl/certs:/etc/ssl/certs:ro",
                "-v",
                f"{args.agy_binary.resolve()}:/usr/local/bin/agy:ro",
                "-v",
                f"{state_root}:/home/benchmark/.gemini",
                "-v",
                f"{args.workspace}:/workspace",
                args.image,
                "/usr/local/bin/agy",
                "--dangerously-skip-permissions",
                "--output-format",
                "stream-json",
                "--print-timeout",
                f"{int(args.turn_timeout)}s",
            ]
            if conversation_id:
                command.extend(["--conversation", conversation_id])
            command.extend(["-p", message["text"]])
            turn_started = time.time()
            with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
                completed = subprocess.run(
                    command,
                    text=True,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=args.turn_timeout + 60,
                )
            observed_conversation_id, final_result = parse_events(stdout_path)
            if not conversation_id:
                conversation_id = observed_conversation_id
                summary["conversation_id"] = conversation_id
            elif observed_conversation_id != conversation_id:
                raise RuntimeError(
                    f"conversation changed on turn {turn}: {observed_conversation_id}"
                )
            turn_record = {
                "turn": turn,
                "duration_seconds": round(time.time() - turn_started, 3),
                "process_exit_code": completed.returncode,
                "result": final_result,
                "workspace_hashes": hash_workspace(args.workspace),
            }
            summary["turns"].append(turn_record)
            snapshot = args.output / f"workspace-after-turn-{turn}"
            shutil.copytree(
                args.workspace,
                snapshot,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(
                    ".git", "node_modules", ".venv", "venv", "__pycache__"
                ),
            )
            if completed.returncode != 0 or not conversation_id or final_result is None:
                raise RuntimeError(f"Antigravity turn {turn} did not produce a complete result")
        exit_code = 0
    except Exception as error:
        summary["runner_error"] = f"{type(error).__name__}: {error}"
    finally:
        token_copy.unlink(missing_ok=True)
        model_labels: set[str] = set()
        model_log_evidence: list[dict[str, str]] = []
        for log_path in sorted((cli_state / "log").glob("*.log")):
            for line in log_path.read_text(errors="replace").splitlines():
                match = re.search(
                    r'Propagating selected model override to backend: label="([^"]+)"',
                    line,
                )
                if match:
                    model_labels.add(match.group(1))
                    if not any(
                        item["label"] == match.group(1) for item in model_log_evidence
                    ):
                        model_log_evidence.append(
                            {
                                "log": log_path.name,
                                "label": match.group(1),
                                "line": line,
                            }
                        )
        summary["resolved_model_labels_from_logs"] = sorted(model_labels)
        summary["model_log_evidence"] = model_log_evidence
        summary["oauth_token_removed"] = not token_copy.exists()
        summary["finished_at_unix"] = time.time()
        summary["duration_seconds"] = round(summary["finished_at_unix"] - started, 3)
        summary["exit_code"] = exit_code
        (args.output / "antigravity-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
