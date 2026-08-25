#!/usr/bin/env python3
"""Privacy shield: a local redacting reverse proxy for Antigravity.

    CLOUD_CODE_URL=http://127.0.0.1:8765 agy ...      (CLI)
    CLOUD_CODE_URL=http://127.0.0.1:8765 antigravity  (IDE launched from a shell)

Outbound (request.contents):
  * Every string part is classified: TABLE (CSV-like, with or without line-number
    prefixes), DATA (prose that came from a user file), CODE/SHELL (program text,
    directory listings, command output). TABLE goes through the validated column
    classifier and column-wise tokenisation. DATA goes through validators + GLiNER
    with a case-insensitive name pass. CODE/SHELL gets vault substitution and
    validators only, so junk never grows the vault.
  * --numbers N also hides every run of N+ digits inside DATA/TABLE parts.
  * --always-hide FILE seeds the vault with names/values that must always be hidden.
  * Results are cached by hash; conversation history costs nothing on later calls.
  * In-chat review (--review chat): the first time a TABLE is seen, the proxy
    answers the IDE itself with the proposed column list and waits for the user
    to reply "ok" / "also hide X, Y" / "don't hide Z" before anything leaves.

Inbound: SSE stream rehydrated with a hold-back buffer; --annotate appends a
timing footer to each answer; peek mode (/shield/peek?on=1) disables
rehydration so the user can see what the model really saw.

Status pages: /shield/status, /shield/vault, /shield/last-request (wire view).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import http.server
import io
import json
import os
import re
import ssl
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from columns import classify_columns  # noqa: E402
from detect import build_engine, regex_engine  # noqa: E402
from pseudonymize import PseudonymMap, TOKEN_RE, pseudonymise_frame, redact_text  # noqa: E402

UPHOST = "daily-cloudcode-pa.googleapis.com"
SKIP_KEYS = {"thoughtSignature", "id", "name", "role", "model", "project", "requestId", "sessionId", "userAgent",
             "requestType", "AbsolutePath", "Cwd", "SearchDirectory", "TargetFile", "FilePath", "Pattern",
             "PathToDelete", "mimeType"}
DIRECT = {"person_name", "phone", "email", "aadhaar", "pan", "bank_account", "ifsc", "upi_id",
          "ration_card", "voter_id", "vehicle_number", "address", "village", "gps"}
# In prose the span model may only propose these; every other identifier class has a
# validator (regex/checksum) and the model's guesses for them are mostly junk.
MODEL_PROSE_CLASSES = {"person_name", "village", "address"}
# Validator-backed identifier classes that are hidden even inside columns the user
# kept: keeping a column means keeping its subject matter, not leaking checksummed
# identifiers that ended up there (mangled headers, nested tables, notes columns).
KEPT_SWEEP = {"email", "aadhaar", "pan", "ifsc", "upi_id", "phone", "voter_id", "vehicle_number"}


def KEPT_SWEEP_ENGINE(text):
    return [s for s in regex_engine(text) if s[2] in KEPT_SWEEP]
# two to four words, each Capitalised, ALLCAPS or an initial ("Gurleen Siddiqui",
# "GURLEEN SIDDIQUI", "M. X. Verma"); lowercase names are caught by the title-cased pass
ROLE_PREFIX = re.compile(r"^(?:guardian|mr|mrs|ms|dr|shri|smt|sri|contact person|contact|person|father|mother|parent)\.?\s+", re.I)
LOOSE_NAME = re.compile(r"^[A-Za-z][A-Za-z.'-]*(?:\s[A-Za-z][A-Za-z.'-]*){0,3}$")
COMMON_WORDS = {"family", "school", "office", "village", "district", "block", "taluka", "total", "status", "pending",
                "approved", "rejected", "disbursed", "review", "scheme", "scholarship", "certificate", "income",
                "caste", "bank", "account", "number", "mobile", "phone", "email", "name", "unknown", "none", "null"}
NAME_SHAPE = re.compile(r"^(?:[A-Z][a-z]+|[A-Z]{2,}|[A-Z]\.?)(?:\s(?:[A-Z][a-z]+|[A-Z]{2,}|[A-Z]\.?)){1,3}$")
LINE_NO = re.compile(r"^(\d+): ", re.M)
FOOTER = re.compile(r"\n*_shield: [^\n]*_\s*$")
CODE_HINT = re.compile(r"^\s*(def |class |import |from \S+ import|#include|function |const |let |var |\{|\}|</?\w+>|<\?xml)|;\s*$|=>|\(\)\s*\{", re.M)
# directory listings, prompts, ps output, or unix paths with letters (never dates like 01/03/26)
SHELL_HINT = re.compile(r"^(total \d+|[d-][rwx-]{9}\s|\$ |PID\s|USER\s+PID)|(?<![\w/])[A-Za-z~.][\w.-]*/[A-Za-z][\w.-]*/[\w.-]+", re.M)
USER_REQ = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.S)

STATS: dict[str, Any] = {"calls": 0, "redact_ms_total": 0.0, "redact_ms_last": 0.0, "spans_total": 0,
                         "cache_hits": 0, "cache_misses": 0, "bytes_out": 0, "upstream_ms_total": 0.0,
                         "blocked": 0, "reviews": 0, "started": time.time(), "last": None}
LOCK = threading.Lock()
LAST_REQUEST: dict[str, Any] = {"body": "", "path": "", "when": None}
PEEK = {"on": False}


def kind_of(text: str) -> str:
    lines = [LINE_NO.sub("", l) for l in text.splitlines() if l.strip()]
    if len(lines) >= 3:
        for sep in (",", "\t"):
            try:
                widths = [len(r) for r in csv.reader(lines[:40], delimiter=sep)]
            except csv.Error:
                continue
            if widths and widths[0] >= 3 and sum(w == widths[0] for w in widths) >= 0.8 * len(widths):
                return "table"
    if len(CODE_HINT.findall(text)) >= 3 or len(SHELL_HINT.findall(text)) >= 3:
        return "code"
    return "data"


class Shield:
    def __init__(self, engine_spec: str, vault_path: Path, numbers: int | None, always_hide: Path | None,
                 review: str) -> None:
        self.span_engine = build_engine(engine_spec)
        self.vault = PseudonymMap(vault_path)
        self.cache: dict[str, str] = {}
        self.headers: set[str] = set()   # column names seen in any table: never identifiers
        self.hidden_headers: dict[str, str] = {}   # header (lower) -> class, from reviewed tables
        self.numbers = numbers
        self.review = review
        self.pending: dict[str, Any] | None = None   # in-chat review waiting for the user
        self.decisions_path = vault_path.with_name("shield-decisions-local-only.json")
        self.decisions: dict[str, dict[str, str]] = {}
        self.kept: set[str] = set()
        self.kept_long: set[str] = set()
        if self.decisions_path.exists():
            saved = json.loads(self.decisions_path.read_text())
            self.decisions = saved.get("decisions", saved) if isinstance(saved, dict) else {}
            self.decisions = {k: v for k, v in self.decisions.items() if k != "_kept"}
            kept = saved.get("_kept", []) if isinstance(saved, dict) else []
            self._kept_saved = set(kept)
        self.kept: set[str] = set(getattr(self, "_kept_saved", set()))   # kept-column values: allowed anywhere
        self.kept_long: set[str] = {v for v in self.kept if len(v) >= 4 and not v.replace(".", "").isdigit()}

        if always_hide and always_hide.exists():
            for line in always_hide.read_text().splitlines():
                value = line.strip()
                if value:
                    self.vault.token(value, "person_name")
            self.vault.save()

    # ---------------------------------------------------------------- engines
    def header_value_spans(self, text: str):
        """`Naam: Lalita` / `Mob = 98...` lines and `Name: X,` fragments where the key is a
        column the user chose to hide: the value gets that column's class whatever its shape."""
        spans = []
        if not self.hidden_headers:
            return spans
        keys = "|".join(re.escape(h) for h in sorted(self.hidden_headers, key=len, reverse=True))
        for m in re.finditer(rf"(?i)(?:^|[\s,;|(])({keys})\s*[:=]\s*([^\r\n,;|]{{2,80}}?)\s*(?=$|[\r\n,;|)])", text, re.M):
            value = m.group(2).strip().strip("'\"")
            if value and value.casefold() not in self.kept and not TOKEN_RE.search(value):
                start = m.start(2) + (len(m.group(2)) - len(m.group(2).lstrip()))
                spans.append((start, start + len(value), self.hidden_headers[m.group(1).casefold()], 1.0))
        return spans

    # deterministic name shapes the span model is unsure about: initials ("L. H. Dubey",
    # "U.K. Shinde") and a capitalised word between a contact cue and a phone/email
    INITIALS_NAME = re.compile(r"\b(?:[A-Z]\.\s?){1,3}[A-Z][a-z]{2,}\b")
    CUE_NAME = re.compile(r"(?i)(?:with|contact(?: person)?|call|guardian|parent|father|mother)\s+((?-i:[A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})?))\s*(?=(?:at|on|,|\(|-)\s*(?:\+?\d|[A-Z]+_\d|[\w.+-]+@))")

    # WhatsApp/Signal export line: "dd/mm/yy, hh:mm - Sender Name: message"
    CHAT_LINE = re.compile(r"^\[?\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}(?::\d{2})?(?: [AP]M)?\]? ?- ([^:\n]{2,60}):", re.M)

    def data_engine(self, text: str, single_min: float = 0.65):
        spans = [sp for sp in regex_engine(text) if sp[1] - sp[0] >= 4] + self.header_value_spans(text)
        spans += [(m.start(1), m.end(1), "person_name", 1.0) for m in self.CHAT_LINE.finditer(text)]
        spans += [(m.start(), m.end(), "person_name", 0.9) for m in self.INITIALS_NAME.finditer(text)]
        spans += [(m.start(1), m.end(1), "person_name", 0.9) for m in self.CUE_NAME.finditer(text)
                  if m.group(1).casefold() not in COMMON_WORDS]
        seen = set()
        for variant in (text, text.title()):
            for start, end, label, score in self.span_engine(variant):
                value = text[start:end]
                if label not in MODEL_PROSE_CLASSES or score < 0.45 or (start, end) in seen or end - start < 4:
                    continue
                if "\n" in value or "\r" in value:
                    continue
                if "/" in value or re.search(r"[0-9a-f]{8}-[0-9a-f]{4}", value):
                    continue  # paths and uuids are not identifiers
                low = value.casefold().strip()
                if low in self.headers or low in self.kept:
                    continue  # column headers / values from kept columns are not identifiers
                if any(len(k) >= 4 and (k in low or low in k) for k in self.kept_long):
                    continue  # overlaps a kept value ("Pune district", scheme names)
                if label == "person_name":
                    # strip leading role words, then accept letters-only names of 1-4 words;
                    # a single word needs higher confidence (the model finds "Pradeep",
                    # "gurmeet shinde", "L. H. Dubey"; the old strict shape threw them away)
                    m_role = ROLE_PREFIX.match(value)
                    if m_role:
                        start += m_role.end(); value = value[m_role.end():]
                    if not LOOSE_NAME.match(value):
                        continue
                    if " " not in value and score < single_min:
                        continue
                    if value.casefold() in COMMON_WORDS:
                        continue
                seen.add((start, end))
                spans.append((start, end, label, score))
        if self.numbers:
            spans += [(m.start(), m.end(), "long_number", 1.0)
                      for m in re.finditer(rf"(?<![\d-])(?:\d ?){{{self.numbers - 1},}}\d(?![\d-])", text)]
        # a name found once is a name everywhere in this text, whatever the casing
        found = {text[a:b] for a, b, lab, _ in spans if lab == "person_name" and b - a >= 4}
        covered = {(a, b) for a, b, _, _ in spans}
        for value in found:
            for m in re.finditer(rf"(?<![\w]){re.escape(value)}(?![\w])", text, flags=re.I):
                if (m.start(), m.end()) not in covered:
                    spans.append((m.start(), m.end(), "person_name", 0.9)); covered.add((m.start(), m.end()))
        return spans

    def cell_engine(self, text: str):
        """Free-text cells inside tables: names and validator-backed identifiers only.
        Place/address guesses on short cells produce junk ('shifted house')."""
        return [sp for sp in self.data_engine(text, single_min=0.45) if sp[2] not in ("village", "address")]

    def code_engine(self, text: str):
        return list(regex_engine(text))

    # ----------------------------------------------------------------- tables
    def parse_table(self, text: str) -> tuple[pd.DataFrame, list[str], str]:
        prefixes = LINE_NO.findall(text)
        raw = "\n".join(l.strip() for l in LINE_NO.sub("", text).split("\n"))
        sep = "\t" if raw.count("\t") > raw.count(",") else ","
        frame = pd.read_csv(io.StringIO(raw), dtype=str, keep_default_na=False, sep=sep, skip_blank_lines=False)
        return frame, prefixes, sep

    def save_decisions(self) -> None:
        self.decisions_path.write_text(json.dumps({"decisions": self.decisions, "_kept": sorted(self.kept)}, indent=1))

    def header_key(self, text: str) -> str:
        """Decisions are keyed by the column-header signature, so an approved table is
        never re-asked when it reappears inside other text (a page, a log, a reread)."""
        try:
            frame, _, _ = self.parse_table(text)
            return "hdr:" + hashlib.sha256("|".join(str(c).casefold().strip() for c in frame.columns).encode()).hexdigest()
        except Exception:
            return "hdr:" + hashlib.sha256(text[:200].encode()).hexdigest()

    def propose(self, text: str) -> dict[str, dict[str, Any]]:
        frame, _, _ = self.parse_table(text)
        self.headers.update(str(c).casefold().strip() for c in frame.columns)
        return classify_columns(frame, self.span_engine)

    def redact_table(self, text: str, classes: dict[str, str]) -> tuple[str, int]:
        frame, prefixes, sep = self.parse_table(text)
        # a column whose values the user already keeps elsewhere is kept here too
        for c in list(classes):
            if classes[c] not in ("none", "record_id_non_pii", "age") and c in frame.columns:
                vals = [str(v).casefold().strip() for v in frame[c].unique() if str(v).strip()]
                if vals and self.kept and sum(v in self.kept for v in vals) >= 0.8 * len(vals):
                    classes[c] = "none"
        self.headers.update(str(c).casefold().strip() for c in frame.columns)
        for c, cls in classes.items():
            if cls not in ("none", "record_id_non_pii", "age", "dob", "gps", "free_text_with_pii"):
                self.hidden_headers[str(c).casefold().strip()] = cls
            if cls in ("none", "record_id_non_pii", "age") and c in frame.columns:
                vals = {str(v).casefold().strip() for v in frame[c].unique() if str(v).strip()}
                if vals - self.kept:
                    self.kept.update(vals)
                    self.kept_long.update(v for v in vals if len(v) >= 4 and not v.replace(".", "").isdigit())
                    self.save_decisions()
        before = len(self.vault.display)
        shadow = pseudonymise_frame(frame, classes, self.vault, self.cell_engine, kept_validator=KEPT_SWEEP_ENGINE)
        if self.numbers:
            shadow = shadow.map(lambda v: re.sub(rf"(?<![\d-])(?:\d ?){{{self.numbers - 1},}}\d(?![\d-])",
                                                 lambda m: self.vault.token(m.group(0), "long_number"), v)
                                if isinstance(v, str) else v)
        out = shadow.to_csv(index=False, sep=sep, lineterminator="\n")
        out = redact_text(out, self.vault, None)[0]   # hidden anywhere => hidden everywhere
        if prefixes:
            lines = out.splitlines()
            out = "\n".join(f"{n}: {l}" for n, l in zip(prefixes, lines)) + ("\n" if text.endswith("\n") else "")
        return out, len(self.vault.display) - before

    # ---------------------------------------------------------------- strings
    def parses_as_table(self, block: str) -> bool:
        """A block is a table only if pandas parses it AND the header is credible:
        mostly named columns (not 'Unnamed: n'), short header cells, no duplicate
        names, at least two data rows. Tracebacks, command errors and prose with
        commas fail this and are treated as text."""
        try:
            frame, _, _ = self.parse_table(block)
        except Exception:
            return False
        cols = [str(c) for c in frame.columns]
        if len(cols) < 3 or len(frame) < 2:
            return False
        unnamed = sum(c.startswith("Unnamed") or not c.strip() for c in cols)
        if unnamed > len(cols) * 0.3 or any(len(c) > 48 for c in cols) or len(set(c.casefold() for c in cols)) < len(cols):
            return False
        if sum(bool(re.search(r"[.!?]\s|\b(error|failed|traceback|exception)\b", c, re.I)) for c in cols):
            return False
        # header cells must read like labels, not like data: no quotes/brackets, not
        # numeric, not phone/date/email shaped (tuple-printed rows fail here)
        def label_like(c: str) -> bool:
            c = c.strip()
            if not c or c[0] in "'\"([{" or c[-1] in "'\")]}":
                return False
            if re.fullmatch(r"[-+]?\d[\d., ]*", c) or re.search(r"\d{2}[-/]\d{2}[-/]\d{2,4}|@|\+91", c):
                return False
            return bool(re.search(r"[A-Za-z]", c))
        if sum(label_like(c) for c in cols) < 0.7 * len(cols):
            return False
        return True

    def split_table(self, text: str) -> tuple[str, str, str] | None:
        found = self._split_table(text)
        return found if found and self.parses_as_table(found[1]) else None

    def _split_table(self, text: str) -> tuple[str, str, str] | None:
        """Find a CSV/TSV block inside a tool result: returns (preamble, table, rest)."""
        lines = text.split("\n")
        stripped = [LINE_NO.sub("", l).strip() for l in lines]
        for sep in (",", "\t"):
            for start in range(min(len(lines), 15)):
                try:
                    widths = [len(r) for r in csv.reader(stripped[start:start + 40], delimiter=sep)]
                except csv.Error:
                    continue
                if not widths or widths[0] < 3:
                    continue
                run = 0
                for w in widths:
                    if w == widths[0]:
                        run += 1
                    else:
                        break
                header_cells = [c.strip().strip('"') for c in stripped[start].split(sep)]
                if any(len(c) > 40 for c in header_cells):
                    continue   # sentence fragments with commas are not a table header
                header_known = header_cells[0].casefold() in self.headers
                if run < 3 and not header_known:
                    continue
                end = start + run
                # extend through remaining consistent lines beyond the 40-line probe
                for i, l in enumerate(stripped[end:], end):
                    try:
                        if not l.strip() or len(next(csv.reader([l], delimiter=sep))) != widths[0]:
                            break
                    except csv.Error:
                        break
                    end = i + 1
                return "\n".join(lines[:start]) + ("\n" if start else ""), "\n".join(lines[start:end]), \
                    ("\n" if end < len(lines) else "") + "\n".join(lines[end:])
        return None

    # A capitalised run right before a bracket of already-hidden identifiers is a
    # contact line ("Surveyor: Anita Kulkarni (EMAIL_004, PHONE_019)"): the span
    # model sometimes misses the name in noisy extractor output, but the shape is
    # deterministic once the identifiers next to it are tokens.
    CONTACT_NAME = re.compile(
        r"((?![A-Z_]+\\?_\d)[A-Z][\w'.-]+(?:\s+(?![A-Z_]+\\?_\d)[A-Z][\w'.-]+){1,3})"
        r"(?=\s*(?:[(\[][^()\[\]]{0,60}|(?:at|on|:|,|-)\s*)(?:EMAIL|PHONE|AADHAAR|PAN|ACCOUNT|VOTER|UPI)\\?_\d)")

    def _hide_contact_names(self, text: str) -> str:
        return self.CONTACT_NAME.sub(lambda m: self.vault.token(m.group(1), "person_name"), text)

    def redact_string(self, text: str) -> tuple[str, int, bool]:
        if len(text) < 3:
            return text, 0, True
        text = FOOTER.sub("", text)
        key = hashlib.sha256(text.encode()).hexdigest()
        if key in self.cache:
            # vault may have grown since this part was cached: re-apply known values only
            return redact_text(self.cache[key], self.vault, None)[0], 0, True
        split = self.split_table(text)
        if split:
            pre, table, rest = split
            try:
                classes = self.decisions.get(self.header_key(table)) or {c: v["class"] for c, v in self.propose(table).items()}
                redacted, spans = self.redact_table(table, classes)
                pre_r, e1 = redact_text(pre, self.vault, self.data_engine, classes=DIRECT | {"long_number"})
                rest_r, e2 = redact_text(rest, self.vault, self.data_engine, classes=DIRECT | {"long_number"})
                out = self._hide_contact_names(pre_r + redacted + rest_r)
                self.cache[key] = out
                return out, spans + len(e1) + len(e2), False
            except Exception:
                pass
        kind = kind_of(text)
        engine = self.data_engine if kind == "data" else self.code_engine
        redacted, events = redact_text(text, self.vault, engine, classes=DIRECT | {"long_number"})
        if kind == "data":
            redacted = self._hide_contact_names(redacted)
        self.cache[key] = redacted
        return redacted, len(events), False

    def walk(self, node: Any, counters: dict[str, int], mint: bool = True, walked: list[str] | None = None) -> Any:
        """Redact every string in a request tree. `parts` lists are tidied afterwards
        (see tidy_parts): Antigravity replays our own footer back as model text and
        stripping it leaves an empty part the Claude backends reject."""
        if isinstance(node, dict):
            out = {}
            if node.get("role") == "model":
                mint = False                        # model-authored content: vault only ...
            for k, v in node.items():
                if k in SKIP_KEYS:
                    out[k] = v
                elif k == "functionResponse":      # ... except tool results, which carry user data
                    out[k] = self.walk(v, counters, True, walked)
                elif k in ("functionCall", "thought"):
                    out[k] = self.walk(v, counters, False, walked)
                elif k == "parts" and isinstance(v, list):
                    out[k] = tidy_parts(self.walk(v, counters, mint, walked))
                else:
                    out[k] = self.walk(v, counters, mint, walked)
            return out
        if isinstance(node, list):
            return [self.walk(v, counters, mint, walked) for v in node]
        if isinstance(node, str):
            if mint:
                before = len(self.vault.display)
                out, spans, hit = self.redact_string(node)
                if not hit and len(self.vault.display) > before:
                    new = list(self.vault.display.items())[before:before + 6]
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"minted_from": node[:160], "kind": kind_of(FOOTER.sub("", node)),
                                              "new": new, "count": len(self.vault.display) - before}, ensure_ascii=False) + "\n")
            else:
                out, spans, hit = redact_text(FOOTER.sub("", node), self.vault, None)[0], 0, True
            counters["spans"] += spans
            counters["hits" if hit else "misses"] += 1
            if walked is not None:
                walked.append(out)
            return out
        return node

    # --------------------------------------------------------- in-chat review
    def find_unreviewed_tables(self, node: Any, found: list[tuple[str, str]]) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k not in SKIP_KEYS and k != "functionCall" and not (node.get("role") == "model" and k == "text"):
                    self.find_unreviewed_tables(v, found)
        elif isinstance(node, list):
            for v in node:
                self.find_unreviewed_tables(v, found)
        elif isinstance(node, str) and len(node) >= 3:
            text = FOOTER.sub("", node)
            key = hashlib.sha256(text.encode()).hexdigest()
            if key not in self.cache:
                split = self.split_table(text)
                if split and self.header_key(split[1]) not in self.decisions:
                    # A table that already carries vault tokens is our own redacted
                    # output echoed back (summaries, checkpoints): nothing real can
                    # leave, and asking the user about NAME_001/PHONE_002 is noise.
                    tokens = {m.group(0) for m in TOKEN_RE.finditer(split[1])}
                    if sum(1 for t in tokens if t in self.vault.display) >= 2:
                        return
                    found.append((self.header_key(split[1]), split[1]))

    def latest_user_request(self, contents: Any) -> str | None:
        last = None
        for item in contents if isinstance(contents, list) else []:
            if item.get("role") == "user":
                for part in item.get("parts", []):
                    m = USER_REQ.search(part.get("text", "") or "")
                    if m:
                        last = m.group(1)
        return last

    def apply_review_reply(self, reply: str) -> str | None:
        """Returns a message to show the user, or None if reply was not a review answer."""
        assert self.pending
        low = reply.strip().casefold()
        classes = dict(self.pending["classes"])
        columns = {c.casefold(): c for c in classes}
        extra_values: list[str] = []
        DIRECTIVE = re.compile(r"(also\s+hide|don'?t\s+hide|do\s+not\s+hide|unhide|hide)", re.I)
        parts = DIRECTIVE.split(reply.strip())
        # The reply is a review answer when it is a bare acknowledgement, or when any
        # directives start right after one ("ok, also hide status and Ujjwala").
        if parts[0].strip().rstrip(" .!,").casefold() not in {"ok", "okay", "yes", "fine", "go", "go ahead", "proceed", "ok go", ""}:
            return None
        if len(parts) == 1 and not parts[0].strip():
            return None
        for i in range(1, len(parts) - 1, 2):
            adding = not re.match(r"(don'?t|do\s+not|unhide)", parts[i].strip(), re.I)
            for n in re.split(r"[,;]|\band\b", parts[i + 1], flags=re.I):
                n = n.strip().strip("`'\"").rstrip(" .!")
                if not n:
                    continue
                if n.casefold() in columns:
                    classes[columns[n.casefold()]] = "person_name" if adding else "none"
                elif adding and len(n) >= 3:
                    # Not a column: a literal value to hide everywhere from now on
                    # (matched case-insensitively wherever it appears in content).
                    self.vault.token(n, "custom")
                    extra_values.append(n)
        if extra_values:
            self.vault.save()
        self.decisions[self.pending["key"]] = classes
        self.save_decisions()
        self.pending = None
        hidden = [c for c, k in classes.items() if k not in ("none", "record_id_non_pii", "age")]
        note = f"Understood. Hiding {len(hidden)} columns: {', '.join(hidden)}."
        if extra_values:
            note += " Also hiding these values wherever they appear: " + ", ".join(extra_values) + "."
        return note + " Continuing."

    def review_message(self, key: str, text: str) -> str | None:
        proposal = self.propose(text)
        classes = {c: v["class"] for c, v in proposal.items()}
        hidden = [f"{c} ({v['class']}, {v['rule']})" for c, v in proposal.items()
                  if v["class"] not in ("none", "record_id_non_pii", "age")]
        if not hidden:
            # Nothing would be replaced: asking the user is noise. Record and continue.
            self.decisions[key] = classes
            self.decisions_path.write_text(json.dumps(self.decisions, indent=1))
            return None
        self.pending = {"key": key, "classes": classes}
        kept = [c for c, v in proposal.items() if v["class"] in ("none", "record_id_non_pii", "age")]
        return (
            "🛡️ Privacy shield: a table is about to leave your laptop. I will replace these columns with tokens "
            f"before sending:\n- " + "\n- ".join(hidden) +
            f"\n\nKept as-is: {', '.join(kept) or 'none'}.\n\nReply **ok** to continue, **also hide X, Y** to hide more "
            "(a column name, or any word/value to hide everywhere), or **don't hide Z** to keep a column."
        )

    WRITE_TOOLS = {"write_to_file", "replace_file_content", "multi_replace_file_content", "edit_file", "create_file"}
    PATH_KEYS = ("TargetFile", "AbsolutePath", "FilePath", "path")

    def rehydrate_written_files(self, contents: Any) -> list[str]:
        """Any file a write tool touched may still contain tokens (streamed arguments
        split across events). Fix it on disk; the user's copy must never show tokens."""
        fixed: list[str] = []
        if not isinstance(contents, list):
            return fixed
        for item in contents[-6:]:
            for part in item.get("parts", []) if isinstance(item, dict) else []:
                call = part.get("functionCall") if isinstance(part, dict) else None
                if not call or call.get("name") not in self.WRITE_TOOLS:
                    continue
                args = call.get("args") or {}
                target = next((args[k] for k in self.PATH_KEYS if isinstance(args.get(k), str)), None)
                if not target or not os.path.isfile(target):
                    continue
                try:
                    raw = open(target, encoding="utf8").read()
                except (OSError, UnicodeDecodeError):
                    continue
                new = self.vault.rehydrate(raw)
                if new != raw:
                    open(target, "w", encoding="utf8").write(new)
                    fixed.append(target)
        return fixed

    def redact_request(self, body: bytes) -> tuple[bytes | None, dict[str, int], str | None]:
        """Returns (redacted body, counters, synthetic reply). If synthetic reply is
        set, the body is None and the proxy must answer the IDE itself."""
        counters = {"spans": 0, "hits": 0, "misses": 0}
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body, counters, None
        req = payload.get("request")
        if not (isinstance(req, dict) and "contents" in req):
            return body, counters, None
        if payload.get("requestType") == "checkpoint":  # title generator: redact, never review
            walked: list[str] = []
            req["contents"] = self.walk(req["contents"], counters, True, walked)
            self.last_walked = "\n".join(walked)
            return json.dumps(payload, ensure_ascii=False).encode(), counters, None
        if self.review == "chat":
            if self.pending:
                reply = self.latest_user_request(req["contents"])
                verdict = self.apply_review_reply(reply or "")
                if verdict is None:
                    return None, counters, self.pending_prompt  # re-ask
                self.pending_prompt = None
                with LOCK:
                    STATS["reviews"] += 1
                # fall through: forward this same request so the model continues the task
            found: list[tuple[str, str]] = []
            self.find_unreviewed_tables(req["contents"], found)
            for key, text in found:
                self.pending_prompt = self.review_message(key, text)
                if self.pending_prompt is not None:
                    return None, counters, self.pending_prompt
        fixed_files = self.rehydrate_written_files(req["contents"])
        if fixed_files:
            with open("shield.log", "a") as log:
                log.write(json.dumps({"t": time.time(), "rehydrated_files": fixed_files}) + "\n")
        walked: list[str] = []
        before = len(self.vault.display)
        req["contents"] = self.walk(req["contents"], counters, True, walked)
        # Consistency pass, always: every known value must be a token everywhere in
        # the outgoing request, whatever order parts were walked or cached in.
        walked = []
        req["contents"] = self.walk(req["contents"], {"spans": 0, "hits": 0, "misses": 0}, False, walked)
        self.vault.save()
        self.last_walked = "\n".join(walked)
        return json.dumps(payload, ensure_ascii=False).encode(), counters, None


class Rehydrator:
    """Event-level rehydration. SSE bytes are assembled into complete `data:` events;
    text parts are rehydrated with a carried tail so a token split across two events
    ("...AADHAAR_" + "050") is still replaced. Non-text fields pass through."""
    HOLD = 24

    def __init__(self, vault: PseudonymMap, note: str | None = None) -> None:
        self.vault = vault
        self.raw = b""
        self.tail = ""
        # Optional one-line summary. It is folded into the stream's own finish event
        # (the one carrying finishReason) rather than sent as an extra event after it:
        # Antigravity's language server stores a trailing extra event as an empty
        # model part, and the Claude backends then reject the replayed history
        # (400 "text: Field required"). Measured on the laptop, 2026-08-22.
        self.note = note

    def _fix(self, text: str, final: bool) -> str:
        joined = self.tail + text
        if final:
            self.tail = ""
            return self.vault.rehydrate(joined)
        cut = max(0, len(joined) - self.HOLD)
        while cut > 0 and (joined[cut - 1].isalnum() or joined[cut - 1] in "_\\"):
            cut -= 1   # never cut inside a possible token
        out, self.tail = joined[:cut], joined[cut:]
        return self.vault.rehydrate(out)

    def _partial_token(self, text: str) -> str:
        """The trailing fragment of `text` that could still grow into a vault token
        ("...NAME_0" of NAME_012), or "" when the text ends cleanly."""
        m = re.search(r"[A-Z][A-Z_\\\d]*$", text)
        if not m:
            return ""
        frag = m.group(0).replace("\\_", "_")
        return m.group(0) if any(t != frag and t.startswith(frag) for t in self.vault.display) else ""

    def _fix_arg(self, key: str, text: str, final: bool) -> str:
        """Streamed tool-call argument strings: same tail carry, keyed by argument name.
        Tool calls usually arrive whole in one event and a held tail can never be
        appended to a finished call, so only a fragment that is a strict prefix of
        an existing token is held back; ordinary text is never truncated."""
        tails = self.__dict__.setdefault("arg_tails", {})
        joined = tails.get(key, "") + text
        if final:
            tails[key] = ""
            return self.vault.rehydrate(joined)
        hold = self._partial_token(joined)
        out, tails[key] = joined[:len(joined) - len(hold)], hold
        return self.vault.rehydrate(out)

    def _walk(self, node, final, in_args=False):
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if k == "text" and isinstance(v, str) and not node.get("thought"):
                    out[k] = self._fix(v, final)
                elif in_args and isinstance(v, str):
                    out[k] = self._fix_arg(k, v, final) if len(v) > 200 else self.vault.rehydrate(v)
                else:
                    out[k] = self._walk(v, final, in_args or k == "args")
            return out
        if isinstance(node, list):
            return [self._walk(v, final, in_args) for v in node]
        return node

    def feed(self, chunk: bytes, final: bool = False) -> bytes:
        if PEEK["on"]:
            return chunk
        self.raw += chunk
        out = b""
        while True:
            i1, i2 = self.raw.find(b"\r\n\r\n"), self.raw.find(b"\n\n")
            cands = [(i, n) for i, n in ((i1, 4), (i2, 2)) if i >= 0]
            if not cands:
                break
            idx, n = min(cands)
            event, self.raw = self.raw[:idx + n], self.raw[idx + n:]
            self.sep = self.raw_sep = b"\r\n\r\n" if n == 4 else b"\n\n"
            out += self._event(event, False)
        if final:
            if self.raw.strip():
                out += self._event(self.raw, True)
                self.raw = b""
            if self.tail:
                out += sse_text_event(self.vault.rehydrate(self.tail))
                self.tail = ""
            for key, tail in list(self.__dict__.get("arg_tails", {}).items()):
                if tail:   # cannot append to a finished tool call: flushed via the on-disk backstop
                    self.__dict__.setdefault("arg_leftovers", []).append((key, tail))
                    self.arg_tails[key] = ""
        return out

    def _event(self, event: bytes, final: bool) -> bytes:
        text = event.decode("utf8", "replace")
        if not text.startswith("data: "):
            return event
        try:
            payload = json.loads(text[6:].strip())
        except json.JSONDecodeError:
            return event
        fixed = self._walk(payload, final)
        try:
            cand = fixed["response"]["candidates"][0]
            parts = cand.get("content", {}).get("parts")
        except (KeyError, IndexError, TypeError, AttributeError):
            cand, parts = None, None
        if isinstance(parts, list):
            # Empty text parts (Google's own stream markers, or a short chunk held back
            # whole by the tail carry) are dropped: Antigravity's language server keeps
            # an empty part that arrives through a proxy, and the Claude backends then
            # reject the replayed history (400 "text: Field required").
            parts[:] = [p for p in parts if not (isinstance(p, dict) and set(p) == {"text"} and p["text"] == "")]
            if cand.get("finishReason"):
                extra = self.vault.rehydrate(self.tail) + (self.note or "")
                self.tail, self.note = "", None
                if extra:
                    if parts and isinstance(parts[-1].get("text"), str) and not parts[-1].get("thought"):
                        parts[-1]["text"] += extra
                    else:
                        parts.append({"text": extra})
            if not parts:
                del cand["content"]
                if not cand and len(fixed["response"]) == 1 and len(fixed["response"]["candidates"]) == 1:
                    return b""            # nothing left to say
        return b"data: " + json.dumps(fixed, ensure_ascii=False).encode() + getattr(self, "sep", b"\r\n\r\n")


def tidy_parts(parts: list[Any]) -> list[Any]:
    """Drop text parts that are empty after redaction (Anthropic models, reached
    through Antigravity, reject them with 400 "text: Field required") and hang an
    orphaned thoughtSignature on the thought part it belongs to."""
    out: list[Any] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text") == "" and not (part.keys() & {"functionCall", "functionResponse"}):
            sig = part.get("thoughtSignature")
            if sig and out and isinstance(out[-1], dict) and out[-1].get("thought") and "thoughtSignature" not in out[-1]:
                out[-1]["thoughtSignature"] = sig
                continue
            if not sig:
                continue
        out.append(part)
    return out


def sse_text_event(text: str, finish: bool = False) -> bytes:
    cand: dict[str, Any] = {"content": {"role": "model", "parts": [{"text": text}]}}
    if finish:
        cand["finishReason"] = "STOP"
    return (f"data: {json.dumps({'response': {'candidates': [cand]}})}\r\n\r\n").encode()


def make_handler(shield: Shield, annotate: bool):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def read_body(self) -> bytes:
            if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
                out = b""
                while True:
                    size = int(self.rfile.readline().strip().split(b";")[0], 16)
                    if size == 0:
                        self.rfile.readline()
                        return out
                    out += self.rfile.read(size)
                    self.rfile.readline()
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def send_local(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_sse(self, events: list[bytes]) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for ev in events:
                self.wfile.write(f"{len(ev):x}\r\n".encode() + ev + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/shield/status" or url.path == "/shield/status.json":
                with LOCK:
                    snap = dict(STATS)
                snap.update(vault_entries=len(shield.vault.display), cache_entries=len(shield.cache),
                            peek=PEEK["on"], pending_review=bool(shield.pending),
                            tokens_est_out=int(snap.get("bytes_out", 0) / 4),
                            server=os.path.dirname(os.path.abspath(__file__)))
                if url.path.endswith(".json"):
                    return self.send_local(200, json.dumps(snap, indent=1).encode())
                rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in snap.items())
                html = ("<meta http-equiv=refresh content=2><title>Privacy shield</title><body style='font-family:sans-serif'>"
                        f"<h3>Privacy shield</h3><table border=1 cellpadding=4>{rows}</table>"
                        "<p><a href=/shield/vault>vault</a> - <a href=/shield/last-request>last request (wire view)</a> - "
                        "<a href='/shield/peek?on=1'>peek on</a> / <a href='/shield/peek?on=0'>peek off</a></p></body>")
                return self.send_local(200, html.encode(), "text/html")
            if url.path == "/shield/vault":
                return self.send_local(200, json.dumps(shield.vault.display, indent=1, ensure_ascii=False).encode())
            if url.path == "/shield/quit":
                self.send_local(200, b'{"bye": true}')
                threading.Timer(0.3, lambda: os._exit(0)).start()
                return
            if url.path == "/shield/peek":
                PEEK["on"] = parse_qs(url.query).get("on", ["0"])[0] == "1"
                return self.send_local(200, json.dumps({"peek": PEEK["on"]}).encode())
            if url.path == "/shield/last-request":
                q = parse_qs(url.query).get("q", [""])[0]
                body = LAST_REQUEST["body"]
                hits = len(re.findall(re.escape(q), body, flags=re.I)) if q else None
                html = ("<title>wire view</title><body style='font-family:monospace;white-space:pre-wrap'>"
                        f"<form>search what left the laptop: <input name=q value='{q}'><button>find</button>"
                        f"{'' if hits is None else f' → {hits} hits'}</form>"
                        f"<p>{LAST_REQUEST['path']} at {LAST_REQUEST['when']} - {len(body)} bytes</p><hr>"
                        + body.replace("&", "&amp;").replace("<", "&lt;") + "</body>")
                return self.send_local(200, html.encode(), "text/html")
            return self._fwd()

        def do_POST(self):
            return self._fwd()

        def _fwd(self):
            body = self.read_body()
            with open("shield-requests.log", "a") as log:
                log.write(json.dumps({"t": time.time(), "path": self.path, "bytes": len(body)}) + "\n")
            counters = {"spans": 0, "hits": 0, "misses": 0}
            redact_ms = 0.0
            is_model_call = "streamGenerateContent" in self.path or "generateContent" in self.path
            if is_model_call and body:
                t0 = time.monotonic()
                try:
                    body2, counters, synthetic = shield.redact_request(body)
                except Exception as error:  # fail closed, never leave the client hanging
                    import traceback
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"t": time.time(), "redaction_error": f"{type(error).__name__}: {error}",
                                              "trace": traceback.format_exc()[-2000:]}) + "\n")
                    with LOCK:
                        STATS["errors"] = STATS.get("errors", 0) + 1
                    return self.send_sse([sse_text_event(
                        "🛡️ Privacy shield hit an internal error while checking this request, so nothing was sent. "
                        "Please try the message again; if it repeats, run 'Privacy Shield: Show daemon log'.", finish=True)])
                redact_ms = (time.monotonic() - t0) * 1000
                if synthetic is not None:
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"t": time.time(), "review_prompt": True, "redact_ms": round(redact_ms, 1)}) + "\n")
                    return self.send_sse([sse_text_event(synthetic, finish=True)])
                body = body2
                # last line of defence repairs before it refuses: substitute every known
                # value once more over the final body (order-independent), then check
                known = shield.vault.known_regex()
                if known:
                    def _sub(m):
                        return shield.vault.forward.get(re.sub(r"\s+", " ", m.group(0).strip()).casefold(), m.group(0))
                    fixed = known.sub(_sub, body.decode("utf8", "replace"))
                    body = fixed.encode()
                    shield.last_walked = known.sub(_sub, getattr(shield, "last_walked", ""))
                lowered = getattr(shield, "last_walked", "").casefold()
                leak = next((v for t, v in shield.vault.display.items()
                             if len(v) >= 4 and not t.startswith(("NUMBER", "AGE"))
                             and not re.fullmatch(TOKEN_RE.pattern, v.strip().strip("'\"`"), re.I)
                             and re.search(rf"(?<![\w@.]){re.escape(v.casefold())}(?![\w@.])", lowered)), None)
                if leak:
                    with LOCK:
                        STATS["blocked"] += 1
                    i = lowered.find(leak.casefold())
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"t": time.time(), "blocked_value": leak,
                                              "context": lowered[max(0, i - 120):i + 80]}) + "\n")
                    return self.send_sse([sse_text_event(
                        "🛡️ Privacy shield blocked this request: a protected value was still present in the outgoing text. "
                        "Nothing was sent.", finish=True)])
                LAST_REQUEST.update(body=body.decode("utf8", "replace"), path=self.path, when=time.strftime("%H:%M:%S"))
            hdr = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "transfer-encoding", "accept-encoding")}
            hdr["Host"] = UPHOST
            hdr["Content-Length"] = str(len(body))
            t1 = time.monotonic()
            conn = http.client.HTTPSConnection(UPHOST, timeout=600, context=ssl.create_default_context())
            conn.request(self.command, self.path, body=body, headers=hdr)
            r = conn.getresponse()
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() not in ("transfer-encoding", "content-length", "connection", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            note = None
            if is_model_call and annotate:
                note = (f"\n\n_shield: {counters['spans']} new spans, {counters['misses']} new parts, "
                        f"{redact_ms:.0f} ms redaction, vault {len(shield.vault.display)}_")
            rehydrator = Rehydrator(shield.vault, note)
            total = 0

            def emit(data: bytes) -> None:
                if data:
                    self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
                    self.wfile.flush()

            while True:
                chunk = r.read1(65536)
                if not chunk:
                    break
                total += len(chunk)
                emit(rehydrator.feed(chunk) if is_model_call else chunk)
            tail = rehydrator.feed(b"", final=True) if is_model_call else b""
            emit(tail)
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            conn.close()
            upstream_ms = (time.monotonic() - t1) * 1000
            if is_model_call:
                with LOCK:
                    STATS["calls"] += 1
                    STATS["redact_ms_total"] += redact_ms
                    STATS["redact_ms_last"] = round(redact_ms, 1)
                    STATS["spans_total"] += counters["spans"]
                    STATS["cache_hits"] += counters["hits"]
                    STATS["cache_misses"] += counters["misses"]
                    STATS["bytes_out"] += len(body)
                    STATS["upstream_ms_total"] += upstream_ms
                    STATS["last"] = time.strftime("%H:%M:%S")
                tools = re.findall(r'"functionCall":\s*\{[^{}]*?"name":\s*"([^"]+)"', body.decode("utf8", "replace"))
                with open("shield.log", "a") as log:
                    log.write(json.dumps({"t": time.time(), "path": self.path, "bytes_out": len(body), "tools": tools[-3:],
                                          "redact_ms": round(redact_ms, 1), "upstream_ms": round(upstream_ms),
                                          "resp_bytes": total, **counters}) + "\n")
    return H


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--engine", default="gliner:knowledgator/gliner-pii-edge-v1.0")
    parser.add_argument("--vault", type=Path, default=Path("shield-vault-local-only.json"))
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--numbers", type=int, help="also hide every run of N+ digits in data and tables")
    parser.add_argument("--always-hide", type=Path, help="file with one value per line to always hide")
    parser.add_argument("--review", choices=("chat", "off"), default="off")
    args = parser.parse_args()
    os.environ.setdefault("PII_THREADS", "4")
    t0 = time.monotonic()
    shield = Shield(args.engine, args.vault, args.numbers, args.always_hide, args.review)
    shield.pending_prompt = None
    print(f"shield ready on http://127.0.0.1:{args.port}  (engine loaded in {time.monotonic() - t0:.1f}s)", flush=True)
    print(f"status: http://127.0.0.1:{args.port}/shield/status", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(shield, args.annotate)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
