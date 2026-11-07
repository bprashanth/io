"""Sheets site plugin: Excel/CSV files in the workspace folder, queried with DuckDB.

The model never gets a whole sheet. It gets a profile (columns, types, blanks, a few example
rows), runs SQL, and asks for charts, which are written as self-contained HTML (inline SVG,
no scripts or CDN) next to the data so the user can open them from the chat.
Files are only read; the tools never change a spreadsheet.
"""
import html
import os
import re

import duckdb
import pandas as pd

EXTS = (".xlsx", ".xlsm", ".xls", ".csv")
_con = duckdb.connect()
_tables = {}  # table name -> {"file", "sheet", "columns": {sql_name: original}}


def data_dir():
    return os.environ.get("COWORK_DATA_DIR") or os.getcwd()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_") or "x"


def files():
    out = []
    root = data_dir()
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("dashboards", "checked")]
        if dirpath.count(os.sep) - root.count(os.sep) > 1:
            continue
        for n in sorted(names):
            if n.lower().endswith(EXTS) and not n.startswith("~$"):
                out.append(os.path.relpath(os.path.join(dirpath, n), root))
    return out


def resolve(file):
    path = os.path.realpath(os.path.join(data_dir(), file))
    if not path.startswith(os.path.realpath(data_dir()) + os.sep) or not os.path.isfile(path):
        raise ValueError(f"No file '{file}' in the workspace folder. Use sheet_list.")
    return path


def raw_frames(path):
    if path.lower().endswith(".csv"):
        return {"csv": pd.read_csv(path, header=None, dtype=object, keep_default_na=False)}
    return pd.read_excel(path, sheet_name=None, header=None, dtype=object)


def find_header(df):
    """First row that looks like column names: mostly text, and about as wide as the data."""
    df = df.replace("", None).dropna(how="all").dropna(axis=1, how="all")
    width = df.notna().sum(axis=1).max() if len(df) else 0
    for i, (_, row) in enumerate(df.iterrows()):
        vals = [v for v in row if v is not None and str(v).strip() != ""]
        texts = [v for v in vals if isinstance(v, str) and not re.fullmatch(r"[\d.,/ -]+", v)]
        if len(vals) >= max(2, 0.6 * width) and len(texts) >= 0.8 * len(vals):
            return df, i
    return df, 0


def load(file, sheet=None):
    path = resolve(file)
    frames = raw_frames(path)
    sheet = sheet if sheet is not None else next(iter(frames))
    if sheet not in frames:
        raise ValueError(f"No sheet '{sheet}'. Sheets: {list(frames)}")
    df, h = find_header(frames[sheet])
    header = [str(v).strip() if v is not None else f"column_{j + 1}" for j, v in enumerate(df.iloc[h])]
    body = df.iloc[h + 1:].copy()
    names, seen = [], {}
    for c in header:
        n = slug(c)
        seen[n] = seen.get(n, 0) + 1
        names.append(n if seen[n] == 1 else f"{n}_{seen[n]}")
    body.columns = names
    body = body.dropna(how="all")
    for c in names:  # numbers stay numbers; text stays text
        conv = pd.to_numeric(body[c], errors="coerce")
        if conv.notna().sum() >= 0.9 * body[c].notna().sum() and body[c].notna().any():
            body[c] = conv
        else:
            body[c] = body[c].map(lambda v: None if v is None else str(v).strip())
    table = slug(os.path.splitext(os.path.basename(file))[0]) + ("" if sheet == "csv" else "__" + slug(sheet))
    _con.register(table, body.reset_index(drop=True))
    _tables[table] = {"file": file, "sheet": sheet, "columns": dict(zip(names, header))}
    return table, body, int(df.index[h]) + 1, list(frames)


def rows(df, n=None):
    out = df.head(n) if n else df
    return [{k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
            for r in out.to_dict("records")]


# ---------------------------------------------------------------- tools
def t_sheet_list():
    out = []
    for f in files():
        try:
            frames = raw_frames(resolve(f))
            out.append({"file": f, "sheets": [{"sheet": s, "rows": int(d.shape[0])} for s, d in frames.items()]})
        except Exception as e:  # unreadable file: say so, keep going
            out.append({"file": f, "error": str(e)[:120]})
    return {"folder": data_dir(), "files": out,
            "note": "Open a file with file_open before answering questions about it." if out else "No Excel or CSV files here."}


def t_sheet_profile(file, sheet=None):
    table, df, header_row, sheets = load(file, sheet)
    cols = []
    for c, orig in _tables[table]["columns"].items():
        s = df[c]
        col = {"column": c, "header": orig, "type": "number" if pd.api.types.is_numeric_dtype(s) else "text",
               "blank": int(s.isna().sum()), "distinct": int(s.nunique()),
               "examples": [str(v)[:40] for v in s.dropna().unique()[:3]]}
        groups = variants(s) if col["type"] == "text" else []
        if groups:
            col["spelling_variants"] = groups
        cols.append(col)
    cleaning = [c["column"] for c in cols if c.get("spelling_variants")]
    return {"table": table, "file": file, "sheet": _tables[table]["sheet"], "other_sheets": sheets,
            "rows": int(len(df)), "header_found_on_row": header_row, "columns": cols,
            "first_rows": rows(df, 3),
            "note": f"Query it with sheet_query, e.g. SELECT * FROM {table} LIMIT 5."
                    + (f" IMPORTANT: {', '.join(cleaning)} have spelling_variants that mean the same thing; "
                       "merge each group (CASE WHEN ... THEN ...) before counting or grouping." if cleaning else "")
                    + " Dates may need try_strptime."}


def variants(s, max_distinct=60):
    """Groups of values in a short text column that probably mean the same thing
    (case/spacing differences or near-identical spellings, e.g. 'Malvalli' / 'Malavalli')."""
    import difflib
    vals = [v for v in s.dropna().unique() if str(v).strip()]
    if not 2 <= len(vals) <= max_distinct:
        return []
    key = {v: re.sub(r"[^a-z0-9]", "", str(v).lower()) for v in vals}
    parent = {v: v for v in vals}

    def find(v):
        while parent[v] != v:
            v = parent[v]
        return v
    for i, a in enumerate(vals):
        for b in vals[i + 1:]:
            ka, kb = key[a], key[b]
            if ka == kb or (min(len(ka), len(kb)) >= 5 and difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.88):
                parent[find(b)] = find(a)
    groups = {}
    for v in vals:
        groups.setdefault(find(v), []).append(str(v))
    counts = s.value_counts()
    return [sorted(g, key=lambda x: -int(counts.get(x, 0))) for g in groups.values() if len(g) > 1][:10]


def t_sheet_query(sql, max_rows=50):
    if not re.match(r"\s*(select|with|describe|summarize|show)\b", sql, re.I):
        return {"error": "Only SELECT/WITH/DESCRIBE/SUMMARIZE queries; the files are read-only."}
    if not _tables:
        return {"error": "No sheet loaded yet. Call sheet_profile(file) first."}
    try:
        df = _con.execute(sql).fetchdf()
    except duckdb.Error as e:
        return {"error": str(e).split("\n")[0][:300], "tables": {t: list(v["columns"]) for t, v in _tables.items()}}
    return {"rows": rows(df, max_rows), "row_count": int(len(df)),
            "truncated": len(df) > max_rows}


def bar_svg(labels, values, color="#3b6ea8"):
    w, bar_h, gap, left = 640, 26, 8, 200
    vmax = max([v for v in values if v is not None] + [1])
    h = len(labels) * (bar_h + gap) + 10
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = 5 + i * (bar_h + gap)
        bw = 0 if v is None else (w - left - 70) * v / vmax
        parts.append(f'<text x="{left - 8}" y="{y + 17}" text-anchor="end" font-size="13" fill="currentColor">'
                     f'{html.escape(str(lab))[:30]}</text>'
                     f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="3" fill="{color}"/>'
                     f'<text x="{left + bw + 6:.1f}" y="{y + 17}" font-size="12" fill="currentColor">'
                     f'{"" if v is None else f"{v:,.4g}"}</text>')
    return "".join(parts) + "</svg>"


def t_sheet_chart(title, charts):
    """charts: [{"sql": ..., "title": ...}] — each query's first column is the label, second the value."""
    blocks = []
    for ch in charts[:6]:
        r = t_sheet_query(ch["sql"], max_rows=40)
        if "error" in r:
            return {"error": f"Chart '{ch.get('title', '')}': {r['error']}"}
        if not r["rows"]:
            continue
        keys = list(r["rows"][0])
        labels = [row[keys[0]] for row in r["rows"]]
        values = [row[keys[1]] if len(keys) > 1 and isinstance(row[keys[1]], (int, float)) else None
                  for row in r["rows"]]
        blocks.append(f'<section><h2>{html.escape(ch.get("title", ""))}</h2>{bar_svg(labels, values)}</section>')
    out_dir = os.path.join(data_dir(), "dashboards")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug(title) + ".html")
    with open(path, "w") as f:
        f.write(f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{{color-scheme:light dark}}body{{font:15px system-ui,sans-serif;margin:24px;max-width:820px}}
section{{border:1px solid #8884;border-radius:10px;padding:12px 16px;margin:14px 0;overflow:hidden}}svg{{max-width:100%;height:auto;display:block}}h2{{font-size:16px}}</style>
</head><body><h1>{html.escape(title)}</h1>{''.join(blocks)}</body></html>""")
    rel = os.path.relpath(path, data_dir())
    return {"dashboard": rel, "charts": len(blocks),
            "note": f"Tell the user the dashboard is at {rel}; Paseo shows an Open button for it."}


TOOLS = {
    "sheet_list": (t_sheet_list, "List the Excel/CSV files in the workspace folder and their sheets.", {}, []),
    "sheet_profile": (t_sheet_profile, "Load one sheet and describe it: columns, types, blanks, examples, first rows. "
                      "Finds the header row even under title rows. Returns the SQL table name.",
                      {"file": {"type": "string"}, "sheet": {"type": "string"}}, ["file"]),
    "sheet_query": (t_sheet_query, "Run a read-only DuckDB SQL query over loaded sheets. Use it only when the user chose not to "
                    "teach Idli a file; otherwise use file_open and file_answer. Returns at most max_rows rows.",
                    {"sql": {"type": "string"}, "max_rows": {"type": "integer"}}, ["sql"]),
    "sheet_chart": (t_sheet_chart, "Make a dashboard of bar charts. Each chart is a SQL query whose first column is "
                    "the label and second column the number. Writes an HTML file and returns its path.",
                    {"title": {"type": "string"},
                     "charts": {"type": "array", "items": {"type": "object", "properties": {
                         "title": {"type": "string"}, "sql": {"type": "string"}}, "required": ["sql"]}}},
                    ["title", "charts"]),
}


def whoami():
    """Local files need no sign-in."""
    return "local files"
