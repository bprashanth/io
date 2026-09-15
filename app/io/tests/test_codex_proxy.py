#!/usr/bin/env python3
"""Tests for the privacy proxy around the architectural seams: a fake upstream that speaks
the Responses SSE protocol, a deterministic vault, and the failure modes the proxy must
fail closed on. Run: python3 tests/test_codex_proxy.py (stdlib only)."""

from __future__ import annotations

import http.client
import json
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codex_proxy import MapPolicy, Proxy, StreamRestorer, walk_strings  # noqa: E402

MAPPING = {"Alice Example": "NAME_001", "9876543210": "PHONE_001", "SecretVillage": "PLACE_001",
           "Ramesh Kumar": "NAME_002", "Ramesh": "NAME_003", "Zoë Müller": "NAME_004"}


class FakeUpstream:
    """Records what it received; answers with whatever the test queued, in the chunks given."""

    def __init__(self) -> None:
        self.received: list[dict] = []
        self.script: list[tuple[str, int, list[bytes]]] = []   # (content-type, status, chunks)
        srv = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_GET(self):  # noqa: N802
                self._go()

            def do_POST(self):  # noqa: N802
                self._go()

            def _go(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                srv.received.append({"path": self.path, "headers": dict(self.headers), "body": raw})
                ctype, status, chunks = srv.script.pop(0) if srv.script else ("application/json", 200, [b"{}"])
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Connection", "close")
                self.end_headers()
                for c in chunks:
                    self.wfile.write(c)
                    self.wfile.flush()
                    time.sleep(0.02)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.server.shutdown()


def sse(events: list[dict]) -> bytes:
    return b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)


def post(port: int, path: str, body, headers: dict | None = None, raw: bytes | None = None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    data = raw if raw is not None else json.dumps(body).encode()
    h = {"Content-Type": "application/json", "Authorization": "Bearer test-token-not-real"}
    h.update(headers or {})
    c.request("POST", path, body=data, headers=h)
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


class RestorerTests(unittest.TestCase):
    def setUp(self):
        self.p = MapPolicy(MAPPING)

    def test_token_split_across_chunks(self):
        r = StreamRestorer(self.p.inbound)
        out = r.feed("Found NAME_0") + r.feed("01 in the file") + r.flush()
        self.assertEqual(out, "Found Alice Example in the file")

    def test_split_at_underscore_and_single_letters(self):
        r = StreamRestorer(self.p.inbound)
        pieces = ["see P", "HONE", "_", "0", "0", "1 now"]
        out = "".join(r.feed(x) for x in pieces) + r.flush()
        self.assertEqual(out, "see 9876543210 now")

    def test_uppercase_word_is_not_lost(self):
        r = StreamRestorer(self.p.inbound)
        out = r.feed("the NGO") + r.flush()
        self.assertEqual(out, "the NGO")

    def test_no_boundary_before_tail_means_no_hold(self):
        r = StreamRestorer(self.p.inbound)
        # "xNAME_001" is not a token (no word boundary), so nothing should be held back
        out = r.feed("xNAME_0") + r.feed("01")
        self.assertEqual(out, "xNAME_001")

    def test_unknown_placeholder_passes_through(self):
        r = StreamRestorer(self.p.inbound)
        out = r.feed("WHATEVER_999 and NAME_001") + r.flush()
        self.assertEqual(out, "WHATEVER_999 and Alice Example")


class WalkTests(unittest.TestCase):
    def test_structural_keys_untouched_and_role_propagates(self):
        seen = []
        body = {"model": "NAME_001", "input": [{"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "hi Alice Example"}]},
                {"type": "function_call_output", "call_id": "c1", "output": "phone 9876543210"}]}
        out = walk_strings(body, lambda t, r, k: (seen.append((t, r, k)), t.upper())[1])
        self.assertEqual(out["model"], "NAME_001")
        self.assertEqual(out["input"][0]["content"][0]["text"], "HI ALICE EXAMPLE")
        self.assertIn(("hi Alice Example", "user", "text"), seen)
        self.assertIn(("phone 9876543210", None, "output"), seen)


class ProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.up = FakeUpstream()
        cls.lines = []
        cls.proxy = Proxy(MapPolicy(MAPPING), upstream=f"http://127.0.0.1:{cls.up.port}", log=cls.lines.append)
        cls.port = cls.proxy.start()

    @classmethod
    def tearDownClass(cls):
        cls.proxy.stop()
        cls.up.stop()

    def setUp(self):
        self.up.received.clear()
        self.up.script.clear()

    def test_outbound_tokenises_and_inbound_restores_sse(self):
        self.up.script.append(("text/event-stream", 200, [sse([
            {"type": "response.created", "response": {"id": "r1"}},
            {"type": "response.output_text.delta", "item_id": "m1", "output_index": 0, "content_index": 0, "delta": "NAME_001 lives in "},
            {"type": "response.output_text.delta", "item_id": "m1", "output_index": 0, "content_index": 0, "delta": "PLACE_001, phone PHONE_001."},
            {"type": "response.output_item.done", "item": {"type": "message", "content": [{"type": "output_text", "text": "NAME_001 lives in PLACE_001, phone PHONE_001."}]}},
            {"type": "response.completed", "response": {"id": "r1", "usage": {"total_tokens": 3}}},
        ])]))
        body = {"model": "gpt", "stream": True, "instructions": "be brief",
                "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Find every reference to Alice Example, phone 9876543210, in SecretVillage"}]}]}
        status, _h, data = post(self.port, "/backend-api/codex/responses", body)
        self.assertEqual(status, 200)
        sent = json.loads(self.up.received[0]["body"])
        self.assertEqual(sent["input"][0]["content"][0]["text"], "Find every reference to NAME_001, phone PHONE_001, in PLACE_001")
        self.assertNotIn(b"Alice", self.up.received[0]["body"])
        self.assertEqual(self.up.received[0]["headers"].get("Authorization"), "Bearer test-token-not-real")   # auth passed through untouched
        text = data.decode()
        self.assertIn("Alice Example lives in ", text)
        self.assertIn("SecretVillage, phone 9876543210.", text)
        self.assertNotIn("NAME_001", text)
        events = [json.loads(ln[5:]) for ln in text.split("\n") if ln.startswith("data:")]
        self.assertEqual(events[-1]["type"], "response.completed")
        self.assertEqual(events[-2]["item"]["content"][0]["text"], "Alice Example lives in SecretVillage, phone 9876543210.")
        entry = json.loads(self.lines[-1])
        self.assertEqual(entry["subs"], 1)
        self.assertGreaterEqual(entry["restored"], 2)
        self.assertNotIn("Alice", self.lines[-1])
        self.assertNotIn("test-token", self.lines[-1])

    def test_token_split_across_sse_chunks_is_restored(self):
        ev1 = {"type": "response.output_text.delta", "item_id": "m1", "output_index": 0, "content_index": 0, "delta": "It is NAME_0"}
        ev2 = {"type": "response.output_text.delta", "item_id": "m1", "output_index": 0, "content_index": 0, "delta": "01 again"}
        done = {"type": "response.completed", "response": {"id": "r"}}
        self.up.script.append(("text/event-stream", 200, [sse([ev1]), sse([ev2]), sse([done])]))
        status, _h, data = post(self.port, "/backend-api/codex/responses", {"input": []})
        self.assertEqual(status, 200)
        deltas = "".join(json.loads(ln[5:])["delta"] for ln in data.decode().split("\n") if ln.startswith("data:") and "delta" in ln)
        self.assertEqual(deltas, "It is Alice Example again")

    def test_held_tail_is_flushed_before_a_done_event(self):
        ev1 = {"type": "response.output_text.delta", "item_id": "m1", "output_index": 0, "content_index": 0, "delta": "ask NAME"}
        done = {"type": "response.output_item.done", "item": {"type": "message", "content": [{"type": "output_text", "text": "ask NAME"}]}}
        self.up.script.append(("text/event-stream", 200, [sse([ev1, done])]))
        _s, _h, data = post(self.port, "/backend-api/codex/responses", {"input": []})
        deltas = "".join(json.loads(ln[5:])["delta"] for ln in data.decode().split("\n") if ln.startswith("data:") and "delta" in ln)
        self.assertEqual(deltas, "ask NAME")

    def test_function_call_arguments_and_tool_outputs(self):
        self.up.script.append(("text/event-stream", 200, [sse([
            {"type": "response.function_call_arguments.delta", "item_id": "f1", "output_index": 0, "delta": "{\"cmd\":\"grep NAME_"},
            {"type": "response.function_call_arguments.delta", "item_id": "f1", "output_index": 0, "delta": "001 data.csv\"}"},
            {"type": "response.output_item.done", "item": {"type": "function_call", "name": "shell", "call_id": "c1", "arguments": "{\"cmd\":\"grep NAME_001 data.csv\"}"}},
            {"type": "response.completed", "response": {}},
        ])]))
        body = {"input": [{"type": "function_call_output", "call_id": "c0", "output": "name,phone\nAlice Example,9876543210\nRamesh Kumar,1\n"}]}
        _s, _h, data = post(self.port, "/backend-api/codex/responses", body)
        sent = json.loads(self.up.received[0]["body"])
        self.assertEqual(sent["input"][0]["output"], "name,phone\nNAME_001,PHONE_001\nNAME_002,1\n")
        text = data.decode()
        events = [json.loads(ln[5:]) for ln in text.split("\n") if ln.startswith("data:")]
        self.assertEqual("".join(e["delta"] for e in events if "delta" in e), "{\"cmd\":\"grep Alice Example data.csv\"}")
        self.assertEqual(events[2]["item"]["arguments"], "{\"cmd\":\"grep Alice Example data.csv\"}")
        self.assertEqual(events[2]["item"]["name"], "shell")   # structural, untouched

    def test_apply_patch_custom_tool_stream_is_restored(self):
        # the model adds a file through the apply_patch custom tool: the streamed input, the
        # input.done and the item all come back with real column names
        p = Proxy(MapPolicy({"village": "PLACE_052", "gps_lat": "GPS_004"}), upstream=f"http://127.0.0.1:{self.up.port}", log=lambda s: None)
        port = p.start()
        try:
            patch = '*** Begin Patch\n*** Add File: build.py\n+place = row.get("PLACE_052", "")\n+lat = float(row.get("GPS_004"))\n*** End Patch'
            self.up.script.append(("text/event-stream", 200, [sse([
                {"type": "response.custom_tool_call_input.delta", "item_id": "i1", "output_index": 0, "delta": '+place = row.get("PLACE_0'},
                {"type": "response.custom_tool_call_input.delta", "item_id": "i1", "output_index": 0, "delta": '52", "")\n'},
                {"type": "response.custom_tool_call_input.done", "item_id": "i1", "output_index": 0, "input": patch},
                {"type": "response.output_item.done", "item": {"type": "custom_tool_call", "name": "apply_patch", "call_id": "c1", "input": patch}},
                {"type": "response.completed", "response": {"id": "r"}},
            ])]))
            _s, _h, data = post(port, "/backend-api/codex/responses", {"input": []})
            events = [json.loads(l[5:]) for l in data.decode().split("\n") if l.startswith("data:")]
            self.assertEqual("".join(e["delta"] for e in events if "delta" in e), '+place = row.get("village", "")\n')
            self.assertIn('row.get("gps_lat")', events[-2]["item"]["input"])
            self.assertNotIn("PLACE_052", data.decode())
        finally:
            p.stop()

    def test_overlapping_values_longest_first_and_unicode(self):
        self.up.script.append(("application/json", 200, [b"{\"ok\":true}"]))
        body = {"input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Ramesh Kumar and Ramesh and Zoë Müller went"}]}]}
        post(self.port, "/backend-api/codex/responses/compact", body)
        sent = json.loads(self.up.received[0]["body"].decode("utf-8"))
        self.assertEqual(sent["input"][0]["content"][0]["text"], "NAME_002 and NAME_003 and NAME_004 went")

    def test_json_reply_is_restored(self):
        self.up.script.append(("application/json", 200, [b"{\"output\":[{\"text\":\"NAME_004 ok\"}]}"]))
        _s, _h, data = post(self.port, "/backend-api/codex/responses/compact", {"input": []})
        self.assertEqual(json.loads(data)["output"][0]["text"], "Zoë Müller ok")

    def test_websocket_upgrade_gets_426(self):
        status, _h, _d = post(self.port, "/backend-api/codex/responses", {}, headers={"Upgrade": "websocket", "Connection": "Upgrade"})
        self.assertEqual(status, 426)
        self.assertEqual(len(self.up.received), 0)

    def test_unknown_path_is_refused(self):
        status, _h, _d = post(self.port, "/backend-api/codex/anything-else", {"input": []})
        self.assertEqual(status, 403)
        self.assertEqual(len(self.up.received), 0)

    def test_passthrough_paths_are_forwarded_untransformed(self):
        self.up.script.append(("application/json", 200, [b"{\"plan\":\"plus\"}"]))
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", "/backend-api/wham/accounts/check", headers={"Authorization": "Bearer x"})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertEqual(r.read(), b"{\"plan\":\"plus\"}")
        self.assertEqual(self.up.received[0]["path"], "/backend-api/wham/accounts/check")

    def test_bad_json_and_unknown_encoding_never_reach_upstream(self):
        status, _h, _d = post(self.port, "/backend-api/codex/responses", None, raw=b"\x00\xffnot json")
        self.assertEqual(status, 400)
        status, _h, _d = post(self.port, "/backend-api/codex/responses", {"input": []}, headers={"Content-Encoding": "br"})
        self.assertEqual(status, 415)
        self.assertEqual(len(self.up.received), 0)

    def test_upstream_error_is_relayed(self):
        self.up.script.append(("application/json", 401, [b"{\"error\":{\"message\":\"NAME_001 bad token\"}}"]))
        status, _h, data = post(self.port, "/backend-api/codex/responses", {"input": []})
        self.assertEqual(status, 401)
        self.assertIn("Alice Example bad token", data.decode())

    def test_upstream_down_is_a_visible_error_not_a_bypass(self):
        dead = Proxy(MapPolicy(MAPPING), upstream="http://127.0.0.1:9", log=lambda s: None)
        port = dead.start()
        try:
            status, _h, data = post(port, "/backend-api/codex/responses", {"input": []})
            self.assertEqual(status, 502)
            self.assertIn("io proxy", data.decode())
        finally:
            dead.stop()

    def test_not_ready_refuses_everything(self):
        class Gate(MapPolicy):
            def ready(self):
                return False
        p = Proxy(Gate(MAPPING), upstream=f"http://127.0.0.1:{self.up.port}", log=lambda s: None)
        port = p.start()
        try:
            status, _h, data = post(port, "/backend-api/codex/responses", {"input": []})
            self.assertEqual(status, 403)
            self.assertIn("not been approved", data.decode())
            self.assertEqual(len(self.up.received), 0)
        finally:
            p.stop()

    def test_protocol_constants_are_not_leaks(self):
        # a vault value that equals a protocol word must not stop requests
        p = Proxy(MapPolicy({"Auto": "NAME_009", "Alice Example": "NAME_001"}), upstream=f"http://127.0.0.1:{self.up.port}", log=lambda s: None)
        port = p.start()
        try:
            self.up.script.append(("application/json", 200, [b"{}"]))
            body = {"tool_choice": "auto", "reasoning": {"summary": "auto"}, "text": {"format": {"type": "text"}},
                    "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello Alice Example"}]}]}
            status, _h, _d = post(port, "/backend-api/codex/responses/compact", body)
            self.assertEqual(status, 200)
            sent = json.loads(self.up.received[0]["body"])
            self.assertEqual(sent["tool_choice"], "auto")
            self.assertEqual(sent["input"][0]["content"][0]["text"], "hello NAME_001")
        finally:
            p.stop()

    def test_leak_check_stops_a_request(self):
        class Leaky(MapPolicy):
            def outbound(self, text, role):
                return text            # a broken transform: nothing replaced
        p = Proxy(Leaky(MAPPING), upstream=f"http://127.0.0.1:{self.up.port}", log=lambda s: None)
        port = p.start()
        try:
            lines = []
            p.log = lines.append
            status, _h, data = post(port, "/backend-api/codex/responses", {"input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Alice Example"}]}]})
            self.assertEqual(status, 403)
            self.assertIn("about to leave", data.decode())
            self.assertEqual(len(self.up.received), 0)
            entry = json.loads(lines[-1])
            self.assertEqual(entry["leaks"], [{"code": "NAME_001", "keys": ["text"]}])
            self.assertNotIn("Alice", lines[-1])
        finally:
            p.stop()


    def test_cache_is_invalidated_when_the_vault_grows(self):
        # The exact failure seen live on 2026-09-14: a string transformed under an older
        # vault (cached) still holds a value that was minted later from another string.
        class Growing(MapPolicy):
            def __init__(self):
                super().__init__({"Alice Example": "NAME_001"})
                self.v = 1

            def grow(self):
                self.__init__.__func__(self) if False else None
                MapPolicy.__init__(self, {"Alice Example": "NAME_001", "Kiran Demo": "NAME_002"})
                self.v = 2

            def version(self):
                return self.v

        pol = Growing()
        p = Proxy(pol, upstream=f"http://127.0.0.1:{self.up.port}", log=lambda s: None)
        port = p.start()
        try:
            self.up.script.append(("application/json", 200, [b"{}"]))
            self.up.script.append(("application/json", 200, [b"{}"]))
            body = {"instructions": "notes about Kiran Demo", "input": []}
            post(port, "/backend-api/codex/responses/compact", body)
            self.assertEqual(json.loads(self.up.received[0]["body"])["instructions"], "notes about Kiran Demo")
            pol.grow()
            status, _h, _d = post(port, "/backend-api/codex/responses/compact", body)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(self.up.received[1]["body"])["instructions"], "notes about NAME_002")
        finally:
            p.stop()

    def test_vault_growing_during_one_request_is_applied_to_the_whole_body(self):
        # instructions (transformed first) mention a word that the "scanner" only mints a
        # code for when it reaches the user message; the walk must run again
        class Minting(MapPolicy):
            def __init__(self):
                super().__init__({})
                self.v = 0

            def outbound(self, text, role):
                if role == "user" and "Kiran Demo" in text and "Kiran Demo" not in self.forward:
                    MapPolicy.__init__(self, {"Kiran Demo": "NAME_001"})
                    self.v += 1
                return MapPolicy.outbound(self, text, role)

            def version(self):
                return self.v

        p = Proxy(Minting(), upstream=f"http://127.0.0.1:{self.up.port}", log=lambda s: None)
        port = p.start()
        try:
            self.up.script.append(("application/json", 200, [b"{}"]))
            body = {"instructions": "notes about Kiran Demo", "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "who is Kiran Demo"}]}]}
            status, _h, _d = post(port, "/backend-api/codex/responses/compact", body)
            self.assertEqual(status, 200)
            sent = json.loads(self.up.received[0]["body"])
            self.assertEqual(sent["instructions"], "notes about NAME_001")
            self.assertEqual(sent["input"][0]["content"][0]["text"], "who is NAME_001")
        finally:
            p.stop()

    def test_multi_turn_history_is_cached_and_consistent(self):
        self.up.script.append(("application/json", 200, [b"{}"]))
        self.up.script.append(("application/json", 200, [b"{}"]))
        turn1 = {"input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "who is Alice Example"}]}]}
        post(self.port, "/backend-api/codex/responses/compact", turn1)
        turn2 = {"input": turn1["input"] + [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Alice Example is in SecretVillage"}]}]}
        post(self.port, "/backend-api/codex/responses/compact", turn2)
        a = json.loads(self.up.received[0]["body"])["input"][0]["content"][0]["text"]
        b = json.loads(self.up.received[1]["body"])["input"]
        self.assertEqual(a, "who is NAME_001")
        self.assertEqual(b[0]["content"][0]["text"], "who is NAME_001")
        self.assertEqual(b[1]["content"][0]["text"], "NAME_001 is in PLACE_001")



class LiveVaultPolicyTests(unittest.TestCase):
    """The service's policy shape, driven with the real engine (PseudonymMap + regex
    validators) but no scanner model: known values from the vault, unseen phone numbers
    minted by the general rule, kept values left alone, tokens restored."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
        from pseudonymize import PseudonymMap, redact_text  # noqa: PLC0415
        from detect import regex_engine  # noqa: PLC0415
        self.pmap = PseudonymMap(None)
        self.pmap.token("Alice Example", "person_name")
        self.pmap.token("SecretVillage", "village")
        kept = {"9000000000"}
        direct = {"person_name", "phone", "email", "aadhaar", "pan", "bank_account", "ifsc", "upi_id",
                  "ration_card", "voter_id", "vehicle_number", "address", "village"}
        pm, rt = self.pmap, redact_text

        class Live(MapPolicy):
            def __init__(self):
                pass

            def outbound(self, text, role):
                def filt(t):
                    return [sp for sp in regex_engine(t) if t[sp[0]:sp[1]] not in kept]
                return rt(text, pm, filt, classes=direct)[0]

            def inbound(self, text):
                return pm.rehydrate(text)

            def leaks(self, text):
                known = pm.known_regex()
                return sorted({m.group(0) for m in known.finditer(text)}) if known else []

        self.policy = Live()

    def test_known_value_and_general_rule_and_kept(self):
        out = self.policy.outbound("Alice Example (9876543210) and Ravi Test (9000000000) in SecretVillage", "user")
        self.assertEqual(out, "NAME_001 (PHONE_001) and Ravi Test (9000000000) in PLACE_001")
        self.assertEqual(self.pmap.display["PHONE_001"], "9876543210")      # minted by the phone rule
        self.assertEqual(self.policy.inbound("call PHONE_001 about NAME_001"), "call 9876543210 about Alice Example")

    def test_unknown_name_is_not_invented_without_a_scanner(self):
        # No scanner in this test: an unseen person name is not a "general rule" hit, so it
        # passes (the service adds GLiNER for role=user text; that is the policy's decision,
        # not the proxy's).
        self.assertEqual(self.policy.outbound("Ravi Test went home", None), "Ravi Test went home")

    def test_leaks_reports_known_values_only(self):
        self.assertEqual(self.policy.leaks("Alice Example and Nobody"), ["Alice Example"])
        self.assertEqual(self.policy.leaks("NAME_001 and Nobody"), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
