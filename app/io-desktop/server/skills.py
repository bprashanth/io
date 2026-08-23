"""Skills: declarative, reviewable claims the kernel compiles without a model.

A skill is one JSON file:
{
  "name": "razorpay-export", "kind": "hint" | "mapping" | "parse" | "rule" | "template",
  "description": "plain-language one-liner shown on the card",
  "origin": "builtin" | "authored" | "compacted" | "correction",
  "trigger": {            # every present key must match; a skill with no trigger never fires
     "columns_all": [..], "columns_any": [..],      # case-insensitive column names of a table
     "table_regex": "...", "file_glob": "*.csv", "file_sha256": "...", "folder_name": "...",
     "whatsapp": true, "months": true,               # structural flags the loader sets
     "question_regex": "..."                         # for rule/template: fires per question
  },
  # payload by kind:
  "claim": "text appended to the table's schema as a -- note"          (hint)
  "claim": "text appended to the question prompt as a rule"            (rule)
  "mapping": {"derive": {"amount_rupees": "amount / 100.0"},            (mapping)
              "unify": {"households_reached": ["No. of HH", "Households reached"]}}
  "parse": {"header_row": 2, "dayfirst": false, "sheet": "Yield"}      (parse; applied at load)
  "template": {"plan": {...}}                                           (template; plan used as-is)
}
Skills never contain data values: every skill is checked against the values of the loaded
high-cardinality text columns (names, phones, ids) before it is saved or applied.

Search order: built-in (shipped), user (~/.config/io-desktop/skills), folder (<folder>/.io/skills).
Later dirs override earlier ones by name.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILTIN_DIR = HERE.parent / "skills" / "builtin"
USER_DIR = Path(os.environ.get("IO_CONFIG_DIR") or (Path.home() / ".config" / "io-desktop")) / "skills"
KINDS = {"hint", "mapping", "parse", "rule", "template"}


def load_skills(folder: Path | None) -> list[dict]:
    found: dict[str, dict] = {}
    dirs = ([] if os.environ.get("IO_DISABLE_BUILTIN") else [BUILTIN_DIR]) + [USER_DIR] + ([folder / ".io" / "skills"] if folder else [])
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                sk = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(sk, dict) or sk.get("kind") not in KINDS or not sk.get("name"):
                continue
            sk["_path"] = str(p)
            sk["_layer"] = "builtin" if d == BUILTIN_DIR else "user" if d == USER_DIR else "folder"
            if sk.get("enabled", True):
                found[sk["name"]] = sk
    return list(found.values())


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table_matches(trigger: dict, table: dict) -> bool:
    """table: {"table": name, "file": filename, "columns": [...], "sha256": ..., "folder": name, flags...}"""
    cols = {c.casefold() for c in table.get("columns", [])}
    if "columns_all" in trigger and not all(c.casefold() in cols for c in trigger["columns_all"]):
        return False
    if "columns_any" in trigger and not any(c.casefold() in cols for c in trigger["columns_any"]):
        return False
    if "table_regex" in trigger and not re.search(trigger["table_regex"], table.get("table", ""), re.I):
        return False
    if "file_glob" in trigger and not fnmatch.fnmatch(table.get("file", "").lower(), trigger["file_glob"].lower()):
        return False
    if "file_sha256" in trigger and trigger["file_sha256"] != table.get("sha256"):
        return False
    if "folder_name" in trigger and trigger["folder_name"].lower() != (table.get("folder") or "").lower():
        return False
    for flag in ("whatsapp", "months", "ledger"):
        if flag in trigger and bool(trigger[flag]) != bool(table.get(flag)):
            return False
    return any(k in trigger for k in ("columns_all", "columns_any", "table_regex", "file_glob", "file_sha256", "folder_name", "whatsapp", "months", "ledger"))


def question_matches(trigger: dict, question: str) -> bool:
    rx = trigger.get("question_regex")
    return bool(rx) and re.search(rx, question, re.I) is not None


def value_leak(skill: dict, protected_values: set[str]) -> list[str]:
    """Values from high-cardinality text columns (names, phones, ids) that appear in the skill text."""
    text = json.dumps({k: v for k, v in skill.items() if not k.startswith("_")}, ensure_ascii=False).casefold()
    hits = []
    for v in protected_values:
        if len(v) >= 4 and v.casefold() in text:
            hits.append(v)
            if len(hits) >= 5:
                break
    return hits


def save_skill(skill: dict, layer: str, folder: Path | None) -> Path:
    d = USER_DIR if layer == "user" else (folder / ".io" / "skills")
    d.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", skill["name"].lower()).strip("-") or "skill"
    p = d / f"{slug}.json"
    clean = {k: v for k, v in skill.items() if not k.startswith("_")}
    clean["name"] = slug
    p.write_text(json.dumps(clean, indent=1, ensure_ascii=False))
    return p


def delete_skill(name: str, folder: Path | None) -> bool:
    for sk in load_skills(folder):
        if sk["name"] == name and sk["_layer"] != "builtin":
            Path(sk["_path"]).unlink(missing_ok=True)
            return True
    return False
