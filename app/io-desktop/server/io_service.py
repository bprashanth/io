#!/usr/bin/env python3
"""io — T0 local service.

One process, stdlib HTTP on 127.0.0.1. Loads the CSV/XLSX files in a folder
into DuckDB, turns questions into SQL (Ask lane) or into a panel plan (Build
lane) using whichever model the user configured — a local llama.cpp/Ollama
OpenAI-compatible URL, or OpenRouter with a key — executes everything locally
and renders deterministic pages. The model never sees a row and never states a
number; every figure on screen is a receipted query result.

Endpoints
  GET  /                      the UI
  GET  /api/state             folder, tables, model config (key masked), history
  POST /api/folder {path}     load a folder
  POST /api/config {...}      {"source":"local"|"openrouter","endpoint","model","api_key"}
  POST /api/ask {text}        routes to Ask or Build lane, returns a turn
  GET  /api/page/<turn>       rendered HTML for a Build turn
  GET  /api/csv/<turn>/<pid>  CSV download of a panel / answer
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import sqlglot
from sqlglot import exp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_plan  # noqa: E402

HERE = Path(__file__).resolve().parent
UI = HERE.parent / "ui"
CONFIG_DIR = Path(os.environ.get("IO_CONFIG_DIR") or (Path.home() / ".config" / "io-desktop"))
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_CONFIG = {"source": "openrouter", "endpoint": "https://openrouter.ai/api/v1", "model": "qwen/qwen3.5-9b", "api_key": "",
                  "local_endpoint": "http://127.0.0.1:8080/v1", "local_model": "local"}

PAGE_WORDS = re.compile(r"\b(pwa|web ?app|an? app|app for|form|website|homepage|landing page|quiz|sign ?up|tracker|collector|offline|game|calculator|checklist)\b", re.I)
BUILD_WORDS = re.compile(r"\b(build|dashboard|website|web ?page|report|summary|summari[sz]e|write me|make me a page|one.?pager|brief)\b", re.I)

ASK_RULES = [
    "You translate ordinary questions into exactly one read-only DuckDB SELECT or WITH query.",
    "Return SQL only. Never write files, install software, calculate values yourself, or invent columns.",
    "Use only the supplied schema. Preserve relevant scope from earlier turns unless the newest question changes it.",
    "A requested rate must use its stated numerator and denominator. Percentage-point change means later percentage minus earlier percentage, not relative growth.",
    "When the user explicitly asks for percent or percentage, multiply numerator divided by denominator by 100.",
    "When the user asks to compare years or groups without asking for a change, keep those year/group columns and requested measures in the output.",
    "When several known category values are named, filter them separately with IN rather than concatenating them.",
    "Use NULLIF for denominators. Missing values remain missing and are not zero.",
]
# Two extra rules (quoting/UNION alignment, a jaro_winkler hint) were measured on 2026-08-23 and did not
# help the 9B (holdout 23/21 plain vs 20/19 with them; anchor 19 vs 16); approximate matching is done
# by the spelling-normalised columns instead. Keep the prompt identical to the stage-2 shell prompt.

BUILD_CONTRACT = """You design a small, honest data page. You never see rows and you never state a number.
You return ONE JSON object and nothing else (no prose, no code fences):
{
  "title": "short page title",
  "subtitle": "one line on what the page answers",
  "panels": [
    {"id": "p1", "kind": "kpi", "title": "Total children", "sql": "SELECT COUNT(*) AS n FROM ...", "unit": ""},
    {"id": "p2", "kind": "bar", "title": "Average score by site", "sql": "SELECT site, AVG(score) AS avg_score FROM ... GROUP BY 1 ORDER BY 2 DESC", "x": "site", "y": ["avg_score"]},
    {"id": "p3", "kind": "line", "title": "Monthly trend", "sql": "SELECT month, SUM(amount) AS total FROM ... GROUP BY 1 ORDER BY 1", "x": "month", "y": ["total"]},
    {"id": "p4", "kind": "table", "title": "Top 10 ...", "sql": "SELECT ... LIMIT 10"}
  ],
  "narrative": "optional: 2-5 short paragraphs. Every number or ranked item MUST be a placeholder: {{p1}} = the number of a one-row panel; {{p5}} = first row of a multi-row panel shown as 'label (value)'; {{p5[2]}} = second row; {{p5.city}} / {{p5[2].total}} = a named column of that row. Never type a digit or a top-ranked name yourself."
}
Rules:
- kinds: kpi (one row, one numeric), bar, stacked_bar (x = category, y = list of numeric columns), line (x = period, y = one numeric, optional "series" column), scatter (x,y numeric), pie (x = category, y = numeric, <= 8 slices), table.
- 3 to 7 panels for a dashboard; 1 to 4 KPIs first. A report adds a narrative with placeholders. For a table-heavy request, prefer tables.
- SQL: one read-only DuckDB SELECT/WITH per panel over ONLY the schema below; quote column names with double quotes when they contain spaces or odd characters; use NULLIF for denominators; group + order + LIMIT so charts stay readable (<= 20 bars). Missing values stay NULL, not zero.
- Column aliases in SQL must match the x / y names you give. Keep aliases snake_case.
- When two tables describe the same thing with different column names, UNION ALL them with aligned aliases.
- Percentages: multiply by 100 and set unit "%".
"""


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text()))
        except Exception:  # noqa: BLE001
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=1))
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def table_name(stem: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_") or "table"
    if base[0].isdigit():
        base = "t_" + base
    name, i = base, 2
    while name in used:
        name, i = f"{base}_{i}", i + 1
    used.add(name)
    return name


DATE_SHAPE = re.compile(r"^\s*(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})([T ]\d{1,2}:\d{2}(:\d{2})?)?\s*$")



FOOTER_WORDS = re.compile(r"^\s*(total|grand total|sub ?total|source|note|notes|remarks?|prepared by|compiled by|\*)\b", re.I)
MONTH_COL = re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[\s'\-/]*\d{2,4}$|^\d{4}[\-/](0?[1-9]|1[0-2])$|^(0?[1-9]|1[0-2])[\-/]\d{4}$", re.I)
GPS_PAIR = re.compile(r"^\s*(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})\s*$")


def _is_blank(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or (isinstance(v, str) and not v.strip())


def find_header_row(raw: pd.DataFrame) -> int:
    """Real sheets carry a title and blank rows above the header. The header is the first
    row that is mostly filled with short labels and is followed by a row that is mostly filled."""
    n = min(len(raw), 30)
    width = raw.shape[1]
    best, best_score = 0, -1.0
    for i in range(n):
        row = list(raw.iloc[i])
        filled = [v for v in row if not _is_blank(v)]
        if len(filled) < max(2, 0.5 * width):
            continue
        labelish = sum(1 for v in filled if isinstance(v, str) and len(v.strip()) <= 48 and not re.fullmatch(r"[\d.,%\-/ ]+", v.strip()))
        nxt = list(raw.iloc[i + 1]) if i + 1 < len(raw) else []
        nxt_filled = sum(1 for v in nxt if not _is_blank(v))
        score = labelish / len(filled) + (0.5 if nxt_filled >= 0.5 * width else 0) - 0.02 * i
        if labelish / len(filled) >= 0.7 and score > best_score:
            best, best_score = i, score
            break  # first credible header wins
    return best


def tidy_frame(raw: pd.DataFrame) -> pd.DataFrame | None:
    """Turn a raw sheet (header=None) into a clean table: detect the header row, drop title,
    blank, footer and total rows, fix blank/duplicate headers, parse '1,250' numbers,
    split 'lat, long' pairs."""
    raw = raw.dropna(how="all").dropna(axis=1, how="all")
    if raw.empty or raw.shape[1] < 2:
        return None
    raw = raw.reset_index(drop=True)
    h = find_header_row(raw)
    headers = []
    seen: dict[str, int] = {}
    for j, v in enumerate(raw.iloc[h]):
        name = str(v).strip() if not _is_blank(v) else f"col_{j + 1}"
        name = re.sub(r"\s+", " ", name)
        if name.lower().startswith("unnamed:"):
            name = f"col_{j + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        headers.append(name)
    body = raw.iloc[h + 1:].copy()
    body.columns = headers
    body = body.dropna(how="all")
    # footer / total rows: first cell is a footer word, or the row is mostly empty at the tail
    def is_footer(row) -> bool:
        first = next((v for v in row if not _is_blank(v)), None)
        filled = sum(1 for v in row if not _is_blank(v))
        return (isinstance(first, str) and bool(FOOTER_WORDS.match(first)) and filled <= max(2, 0.5 * len(row))) or (isinstance(first, str) and FOOTER_WORDS.match(first) is not None and first.strip().lower() in ("total", "grand total"))
    mask = body.apply(lambda r: is_footer(list(r)), axis=1)
    body = body[~mask]
    # trailing sparse rows (notes under the table)
    while len(body) and sum(1 for v in body.iloc[-1] if not _is_blank(v)) < max(2, 0.3 * body.shape[1]):
        body = body.iloc[:-1]
    body = body.reset_index(drop=True)
    for c in list(body.columns):
        col = body[c]
        if col.dtype == object or str(col.dtype).startswith("str"):
            stripped = col.map(lambda v: v.strip() if isinstance(v, str) else v)
            nonblank = stripped.dropna()
            nonblank = nonblank[nonblank.map(lambda v: not (isinstance(v, str) and not v))]
            if len(nonblank) == 0:
                body[c] = stripped
                continue
            # '1,250' / '12.5%' style numbers
            as_num = pd.to_numeric(nonblank.map(lambda v: re.sub(r"[,\s₹]|%$", "", v) if isinstance(v, str) else v), errors="coerce")
            if as_num.notna().mean() >= 0.95 and nonblank.map(lambda v: isinstance(v, str) and bool(re.search(r"\d", v))).mean() >= 0.9:
                body[c] = pd.to_numeric(stripped.map(lambda v: re.sub(r"[,\s₹]|%$", "", v) if isinstance(v, str) else v), errors="coerce")
                continue
            # 'lat, long' pairs
            if nonblank.map(lambda v: isinstance(v, str) and bool(GPS_PAIR.match(v))).mean() >= 0.9:
                body[f"{c} lat"] = stripped.map(lambda v: float(GPS_PAIR.match(v).group(1)) if isinstance(v, str) and GPS_PAIR.match(v) else None)
                body[f"{c} long"] = stripped.map(lambda v: float(GPS_PAIR.match(v).group(2)) if isinstance(v, str) and GPS_PAIR.match(v) else None)
                body[c] = stripped
                continue
            body[c] = stripped
        else:
            try:
                if (col.dropna() % 1 == 0).all():
                    body[c] = col.astype("Int64")
            except Exception:  # noqa: BLE001
                pass
    return body if len(body) else None


def canonicalise_variants(frame: pd.DataFrame) -> list[str]:
    """'Soyabean' / 'soyabean' / 'SOYABEAN ' are one category. In text columns with few distinct
    values, spellings that differ only by case or spacing are replaced by the most frequent one.
    Returns the columns touched (the schema tells the model)."""
    touched = []
    for c in frame.columns:
        col = frame[c]
        if not (col.dtype == object or str(col.dtype).startswith("str")):
            continue
        vals = col.dropna()
        vals = vals[vals.map(lambda v: isinstance(v, str) and bool(v.strip()))]
        if len(vals) < 5 or vals.nunique() > 60:
            continue
        groups: dict[str, dict[str, int]] = {}
        for v, n in vals.value_counts().items():
            key = re.sub(r"\s+", " ", v.strip()).casefold()
            groups.setdefault(key, {})[v] = n
        if all(len(g) == 1 for g in groups.values()):
            continue
        mapping = {}
        for g in groups.values():
            canon = max(g.items(), key=lambda kv: (kv[1], sum(ch.islower() for ch in kv[0])))[0].strip()
            for v in g:
                if v != canon:
                    mapping[v] = canon
        frame[c] = col.map(lambda v: mapping.get(v, v) if isinstance(v, str) else v)
        touched.append(c)
    return touched


def month_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if MONTH_COL.match(str(c).strip())]

def coerce_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """Text columns whose values look like dates become real DATE/TIMESTAMP columns,
    so the model does not have to guess the format (dd-mm-yyyy is common in Indian sheets)."""
    for col in frame.columns:
        if not (frame[col].dtype == object or str(frame[col].dtype).startswith("str")):
            continue
        sample = frame[col].dropna().astype(str).head(200)
        if len(sample) < 3 or sample.map(lambda v: bool(DATE_SHAPE.match(v))).mean() < 0.9:
            continue
        parsed = None
        for dayfirst in (True, False):
            try:
                cand = pd.to_datetime(frame[col], errors="coerce", dayfirst=dayfirst, format="mixed")
            except Exception:  # noqa: BLE001
                continue
            ok = cand.notna().sum() / max(frame[col].notna().sum(), 1)
            if ok >= 0.95 and (parsed is None or cand.notna().sum() > parsed.notna().sum()):
                parsed = cand
                break
        if parsed is not None:
            has_time = bool(((parsed.dt.hour != 0) | (parsed.dt.minute != 0)).any())
            frame[col] = parsed if has_time else parsed.dt.date
    return frame


class Workspace:
    def __init__(self) -> None:
        self.folder: Path | None = None
        self.db = duckdb.connect(":memory:", config={"enable_external_access": "false"})
        self.tables: list[dict] = []
        self.bridges: list[dict] = []
        self.schema = ""
        self.categories: dict = {}
        self.history: list[dict] = []
        self.turns: dict[str, dict] = {}
        self.lock = threading.Lock()

    def file_signature(self) -> dict[str, tuple[float, int]]:
        if not self.folder or not self.folder.is_dir():
            return {}
        sig = {}
        for p in self.folder.iterdir():
            if p.suffix.lower() in (".csv", ".xlsx", ".xls") and not p.name.startswith("~$"):
                try:
                    st = p.stat()
                    sig[p.name] = (st.st_mtime, st.st_size)
                except OSError:
                    pass
        return sig

    def load(self, folder: Path, keep_history: bool = False) -> None:
        self.db = duckdb.connect(":memory:", config={"enable_external_access": "false"})
        self.tables = []
        if not keep_history:
            self.history, self.turns = [], {}
        self.version = getattr(self, "version", 0) + 1
        used: set[str] = set()
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".csv", ".xlsx", ".xls") and not p.name.startswith("~$"))
        for f in files:
            try:
                if f.suffix.lower() == ".csv":
                    frames = {None: pd.read_csv(f, header=None, dtype=object, skip_blank_lines=False, encoding_errors="replace")}
                else:
                    frames = pd.read_excel(f, sheet_name=None, header=None, dtype=object)
            except Exception as exc:  # noqa: BLE001
                self.tables.append({"file": f.name, "error": str(exc)[:200]})
                continue
            for sheet, raw in frames.items():
                frame = tidy_frame(raw)
                if frame is None:
                    continue
                frame = coerce_dates(frame)
                merged = canonicalise_variants(frame)
                name = table_name(f.stem + (f"_{sheet}" if sheet and len(frames) > 1 else ""), used)
                self.db.register("tmp_frame", frame)
                self.db.execute(f'CREATE TABLE "{name}" AS SELECT * FROM tmp_frame')
                self.db.unregister("tmp_frame")
                self.tables.append({"file": f.name, "sheet": sheet, "table": name, "rows": len(frame), "columns": list(frame.columns), "merged_case": merged})
        self.folder = folder
        self.bridges = self._build_bridges()
        self.schema = self._ddl()
        self.categories = self._categories()
        self.signature = self.file_signature()
        self.changed_at = time.strftime("%H:%M:%S")

    def watch(self, interval: float = 2.0) -> None:
        """Reload when a file in the folder is saved; pages re-run their receipts on the next view."""
        while True:
            time.sleep(interval)
            try:
                if self.folder and self.file_signature() != getattr(self, "signature", {}):
                    time.sleep(0.5)  # let the editor finish writing
                    with self.lock:
                        self.load(self.folder, keep_history=True)
            except Exception:  # noqa: BLE001
                traceback.print_exc()

    def _text_columns(self, table: str, min_distinct: int = 15) -> list[str]:
        cols = self.db.execute("SELECT column_name FROM information_schema.columns WHERE table_name = ? AND data_type IN ('VARCHAR','TEXT') ORDER BY ordinal_position", [table]).fetchall()
        out = []
        for (c,) in cols:
            q = c.replace('"', '""')
            n, d, avg_len = self.db.execute(f'SELECT COUNT("{q}"), COUNT(DISTINCT "{q}"), AVG(LENGTH("{q}")) FROM "{table}"').fetchone()
            if d >= min_distinct and avg_len and 6 <= avg_len <= 80:
                out.append(c)
        return out

    def _build_bridges(self) -> list[dict]:
        """For pairs of text columns in different files whose values mostly match only
        approximately (spelling variants), precompute the best fuzzy match per value.
        The model never has to write the matching logic; it joins through the bridge."""
        names = [t["table"] for t in self.tables if "table" in t]
        bridges: list[dict] = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                for ca in self._text_columns(a):
                    for cb in self._text_columns(b):
                        qa, qb = ca.replace('"', '""'), cb.replace('"', '""')
                        da = self.db.execute(f'SELECT COUNT(DISTINCT "{qa}") FROM "{a}"').fetchone()[0]
                        if da > 5000:
                            continue
                        exact = self.db.execute(f'SELECT COUNT(DISTINCT x."{qa}") FROM "{a}" x WHERE lower(trim(x."{qa}")) IN (SELECT lower(trim(y."{qb}")) FROM "{b}" y)').fetchone()[0]
                        fuzzy = self.db.execute(f'SELECT COUNT(*) FROM (SELECT DISTINCT x."{qa}" v FROM "{a}" x) x WHERE EXISTS (SELECT 1 FROM (SELECT DISTINCT y."{qb}" v FROM "{b}" y) y WHERE jaro_winkler_similarity(lower(trim(x.v)), lower(trim(y.v))) >= 0.9)').fetchone()[0]
                        # same entity set spelled differently: nearly everything matches approximately, far from everything exactly
                        if fuzzy / da < 0.85 or exact / da > 0.8 or fuzzy - exact < 3:
                            continue
                        # the table with the larger distinct set is the master list; the other gets one normalised column
                        db_ = self.db.execute(f'SELECT COUNT(DISTINCT "{qb}") FROM "{b}"').fetchone()[0]
                        if db_ > da:
                            src, sc, ref, rc, n_src = a, ca, b, cb, da
                        else:
                            src, sc, ref, rc, n_src = b, cb, a, ca, db_
                        qs, qr = sc.replace('"', '""'), rc.replace('"', '""')
                        col = f"{sc} (as in {ref})"
                        qcol = col.replace('"', '""')
                        self.db.execute(f'''CREATE TEMP TABLE bridge_tmp AS
                            SELECT av, bv FROM (
                              SELECT x.v AS av, y.v AS bv, jaro_winkler_similarity(lower(trim(x.v)), lower(trim(y.v))) AS sim
                              FROM (SELECT DISTINCT "{qs}" v FROM "{src}" WHERE "{qs}" IS NOT NULL) x
                              JOIN (SELECT DISTINCT "{qr}" v FROM "{ref}" WHERE "{qr}" IS NOT NULL) y
                                ON jaro_winkler_similarity(lower(trim(x.v)), lower(trim(y.v))) >= 0.9)
                            QUALIFY ROW_NUMBER() OVER (PARTITION BY av ORDER BY sim DESC, bv) = 1''')
                        self.db.execute(f'ALTER TABLE "{src}" ADD COLUMN "{qcol}" VARCHAR')
                        self.db.execute(f'UPDATE "{src}" SET "{qcol}" = (SELECT bv FROM bridge_tmp WHERE bridge_tmp.av = "{src}"."{qs}")')
                        matched = self.db.execute('SELECT COUNT(*) FROM bridge_tmp').fetchone()[0]
                        self.db.execute('DROP TABLE bridge_tmp')
                        for t in self.tables:
                            if t.get("table") == src:
                                t["columns"].append(col)
                        bridges.append({"src": src, "src_col": sc, "ref": ref, "ref_col": rc, "col": col, "matched": matched, "of": n_src, "exact": exact})
        return bridges

    def _ddl(self) -> str:
        out = []
        for t in self.tables:
            if "table" not in t:
                continue
            cols = self.db.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position", [t["table"]]).fetchall()
            note = ""
            for br in self.bridges:
                if br["src"] == t["table"]:
                    note += (f'-- "{br["col"]}" was computed locally: "{br["src_col"]}" rewritten in the spelling used by {br["ref"]}."{br["ref_col"]}" '
                             f'(approximate match, {br["matched"]} of {br["of"]} values). '
                             f'To combine {t["table"]} with {br["ref"]}: ... JOIN ON {t["table"]}."{br["col"]}" = {br["ref"]}."{br["ref_col"]}" (never on the raw "{br["src_col"]}").\n')
                if br["ref"] == t["table"]:
                    note += f'-- {t["table"]}."{br["ref_col"]}" is the master spelling; {br["src"]} carries a matching column "{br["col"]}".\n'
            months = month_columns([c for c, _ in cols])
            if len(months) >= 4:
                qm = ", ".join(chr(34) + m + chr(34) for m in months)
                note += (f'-- columns {qm} are months of one measure laid side by side; a blank month means nothing that month, so add them as '
                         f'{" + ".join("COALESCE(" + chr(34) + m + chr(34) + ", 0)" for m in months[:2])} + ... ; to rank months use '
                         f'UNPIVOT "{t["table"]}" ON {qm} INTO NAME month VALUE amount.\n')
            if t.get("merged_case"):
                note += f'-- spelling variants differing only by case/spaces were merged in: {", ".join(chr(34) + c + chr(34) for c in t["merged_case"])}.\n'
            out.append(note + f'CREATE TABLE "{t["table"]}" (\n  ' + ",\n  ".join(f'"{c}" {k}' for c, k in cols) + "\n);")
        return "\n\n".join(out)

    def _categories(self, limit: int = 50) -> dict:
        res: dict = {}
        for t in self.tables:
            if "table" not in t:
                continue
            per: dict = {}
            cols = self.db.execute("SELECT column_name FROM information_schema.columns WHERE table_name = ? AND data_type IN ('VARCHAR','TEXT') ORDER BY ordinal_position", [t["table"]]).fetchall()
            for (c,) in cols:
                q = c.replace('"', '""')
                vals = [str(r[0]) for r in self.db.execute(f'SELECT DISTINCT "{q}" FROM "{t["table"]}" WHERE "{q}" IS NOT NULL ORDER BY 1 LIMIT {limit + 1}').fetchall()]
                if len(vals) <= limit:
                    per[c] = vals
            res[t["table"]] = per
        return res


WS = Workspace()


# ---------------------------------------------------------------- model call

def call_model(cfg: dict, prompt: str, max_tokens: int = 2500, timeout: int = 180) -> tuple[str, dict]:
    if cfg.get("source") == "local":
        endpoint, model, key = cfg.get("local_endpoint") or DEFAULT_CONFIG["local_endpoint"], cfg.get("local_model") or "local", ""
    else:
        endpoint, model, key = cfg.get("endpoint") or DEFAULT_CONFIG["endpoint"], cfg.get("model") or DEFAULT_CONFIG["model"], cfg.get("api_key", "")
        if not key:
            raise RuntimeError("No OpenRouter key set. Open Settings and paste a key, or switch to a local model.")
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens}
    if cfg.get("source") != "local":
        body["reasoning"] = {"enabled": False}
    else:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), headers=headers, method="POST")
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.load(resp)
    text = raw["choices"][0]["message"].get("content") or ""
    if not text.strip():
        raise RuntimeError("model returned no answer")
    return text, {"model": raw.get("model", model), "seconds": round(time.monotonic() - started, 2), "usage": raw.get("usage"),
                  "prompt_bytes": len(prompt.encode()), "rows_sent": 0}


def safe_sql(text: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.I | re.S)
    cand = fenced.group(1) if fenced else text
    start = re.search(r"\b(?:WITH|SELECT)\b", cand, flags=re.I)
    if not start:
        raise ValueError("no SELECT in answer")
    cand = cand[start.start():].strip().removesuffix("```").strip().rstrip(";")
    try:
        parsed = sqlglot.parse(cand, read="duckdb")
    except Exception:  # sqlglot does not know every DuckDB form (UNPIVOT, QUALIFY variants); DuckDB itself decides
        stmts = duckdb.extract_statements(cand)
        if len(stmts) != 1 or stmts[0].type != duckdb.StatementType.SELECT:
            raise ValueError("not exactly one read-only query")
        if re.search(r"\b(copy|export|install|load|attach|create|insert|update|delete|drop|pragma|set)\b", cand, re.I):
            raise ValueError("forbidden operation")
        return cand
    if len(parsed) != 1 or not isinstance(parsed[0], exp.Query):
        raise ValueError("not exactly one read-only query")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command, exp.Copy)
    if any(isinstance(n, forbidden) for n in parsed[0].walk()):
        raise ValueError("forbidden operation")
    return parsed[0].sql(dialect="duckdb")


def invented_numbers(sql: str, question: str) -> list[str]:
    """Numbers in the SQL that the user never said (wages, thresholds, conversion factors the model made up)."""
    said = set(re.findall(r"\d+(?:\.\d+)?", question))
    body = re.sub(r"'[^']*'|\"[^\"]*\"", " ", sql)  # ignore string literals and quoted identifiers
    nums = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", body))
    return sorted(n for n in nums if n not in said and n not in {"0", "1", "2", "100", "1.0", "100.0", "0.0"})


def tables_used(sql: str) -> list[str]:
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
        ctes = {c.alias_or_name for c in tree.find_all(exp.CTE)}
        return sorted({t.name for t in tree.find_all(exp.Table) if t.name not in ctes})
    except Exception:  # noqa: BLE001
        return []


def clean(v: Any) -> Any:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and v != v:
        return None
    if not isinstance(v, (int, float, str, bool)):
        if hasattr(v, "hour") and (v.hour, v.minute, v.second) == (0, 0, 0):
            return v.date().isoformat()
        return str(v)
    return v


def execute(sql: str) -> dict:
    cur = WS.db.execute("EXPLAIN " + sql)
    cur = WS.db.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [{c: clean(v) for c, v in zip(cols, r)} for r in cur.fetchall()]
    return {"columns": cols, "rows": rows, "error": None}


# ---------------------------------------------------------------- Ask lane

STOP = {"the", "a", "an", "of", "for", "per", "by", "in", "and", "or", "to", "with", "from", "is", "are", "how", "many", "much", "what", "which", "show", "me", "only", "top", "list", "all", "each", "every", "rate", "total", "count", "number", "average", "avg", "sum", "name", "names", "id", "no", "rs", "year", "years", "month", "months", "date", "file", "files", "two", "between", "vs", "versus", "side", "wise", "our", "we", "they", "their", "that", "this", "those"}


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) < 3 or w in STOP:
            continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def likely_tables(question: str) -> set[str]:
    """Tables whose name or column names share words with the question."""
    q = words(question)
    scored = []
    for t in WS.tables:
        if "table" not in t:
            continue
        vocab = words(t["table"].replace("_", " ")) | set().union(*(words(c.replace("_", " ")) for c in t["columns"]))
        hit = len(q & vocab)
        if hit:
            scored.append((hit, t["table"]))
    if not scored:
        return set()
    best = max(h for h, _ in scored)
    return {n for h, n in scored if h == best}


def prior_turns(question: str, limit: int = 4) -> list[dict]:
    """Earlier turns are context for follow-ups, but a question that clearly points at
    other tables starts a new topic; carrying the old SQL along makes small models
    join the wrong files."""
    turns = [t for t in WS.history if t.get("sql")]
    if not turns:
        return []
    last_tables = set(turns[-1].get("tables_used") or [])
    pointed = likely_tables(question)
    if pointed and last_tables and not (pointed & last_tables):
        return []
    return turns[-limit:]


def ask_prompt(question: str, repair: str | None) -> str:
    prior = [{"question": t["text"], "sql": t.get("sql"), "output_columns": t.get("columns")} for t in prior_turns(question)]
    rules = list(ASK_RULES)
    if WS.bridges:
        rules.append("Approximate name matching is ALREADY DONE for you: the '(as in ...)' columns hold each name in the other file's spelling; join on them with a plain = (LEFT JOIN from the table whose every row must be kept). "
                     "Never call jaro_winkler_similarity yourself.")
    parts = [*rules, f"SCHEMA:\n{WS.schema}", f"KNOWN CATEGORICAL VALUES:\n{json.dumps(WS.categories, ensure_ascii=False)}",
             f"PRIOR TURNS:\n{json.dumps(prior, ensure_ascii=False)}", f"CURRENT QUESTION:\n{question}"]
    if repair:
        parts.append(f"REJECTED QUERY ERROR:\n{repair}\nReturn a complete corrected query.")
    return "\n\n".join(parts)


def auto_viz(result: dict) -> dict:
    """Deterministic chart choice for an Ask answer."""
    cols, rows = result["columns"], result["rows"]
    if not rows:
        return {"kind": "empty"}
    first = rows[0]
    num = [c for c in cols if isinstance(first.get(c), (int, float)) and not isinstance(first.get(c), bool)]
    txt = [c for c in cols if c not in num]
    if len(rows) == 1 and len(cols) == 1 and num:
        return {"kind": "kpi"}
    if len(rows) == 1 and len(num) <= 4 and not txt:
        return {"kind": "kpis"}
    if len(txt) == 1 and 1 <= len(num) <= 3 and 2 <= len(rows) <= 120:
        x = txt[0]
        period = re.search(r"year|month|date|period|quarter|week|day", x, re.I) or all(re.match(r"^\d{4}(-\d{2})?", str(r.get(x))) for r in rows[:5])
        if period and len(rows) >= 3:
            return {"kind": "line", "x": x, "y": num}
        if len(rows) <= 20:
            return {"kind": "bar", "x": x, "y": num}
    if len(txt) == 0 and len(num) == 2 and len(rows) >= 3:
        x = num[0]
        if all(isinstance(r.get(x), int) and 1900 < r[x] < 2100 for r in rows):
            return {"kind": "line", "x": x, "y": [num[1]]}
    return {"kind": "table"}


def run_ask(text: str, cfg: dict) -> dict:
    repair = None
    attempts = []
    for _ in range(3):
        raw, meta = call_model(cfg, ask_prompt(text, repair), max_tokens=800)
        attempts.append({"raw": raw, "meta": meta})
        try:
            sql = safe_sql(raw)
            result = execute(sql)
        except Exception as exc:  # noqa: BLE001
            repair = f"{type(exc).__name__}: {str(exc)[:300]}"
            attempts[-1]["error"] = repair
            continue
        viz = auto_viz(result)
        used = tables_used(sql)
        prev = next((t for t in reversed(WS.history) if t.get("tables_used")), None)
        scope_note = None
        if prev and used and set(used) != set(prev["tables_used"]):
            scope_note = f"This answer uses {', '.join(used)}; the previous one used {', '.join(prev['tables_used'])}."
        invented = invented_numbers(sql, text)
        if invented:
            scope_note = (scope_note + " " if scope_note else "") + f"The query uses number(s) you did not mention: {', '.join(invented)} — check the receipt."
        turn = {"lane": "ask", "text": text, "sql": sql, "columns": result["columns"], "rowcount": len(result["rows"]), "tables_used": used, "scope_note": scope_note, "invented_numbers": invented,
                "rows": result["rows"][:200], "viz": viz, "attempts": len(attempts), "egress": meta, "html": ask_html(sql, result, viz, text)}
        turn["_full"] = result
        return turn
    return {"lane": "ask", "text": text, "error": f"I couldn't turn that into a query I can run. Last problem: {repair}", "attempts": attempts[-1] if attempts else None,
            "egress": attempts[-1]["meta"] if attempts else None}


def ask_html(sql: str, result: dict, viz: dict, question: str) -> str:
    pid = "a1"
    panel = {"id": pid, "kind": viz.get("kind", "table"), "title": question, "sql": sql, "x": viz.get("x"), "y": viz.get("y")}
    if viz["kind"] == "empty":
        return '<p class=empty>The query ran but returned no rows.</p>'
    if viz["kind"] == "kpi":
        return render_plan.kpi_html(panel, result)
    if viz["kind"] == "kpis":
        row = result["rows"][0]
        return "<div class=kpis>" + "".join(render_plan.kpi_html({"id": pid, "title": c}, {"columns": [c], "rows": [{c: row[c]}]}) for c in result["columns"]) + "</div>"
    return render_plan.panel_html(panel, result)


# ---------------------------------------------------------------- Build lane

def build_prompt(text: str, repair: str | None) -> str:
    request = text
    prior = [{"question": t["text"], "sql": t.get("sql")} for t in prior_turns(text, 3)]
    parts = [BUILD_CONTRACT + ("- Approximate name matching is already done: join on the '(as in ...)' columns with a plain = instead of comparing raw names.\n" if WS.bridges else ""), f"SCHEMA:\n{WS.schema}", f"KNOWN CATEGORICAL VALUES:\n{json.dumps(WS.categories, ensure_ascii=False)}"]
    if prior:
        parts.append(f"EARLIER QUESTIONS IN THIS SESSION (for context):\n{json.dumps(prior, ensure_ascii=False)}")
    parts.append(f"REQUEST:\n{request}")
    if repair:
        parts.append(f"PREVIOUS ATTEMPT PROBLEMS:\n{repair}\nReturn the complete corrected JSON plan.")
    return "\n\n".join(parts)


def extract_json(text: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    cand = fenced.group(1) if fenced else text
    s, e = cand.find("{"), cand.rfind("}")
    if s < 0:
        raise ValueError("no JSON object in answer")
    return json.loads(cand[s:e + 1])


KINDS = {"kpi", "bar", "stacked_bar", "line", "scatter", "pie", "table"}


def run_build(text: str, cfg: dict) -> dict:
    repair = None
    plan, results, metas = None, {}, []
    for attempt in range(2):
        raw, meta = call_model(cfg, build_prompt(text, repair), max_tokens=3000)
        metas.append(meta)
        try:
            cand = extract_json(raw)
            panels = cand.get("panels")
            if not isinstance(panels, list) or not panels:
                raise ValueError("plan has no panels")
            for i, p in enumerate(panels):
                p["id"] = p.get("id") or f"p{i + 1}"
                if p.get("kind") not in KINDS:
                    p["kind"] = "table"
        except Exception as exc:  # noqa: BLE001
            repair = f"Your previous answer could not be used: {exc}"
            continue
        res = {}
        bad = []
        for p in panels:
            try:
                res[p["id"]] = execute(safe_sql(p.get("sql", "")))
                if not res[p["id"]]["rows"]:
                    bad.append(f'{p["id"]}: query returned no rows')
                elif p.get("kind") == "kpi" and len(res[p["id"]]["rows"]) > 1:
                    p["kind"] = "table"  # a KPI must be one number; several rows read better as a table
            except Exception as exc:  # noqa: BLE001
                res[p["id"]] = {"columns": [], "rows": [], "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
                bad.append(f'{p["id"]}: {res[p["id"]]["error"]}')
        if plan is None or len(bad) < sum(1 for r in results.values() if r["error"] or not r["rows"]):
            plan, results = cand, res
        if not bad:
            break
        repair = "These panels failed when the laptop ran them:\n" + "\n".join(bad) + "\nFix only what is needed and return the full plan again."
    if plan is None:
        return {"lane": "build", "text": text, "error": f"I couldn't produce a page plan. {repair}", "egress": metas[-1] if metas else None}
    narrative = plan.get("narrative") or ""
    literals = render_plan.numeric_literal_lint(narrative) if narrative else []
    if literals:
        # the BS detector: numbers the model typed itself are not shown
        for lit in literals:
            narrative = re.sub(rf"(?<![\w.{{]){re.escape(lit)}(?![\w.}}])", "[number removed: not from a query]", narrative)
        plan["narrative"] = narrative
    mode = "report" if re.search(r"report|summar|brief|write", text, re.I) else "dashboard"
    source = ", ".join(sorted({t["file"] for t in WS.tables if "table" in t}))
    html_doc = render_plan.render(plan, results, source, template=mode, question=text)
    plan["_mode"] = mode
    egress = dict(metas[-1])
    egress["calls"] = len(metas)
    egress["seconds"] = round(sum(m["seconds"] for m in metas), 2)
    failed = [pid for pid, r in results.items() if r["error"] or not r["rows"]]
    return {"lane": "build", "text": text, "plan": plan, "page": html_doc, "panels": len(plan["panels"]), "panels_failed": failed,
            "lint_removed": literals, "egress": egress, "sql": plan["panels"][0].get("sql"), "columns": results[plan["panels"][0]["id"]]["columns"],
            "_full": {pid: r for pid, r in results.items()}}


def render_page_now(turn: dict) -> str:
    """Re-execute a stored plan against the current tables and render it; every view is live."""
    plan = turn["plan"]
    results = {}
    for p in plan["panels"]:
        try:
            results[p["id"]] = execute(safe_sql(p.get("sql", "")))
        except Exception as exc:  # noqa: BLE001
            results[p["id"]] = {"columns": [], "rows": [], "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    turn["_full"] = results
    source = ", ".join(sorted({t["file"] for t in WS.tables if "table" in t})) + f" · data as of {WS.changed_at}"
    return render_plan.render(plan, results, source, template=plan.get("_mode", "dashboard"), question=turn["text"])


# ---------------------------------------------------------------- Page lane (generic build)

PAGE_PROMPT = """You build small, self-contained web pages for a social-sector NGO. Return ONE complete HTML document and nothing else (no prose, no code fences). Rules: everything inline (CSS and JS in the file; no external URLs, no CDNs, no frameworks); must work offline from a file; must not throw console errors; clean readable layout; plain English labels. If the request needs a service worker, register it from an inline Blob URL so the single file is enough.{data_clause}

REQUEST:
{request}
"""


def extract_html(text: str) -> str:
    fenced = re.search(r"```(?:html)?\s*(<!doctype.*?|<html.*?)```", text, flags=re.I | re.S)
    cand = fenced.group(1) if fenced else text
    i = cand.lower().find("<!doctype")
    if i < 0:
        i = cand.lower().find("<html")
    if i < 0:
        raise ValueError("the model did not return an HTML page")
    j = cand.lower().rfind("</html>")
    return cand[i:(j + 7) if j > 0 else None]


def script_errors(html_doc: str) -> list[str]:
    """Syntax-check inline scripts (small models drop quotes and brackets). Needs esprima; silent if absent."""
    try:
        import esprima  # type: ignore
    except ImportError:
        return []
    errs = []
    for i, m in enumerate(re.finditer(r"<script(?![^>]*\bsrc=)(?![^>]*type=\"?(?:application/(?:ld\+)?json|text/template))[^>]*>([\s\S]*?)</script>", html_doc, re.I), 1):
        src = m.group(1)
        if not src.strip():
            continue
        try:
            esprima.parseScript(src, {"tolerant": False})
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            line = re.search(r"Line (\d+)", msg)
            snippet = ""
            if line:
                n = int(line.group(1))
                lines = src.split("\n")
                snippet = lines[n - 1].strip()[:160] if 0 < n <= len(lines) else ""
            errs.append(f"script {i}: {msg[:120]}" + (f" -> {snippet}" if snippet else ""))
    return errs


def js_key(col: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "_", col.lower()).strip("_")
    return ("c_" + k) if not k or k[0].isdigit() else k


def run_page(text: str, cfg: dict) -> dict:
    """Generic build: the model writes the page; rows never go to the model. If the request points
    at loaded data, the page is told the data arrives as window.data with these columns, and the
    laptop injects the real rows when the page is viewed."""
    pointed = sorted(likely_tables(text))
    data_clause = ""
    data_table = None
    if pointed:
        data_table = pointed[0]
        cols = next(t["columns"] for t in WS.tables if t.get("table") == data_table)
        keys = {c: js_key(c) for c in cols}
        data_clause = (" The data will be available at runtime as window.data — an array of row objects with exactly these keys (simple identifiers, use dot access): "
                       + ", ".join(f"{k} ({c})" for c, k in keys.items())
                       + ". Compute everything from window.data in the browser; never hardcode numbers or rows; show friendly labels, not the keys.")
    prompt = PAGE_PROMPT.format(data_clause=data_clause, request=text)
    raw, meta = call_model(cfg, prompt, max_tokens=8000, timeout=420)
    html_doc = extract_html(raw)
    errs = script_errors(html_doc)
    calls = 1
    if errs:
        fix_prompt = prompt + "\n\nYOUR PREVIOUS PAGE HAD JAVASCRIPT SYNTAX ERRORS:\n" + "\n".join(errs) + "\nReturn the complete corrected HTML document."
        raw2, meta2 = call_model(cfg, fix_prompt, max_tokens=8000, timeout=420)
        calls = 2
        try:
            cand = extract_html(raw2)
            if not script_errors(cand):
                html_doc, errs = cand, []
        except ValueError:
            pass
        meta = {**meta2, "seconds": round(meta["seconds"] + meta2["seconds"], 2)}
    meta["calls"] = calls
    probe = []
    if data_table:
        try:
            cols = next(t["columns"] for t in WS.tables if t.get("table") == data_table)
            tcol = next((c for c in cols if c in WS.categories.get(data_table, {}) and 2 <= len(WS.categories[data_table][c]) <= 50), None)
            if tcol:
                probe = WS.categories[data_table][tcol][:6]
        except Exception:  # noqa: BLE001
            probe = []
    return {"lane": "page", "text": text, "page_html": html_doc, "data_table": data_table, "egress": meta, "bytes": len(html_doc), "script_errors": errs, "data_probe": probe}


CAPTURE = "<script>window.__ioErrors=[];window.addEventListener('error',function(e){window.__ioErrors.push((e.message||'error')+(e.lineno?' (line '+e.lineno+')':''))});window.addEventListener('unhandledrejection',function(e){window.__ioErrors.push('promise: '+String(e.reason).slice(0,160))});</script>"


def page_with_data(turn: dict) -> str:
    html_doc = turn["page_html"]
    i = html_doc.lower().find("<head>")
    html_doc = (html_doc[:i + 6] + CAPTURE + html_doc[i + 6:]) if i >= 0 else CAPTURE + html_doc
    if turn.get("data_table"):
        try:
            cur = WS.db.execute(f'SELECT * FROM "{turn["data_table"]}" LIMIT 20000')
            cols = [js_key(d[0]) for d in cur.description]
            rows = [{c: clean(v) for c, v in zip(cols, r)} for r in cur.fetchall()]
        except Exception:  # noqa: BLE001
            rows = []
        inject = "<script>window.data = " + json.dumps(rows, default=str).replace("</", "<\\/") + ";</script>"
        i = html_doc.lower().find("<head>")
        html_doc = (html_doc[:i + 6] + inject + html_doc[i + 6:]) if i >= 0 else inject + html_doc
    return html_doc


# ---------------------------------------------------------------- HTTP

def csv_text(result: dict) -> str:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(result["columns"])
    for r in result["rows"]:
        w.writerow([r.get(c) for c in result["columns"]])
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, code: int = 200) -> None:
        self._send(code, json.dumps(obj, default=str).encode())

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._send(200, (UI / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/state":
            cfg = load_config()
            return self._json({"folder": str(WS.folder) if WS.folder else None, "tables": WS.tables, "version": getattr(WS, "version", 0), "changed_at": getattr(WS, "changed_at", None),
                               "config": {**cfg, "api_key": ("set" if cfg.get("api_key") else "")},
                               "history": [{k: v for k, v in t.items() if k not in ("_full", "page", "rows")} for t in WS.history]})
        m = re.match(r"^/api/page/(\d+)$", path)
        if m:
            t = WS.turns.get(m.group(1))
            if not t or ("plan" not in t and "page_html" not in t):
                return self._send(404, b"no page")
            with WS.lock:
                page = page_with_data(t) if t.get("lane") == "page" else render_page_now(t)
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        m = re.match(r"^/api/rerun/(\d+)$", path)
        if m:
            t = WS.turns.get(m.group(1))
            if not t or t.get("lane") != "ask" or not t.get("sql"):
                return self._send(404, b"no turn")
            with WS.lock:
                try:
                    result = execute(t["sql"])
                    t["_full"] = result
                    t["rowcount"] = len(result["rows"])
                    html_frag = ask_html(t["sql"], result, auto_viz(result), t["text"])
                    return self._json({"html": html_frag, "rowcount": len(result["rows"]), "version": WS.version})
                except Exception as exc:  # noqa: BLE001
                    return self._json({"error": str(exc)[:300]}, 500)
        m = re.match(r"^/api/csv/(\d+)/([\w-]+)$", path)
        if m:
            t = WS.turns.get(m.group(1))
            if not t:
                return self._send(404, b"no turn")
            full = t.get("_full")
            res = full if t["lane"] == "ask" else (full or {}).get(m.group(2))
            if not res:
                return self._send(404, b"no data")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", f'attachment; filename="{m.group(2)}.csv"')
            self.end_headers()
            self.wfile.write(csv_text(res).encode())
            return None
        m = re.match(r"^/api/download-page/(\d+)$", path)
        if m:
            t = WS.turns.get(m.group(1))
            if not t or "page_html" not in t:
                return self._send(404, b"no page")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="io-page.html"')
            self.end_headers()
            self.wfile.write(page_with_data(t).encode())
            return None
        if path.startswith("/ui/"):
            f = (UI / path[4:]).resolve()
            if f.is_file() and UI in f.parents:
                ctype = "text/css" if f.suffix == ".css" else "application/javascript" if f.suffix == ".js" else "application/octet-stream"
                return self._send(200, f.read_bytes(), ctype)
        return self._send(404, b"not found")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        try:
            if self.path == "/api/folder":
                folder = Path(body.get("path", "")).expanduser()
                if not folder.is_dir():
                    return self._json({"error": f"Not a folder: {folder}"}, 400)
                with WS.lock:
                    WS.load(folder)
                return self._json({"folder": str(folder), "tables": WS.tables})
            if self.path == "/api/config":
                cfg = load_config()
                for k in ("source", "endpoint", "model", "local_endpoint", "local_model"):
                    if k in body:
                        cfg[k] = body[k]
                if body.get("api_key") and body["api_key"] != "set":
                    cfg["api_key"] = body["api_key"].strip()
                if body.get("clear_key"):
                    cfg["api_key"] = ""
                save_config(cfg)
                return self._json({"ok": True, "config": {**cfg, "api_key": "set" if cfg.get("api_key") else ""}})
            if self.path == "/api/ask":
                text = (body.get("text") or "").strip()
                if not text:
                    return self._json({"error": "empty question"}, 400)
                if not WS.tables:
                    return self._json({"error": "Open a folder with CSV or Excel files first."}, 400)
                cfg = load_config()
                lane = body.get("lane")
                if not lane:
                    if PAGE_WORDS.search(text) and not re.search(r"\b(dashboard|report|summar\w*)\b", text, re.I):
                        lane = "page"
                    elif BUILD_WORDS.search(text):
                        lane = "build"
                    else:
                        lane = "ask"
                with WS.lock:
                    turn = run_page(text, cfg) if lane == "page" else run_build(text, cfg) if lane == "build" else run_ask(text, cfg)
                    turn["id"] = str(len(WS.history) + 1)
                    turn["at"] = time.strftime("%H:%M:%S")
                    WS.history.append(turn)
                    WS.turns[turn["id"]] = turn
                return self._json({k: v for k, v in turn.items() if k not in ("_full", "page", "page_html", "attempts")})
            m = re.match(r"^/api/page-repair/(\d+)$", self.path)
            if m:
                t = WS.turns.get(m.group(1))
                if not t or "page_html" not in t:
                    return self._json({"error": "no page"}, 404)
                errors = [str(e)[:200] for e in (body.get("errors") or [])][:5]
                if body.get("no_data_shown"):
                    errors.append("The page does not display the real data: none of the values from window.data appear on screen, so it is showing made-up content. Every list, count and label must come from window.data; remove any invented rows or names.")
                if t.get("repaired") or not errors:
                    return self._json({"repaired": False})
                cfg = load_config()
                with WS.lock:
                    t["repaired"] = True
                    prompt = ("You wrote this HTML page:\n\n" + t["page_html"][:60000] + "\n\nWhen it ran in the browser it threw these errors:\n" + "\n".join(errors)
                              + "\nFix the causes (missing elements, wrong ids, wrong keys) and return the complete corrected HTML document and nothing else.")
                    try:
                        raw, meta = call_model(cfg, prompt, max_tokens=8000, timeout=420)
                        cand = extract_html(raw)
                        if not script_errors(cand):
                            t["page_html"] = cand
                            t["egress"]["seconds"] = round(t["egress"].get("seconds", 0) + meta["seconds"], 2)
                            t["egress"]["calls"] = t["egress"].get("calls", 1) + 1
                            return self._json({"repaired": True, "errors": errors})
                    except Exception as exc:  # noqa: BLE001
                        return self._json({"repaired": False, "error": str(exc)[:200]})
                return self._json({"repaired": False})
            if self.path == "/api/reset":
                with WS.lock:
                    WS.history, WS.turns = [], {}
                return self._json({"ok": True})
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._json({"error": f"{type(exc).__name__}: {str(exc)[:400]}"}, 500)
        return self._json({"error": "unknown endpoint"}, 404)


def main() -> None:
    port = int(os.environ.get("IO_PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8791))
    folder = os.environ.get("IO_FOLDER")
    if folder:
        WS.load(Path(folder))
    threading.Thread(target=WS.watch, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"io service on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
