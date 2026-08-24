"""Sheltering for the open lane: the stage-3 vault applied inside io.

A folder's tables are classified column by column (cached in <folder>/.io/pii-classes.json —
drop in a hand-reviewed file to override), private values are replaced by stable tokens
(NAME_001, PHONE_002 …) in a per-folder vault (<folder>/.io/vault-local-only.json, gitignored),
and the tokenised tables are what the open lane sends. Whatever the model returns is rehydrated
on the laptop before the user sees it. The review summary (which columns are hidden and why) is
what the UI shows before the first call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "benchmarks" / "pii"))

from columns import classify_columns  # noqa: E402
from detect import regex_engine  # noqa: E402
from pseudonymize import PseudonymMap, pseudonymise_frame, redact_question  # noqa: E402

REASONS = {
    "person_name": "names", "phone": "phone numbers", "aadhaar": "Aadhaar numbers", "email": "email addresses",
    "bank_account": "bank account numbers", "ifsc": "IFSC codes", "village": "village names", "address": "addresses",
    "dob": "dates of birth (year kept)", "gps": "precise locations (rounded)", "caste_category": "caste categories",
    "free_text_with_pii": "free text that may carry names/numbers", "upi": "UPI ids", "pan": "PAN numbers",
    "voter_id": "voter ids", "vehicle": "vehicle numbers",
}


class Shelter:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.dir = folder / ".io"
        self.dir.mkdir(exist_ok=True)
        self.pmap = PseudonymMap(self.dir / "vault-local-only.json")
        self.classes_path = self.dir / "pii-classes.json"
        self.classes: dict[str, dict] = json.loads(self.classes_path.read_text()) if self.classes_path.exists() else {}
        self.redacted: dict[str, pd.DataFrame] = {}

    def classify(self, table: str, frame: pd.DataFrame) -> dict:
        if table not in self.classes:
            try:
                raw = classify_columns(frame.astype("string"), span_engine=None, text_engine=regex_engine)
            except TypeError:
                raw = classify_columns(frame.astype("string"), None)
            self.classes[table] = {c: (v.get("class") if isinstance(v, dict) else v) for c, v in raw.items()} if isinstance(raw, dict) else raw
            self.classes_path.write_text(json.dumps(self.classes, indent=1, ensure_ascii=False))
        return self.classes[table]

    def redact_table(self, table: str, frame: pd.DataFrame) -> pd.DataFrame:
        if table not in self.redacted:
            classes = self.classify(table, frame)
            red = pseudonymise_frame(frame.astype("string"), classes, self.pmap, detector=regex_engine, kept_validator=regex_engine)
            self.redacted[table] = red
            self.pmap.save()
        return self.redacted[table]

    def redact_text(self, text: str) -> str:
        return redact_question(text, self.pmap, regex_engine)["redacted"]

    def rehydrate(self, text: str) -> str:
        return self.pmap.rehydrate(text)

    def review(self, table: str, frame: pd.DataFrame) -> list[dict]:
        classes = self.classify(table, frame)
        out = []
        for col, cls in classes.items():
            cs = cls if isinstance(cls, list) else [cls]
            hidden = [c for c in cs if c not in (None, "none", "record_id_non_pii", "age")]
            if hidden:
                out.append({"column": col, "why": ", ".join(REASONS.get(c, c) for c in hidden)})
        return out

    def sub_known(self, text: str) -> str:
        """Final consistency pass (the shield's repair-before-refuse): any vault value still in the
        payload — a village inside a school string, a name inside remarks — becomes its token."""
        known = self.pmap.known_regex()
        if not known:
            return text
        import re as _re
        return known.sub(lambda m: self.pmap.forward.get(_re.sub(r"\s+", " ", m.group(0).strip()).casefold(), m.group(0)), text)

    def leak_check(self, text: str) -> list[str]:
        """Values from the vault that appear un-tokenised in an outbound payload."""
        known = self.pmap.known_regex()
        if not known:
            return []
        return sorted({m.group(0) for m in known.finditer(text)})[:8]
