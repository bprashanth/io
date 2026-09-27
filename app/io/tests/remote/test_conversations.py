#!/usr/bin/env python3
"""Unit tests for remote worker conversation helpers."""

from __future__ import annotations

import ast
import datetime
import json
import os
import pathlib
import re
import stat
import tempfile
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKER = REPO_ROOT / "app" / "io" / "remote" / "worker.py"

HELPER_NAMES = {
    "_uuid_text",
    "_clean_text",
    "_timestamp_text",
    "_conversation_date",
    "_session_root",
    "_resolve_session_relative",
    "_iter_session_relpaths",
    "_read_session_meta",
    "conversation_records",
    "list_conversations",
    "find_conversation_path",
    "delete_conversation",
    "status_snapshot",
}


def load_helpers():
    source = WORKER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(WORKER))
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in HELPER_NAMES]
    missing = HELPER_NAMES - {node.name for node in body}
    if missing:
        raise AssertionError(f"Missing helper defs in worker.py: {sorted(missing)}")
    module = ast.Module(body=body, type_ignores=[])
    code = compile(module, str(WORKER), "exec")
    ns = {
        "datetime": datetime,
        "json": json,
        "os": os,
        "pathlib": pathlib,
        "re": re,
        "stat": stat,
        "uuid": uuid,
    }
    exec(code, ns)
    return ns


H = load_helpers()


def write_session_file(root: Path, relative: str, meta: dict, *, extra_lines: list[str] | None = None) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if meta.get('type') == 'session_meta':
        meta = {'type':'session_meta', 'timestamp':'2026-09-27T00:00:00Z', 'payload':{k:v for k,v in meta.items() if k != 'type'}}
    lines = [json.dumps(meta, sort_keys=True)]
    if extra_lines:
        lines.extend(extra_lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class ConversationHelperTests(unittest.TestCase):
    def test_list_conversations_uses_first_line_only_and_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="io-conversation-helpers-") as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "sessions"
            root.mkdir()

            good_id = str(uuid.uuid4())
            bad_id = str(uuid.uuid4())
            linked_id = str(uuid.uuid4())

            write_session_file(
                root,
                "2026/09/26/good.jsonl",
                {
                    "type": "session_meta",
                    "id": good_id,
                    "title": "  Safe conversation  ",
                    "created_at": "2026-09-26T12:34:00Z",
                    "cwd": "/home/beeps/src/github.com/bprashanth/io",
                },
                extra_lines=[
                    json.dumps(
                        {
                            "type": "session_meta",
                            "id": bad_id,
                            "title": "This transcript line must never be used",
                            "cwd": "/home/beeps/secret",
                        }
                    )
                ],
            )
            write_session_file(
                root,
                "2026/09/26/ignored.jsonl",
                {"type": "message", "text": "not session_meta on the first line"},
                extra_lines=[
                    json.dumps(
                        {
                            "type": "session_meta",
                            "id": linked_id,
                            "title": "Late meta must be ignored",
                            "created_at": "2026-09-26T13:00:00Z",
                            "transcript": "/home/beeps/secret/transcript",
                        }
                    )
                ],
            )
            outside = tmp_path / "outside.jsonl"
            write_session_file(
                tmp_path,
                "outside.jsonl",
                {
                    "type": "session_meta",
                    "id": str(uuid.uuid4()),
                    "title": "Symlink target",
                    "created_at": "2026-09-26T14:00:00Z",
                },
            )
            (root / "2026" / "09" / "26" / "linked.jsonl").symlink_to(outside)

            conversations = H["list_conversations"](root)

            self.assertEqual(len(conversations), 1)
            self.assertEqual(conversations[0]["id"], good_id)
            self.assertEqual(conversations[0]["title"], "Safe conversation")
            self.assertEqual(conversations[0]["date"], "2026-09-26 12:34 UTC")
            self.assertEqual(sorted(conversations[0].keys()), ["date", "id", "title"])

    def test_find_and_delete_conversation_use_uuid_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="io-conversation-helpers-") as tmp:
            root = Path(tmp) / "sessions"
            root.mkdir()

            conv_id = str(uuid.uuid4())
            session = write_session_file(
                root,
                "2026/09/27/thread.jsonl",
                {
                    "type": "session_meta",
                    "id": conv_id,
                    "title": "Delete me",
                    "created_at": 1738000000,
                },
            )

            self.assertEqual(H["find_conversation_path"](root, conv_id), "2026/09/27/thread.jsonl")
            H["delete_conversation"](root, conv_id)
            self.assertFalse(session.exists())
            self.assertEqual(H["list_conversations"](root), [])

            with self.assertRaises(ValueError):
                H["find_conversation_path"](root, "../../etc/passwd")

    def test_status_snapshot_marks_persistent_and_active_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="io-conversation-helpers-") as tmp:
            root = Path(tmp) / "sessions"
            root.mkdir()

            conv_id = str(uuid.uuid4())
            write_session_file(
                root,
                "2026/09/27/active.jsonl",
                {
                    "type": "session_meta",
                    "id": conv_id,
                    "title": "Active thread",
                    "created_at": "2026-09-27T10:11:12Z",
                },
            )

            payload = H["status_snapshot"](
                logged_in=True,
                running=True,
                mode="data",
                ended=False,
                sandbox=True,
                persistent=True,
                instance="inst-123",
                version="v1",
                root=root,
            )

            self.assertTrue(payload["persistent"])
            self.assertTrue(payload["hasConversation"])
            self.assertIsNone(payload["conversationId"])
            self.assertEqual(payload["instance"], "inst-123")
            self.assertEqual(payload["version"], "v1")
            self.assertTrue(payload["sandbox"])


if __name__ == "__main__":
    unittest.main()
