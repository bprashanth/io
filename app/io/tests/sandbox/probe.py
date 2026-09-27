#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path


PREFIX = "IO_SANDBOX_PROBE="
DENIED_ERRNOS = {
    getattr(os, "EACCES", 13),
    getattr(os, "EPERM", 1),
    getattr(os, "ENOENT", 2),
    getattr(os, "ENOTDIR", 20),
    getattr(os, "EROFS", 30),
}


def clip(text: object, limit: int = 300) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def error_info(exc: BaseException) -> dict[str, object]:
    info: dict[str, object] = {
        "type": exc.__class__.__name__,
        "message": clip(exc),
    }
    errno = getattr(exc, "errno", None)
    if errno is not None:
        try:
            info["errno"] = int(errno)
        except Exception:
            info["errno"] = errno
    winerror = getattr(exc, "winerror", None)
    if winerror is not None:
        try:
            info["winerror"] = int(winerror)
        except Exception:
            info["winerror"] = winerror
    return info


def classify_oserror(exc: OSError) -> str:
    if getattr(exc, "winerror", None) == 5:
        return "denied"
    if getattr(exc, "errno", None) in DENIED_ERRNOS:
        return "denied"
    return "error"


def trim_detail(text: str) -> str:
    return clip(text, 300)


def load_manifest(path: str) -> dict[str, object]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def read_exact_token(path: str, token: str, role: str, name: str) -> dict[str, object]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "outcome": classify_oserror(exc),
            "detail": trim_detail(f"{role} {name} read failed"),
            "error": error_info(exc),
        }
    if content != token:
        return {
            "outcome": "error",
            "detail": trim_detail(f"{role} {name} read unexpected content"),
        }
    return {
        "outcome": "allowed",
        "detail": "matched token",
    }


def write_workspace(path: str, token: str, label: str) -> dict[str, object]:
    expected = f"{token}:{label}:parent"
    try:
        Path(path).write_text(expected, encoding="utf-8")
        observed = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "outcome": classify_oserror(exc),
            "detail": trim_detail("workspace write failed"),
            "error": error_info(exc),
        }
    if observed != expected:
        return {
            "outcome": "error",
            "detail": "workspace write did not round-trip",
        }
    return {
        "outcome": "allowed",
        "detail": "wrote and verified",
    }


def append_existing(path: str, token: str, label: str, role: str) -> dict[str, object]:
    line = f"\n{token}:{label}:{role}"
    fd = None
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND)
        with os.fdopen(fd, "a", encoding="utf-8", newline="") as fh:
            fd = None
            fh.write(line)
            fh.flush()
    except OSError as exc:
        return {
            "outcome": classify_oserror(exc),
            "detail": trim_detail(f"{role} append failed"),
            "error": error_info(exc),
        }
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
    return {
        "outcome": "allowed",
        "detail": "appended",
    }


def recv_ack(sock: socket.socket) -> tuple[bool, str | None]:
    buf = bytearray()
    try:
        while b"\n" not in buf and len(buf) < 4096:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
    except Exception as exc:  # noqa: BLE001
        return False, json.dumps(error_info(exc), separators=(",", ":"))
    line = bytes(buf.split(b"\n", 1)[0] + (b"\n" if b"\n" in buf else b""))
    if line == b"io-ack\n":
        return True, None
    if not line:
        return False, "empty ack"
    return False, trim_detail(f"unexpected ack {line!r}")


def tcp_endpoint(endpoint: dict[str, object], token: str, label: str, role: str) -> dict[str, object]:
    host = str(endpoint["host"])
    port = int(endpoint["port"])
    ack = bool(endpoint.get("ack", False))
    payload = {"token": token, "label": label, "role": role, "endpoint": str(endpoint["name"])}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3.0)
            sock.connect((host, port))
            if not ack:
                return {
                    "outcome": "allowed",
                    "detail": f"connected to {host}:{port}",
                }
            ack_ok = False
            ack_error = None
            try:
                wire = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
                sock.sendall(wire)
                ack_ok, ack_error = recv_ack(sock)
            except Exception as exc:  # noqa: BLE001
                ack_ok = False
                ack_error = json.dumps(error_info(exc), separators=(",", ":"))
            result: dict[str, object] = {
                "outcome": "allowed",
                "detail": f"connected to {host}:{port}",
                "ack": ack_ok,
            }
            if not ack_ok:
                result["ack_error"] = ack_error if ack_error is not None else "ack failed"
            return result
    except OSError as exc:
        return {
            "outcome": "denied",
            "detail": trim_detail(f"connect to {host}:{port} failed"),
            "error": error_info(exc),
        }


def run_checks(manifest: dict[str, object], label: str, role: str) -> dict[str, object]:
    token = str(manifest["token"])
    checks: dict[str, object] = {}
    if role == "parent":
        checks["workspace_read"] = read_exact_token(str(manifest["workspace_read"]), token, role, "workspace_read")
        checks["workspace_write"] = write_workspace(str(manifest["workspace_write"]), token, label)
    checks["outside_read"] = read_exact_token(str(manifest["outside_read"]), token, role, "outside_read")
    checks["outside_write"] = append_existing(str(manifest["outside_write"]), token, label, role)
    checks["link_read"] = read_exact_token(str(manifest["link_read"]), token, role, "link_read")
    checks["link_write"] = append_existing(str(manifest["link_write"]), token, label, role)
    for endpoint in manifest.get("endpoints", []):
        if isinstance(endpoint, dict) and "name" in endpoint:
            checks[f"tcp:{endpoint['name']}"] = tcp_endpoint(endpoint, token, label, role)
    return checks


def parse_child_output(stdout: str) -> dict[str, object] | None:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        return None
    line = lines[0]
    if not line.startswith(PREFIX):
        return None
    payload = line[len(PREFIX) :]
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def emit(data: dict[str, object]) -> None:
    sys.stdout.write(PREFIX + json.dumps(data, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def fail(message: str) -> None:
    print(trim_detail(message), file=sys.stderr)
    raise SystemExit(2)


def main() -> None:
    argv = sys.argv[1:]
    if len(argv) not in {2, 3}:
        fail("usage: probe.py <manifest.json> <label> [--child]")
    manifest_arg, label = argv[0], argv[1]
    child_mode = len(argv) == 3 and argv[2] == "--child"
    if len(argv) == 3 and not child_mode:
        fail("usage: probe.py <manifest.json> <label> [--child]")

    try:
        manifest = load_manifest(manifest_arg)
        checks = run_checks(manifest, label, "child" if child_mode else "parent")
        if child_mode:
            emit({"label": label, "role": "child", "checks": checks})
            return

        parent_checks = checks
        child_data = None
        try:
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), manifest_arg, label, "--child"],
                cwd=os.getcwd(),
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=35,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            parent_checks["child_execution"] = {
                "outcome": "error",
                "detail": trim_detail(f"child execution failed: {exc.__class__.__name__}: {exc}"),
            }
        else:
            if proc.returncode == 0:
                child_data = parse_child_output(proc.stdout or "")
                if child_data is not None and child_data.get("role") != "child":
                    child_data = None
                if child_data is not None and child_data.get("label") != label:
                    child_data = None
            if proc.returncode != 0 or child_data is None:
                detail = f"child exit={proc.returncode}"
                if proc.stdout:
                    detail += f" stdout={trim_detail(proc.stdout)}"
                if proc.stderr:
                    detail += f" stderr={trim_detail(proc.stderr)}"
                parent_checks["child_execution"] = {
                    "outcome": "error",
                    "detail": trim_detail(detail),
                }
            else:
                parent_checks["child_execution"] = {
                    "outcome": "allowed",
                    "detail": "child exit 0",
                }
                for name, value in child_data.get("checks", {}).items():
                    parent_checks[f"child:{name}"] = value
        emit({
            "label": label,
            "role": "parent",
            "pid": os.getpid(),
            "interpreter": sys.executable,
            "checks": parent_checks,
        })
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        fail(f"infrastructure failure: {exc.__class__.__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001
        fail(f"infrastructure failure: {exc.__class__.__name__}: {exc}")


if __name__ == "__main__":
    main()
