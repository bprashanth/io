#!/usr/bin/env python3
"""Run a replayable multi-turn Cline session through ACP over stdio.

The runner keeps the ACP process alive for the whole case, which matches an
interactive editor session and avoids Cline CLI's broken JSON resume path.
Raw protocol traffic is retained as NDJSON. Credentials are read into the
child environment and are never written to the evidence directory.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, TextIO


def load_openrouter_key(path: Path) -> str:
    document = json.loads(path.read_text())
    for field in ("api_key", "key", "OPENROUTER_API_KEY"):
        value = document.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError(f"No recognized OpenRouter key field in {path}")


def pump(stream: TextIO, channel: str, events: queue.Queue[tuple[str, str]]) -> None:
    for line in stream:
        events.put((channel, line.rstrip("\n")))
    events.put((channel, ""))


class AcpClient:
    def __init__(self, process: subprocess.Popen[str], raw: TextIO, stderr: TextIO):
        self.process = process
        self.raw = raw
        self.stderr = stderr
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.pending: dict[int, dict[str, Any]] = {}
        self.notifications: list[dict[str, Any]] = []
        threading.Thread(
            target=pump, args=(process.stdout, "stdout", self.events), daemon=True
        ).start()
        threading.Thread(
            target=pump, args=(process.stderr, "stderr", self.events), daemon=True
        ).start()

    def send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        self.raw.write(
            json.dumps(
                {"direction": "client_to_agent", "time_unix": time.time(), "message": message}
            )
            + "\n"
        )
        self.raw.flush()

    def _handle_agent_request(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        request_id = message.get("id")
        if method == "session/request_permission":
            options = message.get("params", {}).get("options", [])
            selected = next(
                (
                    option
                    for option in options
                    if option.get("kind") in {"allow_always", "allow_once"}
                ),
                options[0] if options else None,
            )
            if selected:
                result = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "outcome": {
                            "outcome": "selected",
                            "optionId": selected["optionId"],
                        }
                    },
                }
            else:
                result = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"outcome": {"outcome": "cancelled"}},
                }
            self.send(result)
            return

        self.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unsupported client method: {method}"},
            }
        )

    def wait_for(self, request_id: int, timeout_seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if request_id in self.pending:
                return self.pending.pop(request_id)
            remaining = max(0.01, deadline - time.monotonic())
            try:
                channel, line = self.events.get(timeout=min(1.0, remaining))
            except queue.Empty:
                if self.process.poll() is not None:
                    raise RuntimeError(f"Cline ACP exited early with code {self.process.returncode}")
                continue
            if channel == "stderr":
                if line:
                    self.stderr.write(line + "\n")
                    self.stderr.flush()
                continue
            if not line:
                if self.process.poll() is not None:
                    raise RuntimeError(f"Cline ACP stdout closed (code {self.process.returncode})")
                continue
            message = json.loads(line)
            self.raw.write(
                json.dumps(
                    {"direction": "agent_to_client", "time_unix": time.time(), "message": message}
                )
                + "\n"
            )
            self.raw.flush()
            if "method" in message and "id" in message:
                self._handle_agent_request(message)
            elif "id" in message:
                self.pending[int(message["id"])] = message
            else:
                self.notifications.append(message)
        raise TimeoutError(f"Timed out waiting for ACP request {request_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--provider", default="openrouter")
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--base-url",
        help="OpenAI-compatible API base URL (for example https://openrouter.ai/api/v1)",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="create the session and assert the model, but do not send case messages",
    )
    parser.add_argument("--thinking", choices=("none", "low", "medium", "high", "xhigh"))
    parser.add_argument(
        "--request-reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        help="record an effort injected by an auditable API proxy (does not change ACP itself)",
    )
    parser.add_argument("--turn-timeout", type=float, default=900)
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="optional named harness override; retained by path and SHA-256 in the run summary",
    )
    parser.add_argument(
        "--container-image",
        default="io-benchmark-agent-tools:2026-08-20-v2",
        help="run Cline inside the shared benchmark tool image; pass an empty value only for a host diagnostic",
    )
    parser.add_argument(
        "--snapshot-workspace",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="retain source snapshots after every turn (dependency/cache directories excluded)",
    )
    parser.add_argument(
        "--key-file",
        type=Path,
        default=Path.home() / ".config/idlisseus/openrouter.json",
    )
    args = parser.parse_args()

    case = json.loads(args.case.read_text())
    args.workspace = args.workspace.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    isolated_home = (args.data_dir / "home").resolve()
    isolated_home.mkdir(parents=True, exist_ok=True)

    api_key = load_openrouter_key(args.key_file)
    env = os.environ.copy()
    env.update(
        CLINE_API_KEY=api_key,
        CLINE_PROVIDER=args.provider,
        CLINE_MODEL=args.model,
        HOME=str(isolated_home),
        XDG_CONFIG_HOME=str(isolated_home / ".config"),
        XDG_CACHE_HOME=str(isolated_home / ".cache"),
    )
    secret_provider_path: Path | None = None
    command = [
        "cline",
        "--acp",
        "--auto-approve",
        "true",
        "--data-dir",
        str(args.data_dir.resolve()),
    ]
    if args.provider == "openai-compatible":
        if not args.base_url:
            parser.error("--base-url is required for provider openai-compatible")
        # Cline's supported custom-provider configuration is the correct path
        # both for OpenRouter catalogue bypass and later local vLLM replay. Its
        # CLI stores this under --data-dir/settings. Remove the plaintext
        # credential before retained evidence is finalized.
        settings_dir = args.data_dir / "settings"
        settings_dir.mkdir(parents=True)
        providers_path = settings_dir / "providers.json"
        providers_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "lastUsedProvider": "openai-compatible",
                    "providers": {
                        "openai-compatible": {
                            "settings": {
                                "provider": "openai-compatible",
                                "apiKey": api_key,
                                "model": args.model,
                                "baseUrl": args.base_url,
                            },
                            "updatedAt": datetime.datetime.now(
                                datetime.timezone.utc
                            ).isoformat().replace("+00:00", "Z"),
                            "tokenSource": "manual",
                        }
                    },
                }
            )
            + "\n"
        )
        providers_path.chmod(0o600)
        secret_provider_path = providers_path
        # ACP does not consistently derive this path from --data-dir in 3.0.55.
        # The explicit variable is also what Cline's own CLI setup helper uses.
        env["CLINE_PROVIDER_SETTINGS_PATH"] = str(providers_path.resolve())
    if args.thinking:
        command.extend(["--thinking", args.thinking])
    system_prompt_sha256: str | None = None
    if args.system_prompt_file:
        system_prompt = args.system_prompt_file.read_text()
        system_prompt_sha256 = hashlib.sha256(system_prompt.encode()).hexdigest()
        command.extend(["--system", system_prompt])

    if args.container_image:
        cline_launcher = Path(shutil.which("cline") or "").resolve()
        cline_binary = cline_launcher.parent / ".cline"
        if not cline_binary.is_file():
            raise RuntimeError(f"Cline standalone binary not found beside {cline_launcher}")
        container_name = f"io-cline-acp-{os.getpid()}"
        forwarded_env = [
            "HOME",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "CLINE_API_KEY",
            "CLINE_PROVIDER",
            "CLINE_MODEL",
        ]
        if "CLINE_PROVIDER_SETTINGS_PATH" in env:
            forwarded_env.append("CLINE_PROVIDER_SETTINGS_PATH")
        container_command = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--name",
            container_name,
            "--memory",
            "2g",
            "--cpus",
            "2",
            "--pids-limit",
            "256",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--add-host",
            "host.docker.internal:host-gateway",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
        ]
        for variable in forwarded_env:
            container_command.extend(["-e", variable])
        container_command.extend(
            [
                "-v",
                "/etc/ssl/certs:/etc/ssl/certs:ro",
                "-v",
                f"{cline_binary}:/usr/local/bin/cline:ro",
                "-v",
                f"{args.workspace}:{args.workspace}",
                "-v",
                f"{args.data_dir.resolve()}:{args.data_dir.resolve()}",
                "-w",
                str(args.workspace),
                args.container_image,
                "/usr/local/bin/cline",
                *command[1:],
            ]
        )
        command = container_command

    started = time.time()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case["case_id"],
        "provider": args.provider,
        "model": args.model,
        "base_url": args.base_url,
        "thinking": args.thinking or "provider-default",
        "request_reasoning_effort": args.request_reasoning_effort,
        "system_prompt_file": str(args.system_prompt_file.resolve()) if args.system_prompt_file else None,
        "system_prompt_sha256": system_prompt_sha256,
        "workspace": str(args.workspace),
        "isolated_home": str(isolated_home),
        "outer_container_image": args.container_image,
        "outer_container_enabled": bool(args.container_image),
        "started_at_unix": started,
        "turns": [],
    }
    if args.container_image:
        image_info = subprocess.run(
            [
                "docker", "image", "inspect", args.container_image, "--format",
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
    exit_code = 1
    process: subprocess.Popen[str] | None = None
    try:
        with (args.output / "acp.ndjson").open("w") as raw, (
            args.output / "acp.stderr.txt"
        ).open("w") as stderr:
            process = subprocess.Popen(
                command,
                cwd=args.workspace,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None and process.stderr is not None
            client = AcpClient(process, raw, stderr)
            client.send(
                {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": 1,
                        "clientCapabilities": {},
                        "clientInfo": {"name": "io-benchmark", "version": "0.1"},
                    },
                }
            )
            initialized = client.wait_for(0, 30)
            if "error" in initialized:
                raise RuntimeError(f"ACP initialize failed: {initialized['error']}")
            summary["agent_info"] = initialized["result"].get("agentInfo")

            client.send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "session/new",
                    "params": {"cwd": str(args.workspace), "mcpServers": []},
                }
            )
            created = client.wait_for(1, 60)
            if "error" in created:
                raise RuntimeError(f"ACP session/new failed: {created['error']}")
            session_id = created["result"]["sessionId"]
            summary["session_id"] = session_id
            models = created["result"].get("models", {})
            available_model_ids = {
                item.get("modelId") for item in models.get("availableModels", [])
            }
            summary["session_model_before_selection"] = models.get("currentModelId")
            summary["requested_model_available"] = args.model in available_model_ids
            summary["custom_model_id"] = (
                args.provider == "openai-compatible"
                and args.model not in available_model_ids
            )
            if args.model not in available_model_ids and not summary["custom_model_id"]:
                raise RuntimeError(
                    f"Requested model {args.model!r} is not in the provider catalogue"
                )

            client.send(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "session/set_model",
                    "params": {"sessionId": session_id, "modelId": args.model},
                }
            )
            selected = client.wait_for(2, 60)
            if "error" in selected:
                raise RuntimeError(f"ACP session/set_model failed: {selected['error']}")
            summary["session_model"] = args.model

            for message in ([] if args.probe_only else case["messages"]):
                request_id = 100 + int(message["turn"])
                turn_started = time.time()
                notification_start = len(client.notifications)
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": "session/prompt",
                        "params": {
                            "sessionId": session_id,
                            "prompt": [{"type": "text", "text": message["text"]}],
                        },
                    }
                )
                response = client.wait_for(request_id, args.turn_timeout)
                turn_notifications = client.notifications[notification_start:]
                agent_text = "".join(
                    item.get("params", {})
                    .get("update", {})
                    .get("content", {})
                    .get("text", "")
                    for item in turn_notifications
                    if item.get("method") == "session/update"
                    and item.get("params", {}).get("update", {}).get("sessionUpdate")
                    == "agent_message_chunk"
                )
                usage_updates = [
                    item["params"]["update"]
                    for item in turn_notifications
                    if item.get("method") == "session/update"
                    and item.get("params", {}).get("update", {}).get("sessionUpdate")
                    == "usage_update"
                ]
                summary["turns"].append(
                    {
                        "turn": message["turn"],
                        "duration_seconds": round(time.time() - turn_started, 3),
                        "response": response.get("result"),
                        "error": response.get("error"),
                        "notification_count": len(turn_notifications),
                        "agent_response": agent_text,
                        "tool_call_count": sum(
                            1
                            for item in turn_notifications
                            if item.get("method") == "session/update"
                            and item.get("params", {})
                            .get("update", {})
                            .get("sessionUpdate")
                            == "tool_call"
                        ),
                        "last_usage_update": usage_updates[-1] if usage_updates else None,
                    }
                )
                if args.snapshot_workspace:
                    snapshot = args.output / f"workspace-after-turn-{message['turn']}"
                    shutil.copytree(
                        args.workspace,
                        snapshot,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(
                            ".git", "node_modules", ".venv", "venv", "__pycache__"
                        ),
                    )
                if "error" in response:
                    raise RuntimeError(f"ACP turn {message['turn']} failed: {response['error']}")
            exit_code = 0
    except Exception as error:  # retain an actionable record for runner failures
        summary["runner_error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if secret_provider_path is not None:
            secret_provider_path.unlink(missing_ok=True)
        session_id = summary.get("session_id")
        if session_id:
            session_files = list(args.data_dir.rglob(f"{session_id}.json"))
            session_file = next(
                (path for path in session_files if not path.name.endswith(".messages.json")),
                None,
            )
            if session_file:
                session_document = json.loads(session_file.read_text())
                metadata = session_document.get("metadata", {})
                summary["usage"] = metadata.get("usage")
                summary["aggregate_usage"] = metadata.get("aggregateUsage")
                summary["total_cost"] = metadata.get("totalCost")
                summary["session_metadata_path"] = str(session_file)
        summary["finished_at_unix"] = time.time()
        summary["duration_seconds"] = round(summary["finished_at_unix"] - started, 3)
        summary["exit_code"] = exit_code
        (args.output / "acp-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
