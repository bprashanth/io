#!/usr/bin/env python3
"""Quota handling tests for the privacy proxy."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codex_proxy import Policy, Proxy  # noqa: E402


class DummyPolicy(Policy):
    def outbound(self, text: str, role: str | None) -> str:
        return text

    def inbound(self, text: str) -> str:
        return text


def make_proxy() -> Proxy:
    return Proxy(DummyPolicy())


class QuotaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proxy = make_proxy()

    def test_wham_usage_tracks_allowed_limit_and_primary_window(self) -> None:
        cases = [
            (
                "allowed",
                {
                    "rate_limit": {
                        "allowed": True,
                        "limit_reached": False,
                        "primary_window": {"used_percent": 42, "reset_at": 111},
                        "secondary_window": {"used_percent": 5, "reset_at": 999},
                    }
                },
                {"exhausted": False, "reset_at": None},
            ),
            (
                "limit_reached",
                {
                    "rate_limit": {
                        "allowed": True,
                        "limit_reached": True,
                        "primary_window": {"used_percent": 100, "reset_at": 222},
                    }
                },
                {"exhausted": True, "reset_at": 222},
            ),
            (
                "allowed_false",
                {
                    "rate_limit": {
                        "allowed": False,
                        "limit_reached": False,
                        "primary_window": {"used_percent": 100, "reset_at": 333},
                    }
                },
                {"exhausted": True, "reset_at": 333},
            ),
        ]

        for name, payload, expected in cases:
            with self.subTest(name=name):
                self.proxy.quota = {"exhausted": False}
                self.proxy.observe(payload, "/backend-api/wham/usage")
                self.assertEqual(self.proxy.quota, expected)

    def test_usage_limit_reached_http_style_error_sets_reset_time(self) -> None:
        self.proxy.observe(
            {"error": {"type": "usage_limit_reached", "resets_at": 1790460900}},
            "/backend-api/codex/responses",
        )
        self.assertEqual(
            self.proxy.quota,
            {"exhausted": True, "reset_at": 1790460900},
        )

    def test_sse_response_failed_error_sets_reset_time(self) -> None:
        self.proxy.observe(
            {
                "type": "response.failed",
                "response": {
                    "error": {
                        "type": "usage_limit_reached",
                        "resets_at": 1790463600,
                    }
                },
            },
            "/backend-api/codex/responses",
        )
        self.assertEqual(
            self.proxy.quota,
            {"exhausted": True, "reset_at": 1790463600},
        )

    def test_generic_429_is_not_quota(self) -> None:
        self.proxy.quota = {"exhausted": True, "reset_at": "keep"}
        self.proxy.observe(
            {"error": {"code": 429, "type": "rate_limit_exceeded", "message": "slow down"}},
            "/backend-api/codex/responses",
        )
        self.assertEqual(self.proxy.quota, {"exhausted": True, "reset_at": "keep"})

    def test_router_context_errors_set_handover_message(self) -> None:
        cases = [
            {"error": {"code": "context_length_exceeded", "message": "context window is too small"}},
            {"error": {"message": "invalid previous_response_id for this handoff"}},
        ]
        expected = {
            "kind": "handover",
            "message": "This smaller model could not continue the saved conversation. Start with a catch-up from its visible messages.",
        }

        for payload in cases:
            with self.subTest(payload=payload):
                self.proxy.provider_error = None
                self.proxy.observe(payload, "/openrouter/v1/responses", True)
                self.assertEqual(self.proxy.provider_error, expected)


if __name__ == "__main__":
    unittest.main(verbosity=1)
