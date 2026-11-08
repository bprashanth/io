"""Idli's Drive index: a quick local catalogue of the user's Drive, so finding a file takes milliseconds
instead of minutes of live searching.

Built on the user's computer by Idli, with the user's consent, through their signed-in browser:
  1. list   - My Drive (into folders, a few levels) and Shared with me: name, kind, folder path, id
  2. peek   - the first rows of each Google Sheet and the opening lines of each Google Doc
  3. summarise - Muse (the private local model) writes one line per file: what it is, key words
Everything stays in DuckDB at ~/idli-insights/config/drive-index.duckdb. Nothing is sent anywhere else.
The whole run is capped (default 5 minutes); what's done is usable at once, and summaries fill in last.

  python -I lib/driveindex.py build     (started by the drive_index tool; needs PASEO_AGENT_ID for the browser)
  python -I lib/driveindex.py status
  python -I lib/driveindex.py find "<words>"
"""
import concurrent.futures as cf
import datetime as dt
import difflib
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

IDLI = os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights")
DB = os.environ.get("IDLI_DRIVE_INDEX") or os.path.join(IDLI, "config", "drive-index.duckdb")
STATE = os.path.splitext(DB)[0] + ".json"
MUSE = (os.environ.get("MUSE_URL") or "http://127.0.0.1:8181") + "/v1/chat/completions"

KINDS = ["Google Sheets", "Google Docs", "Google Slides", "Google Forms", "Google Drawings", "Google My Maps",
         "Google Colab", "Google Sites", "Microsoft Excel", "Microsoft Word", "Microsoft PowerPoint", "Shared folder",
         "Folder", "PDF", "Image", "Video", "Audio", "Text", "CSV", "Compressed archive", "Unknown"]
ROWS_JS = ('() => { const out = []; const seen = {};'
           ' for (const e of document.querySelectorAll("[data-id]")) { const id = e.getAttribute("data-id");'
           '  if (id.length < 20 || seen[id]) continue; seen[id] = 1;'
           '  out.push({id, label: (e.getAttribute("aria-label") || "").replace(/ More info.*$/, ""),'
           '            text: (e.innerText || "").replace(/\\s+/g, " ").slice(0, 300)}); }'
           ' for (const x of document.querySelectorAll("*")) { if (x.scrollHeight > x.clientHeight + 50'
           '  && /auto|scroll/.test(getComputedStyle(x).overflowY)) x.scrollTop = x.scrollHeight; }'
           ' return JSON.stringify(out); }')


# ---------------------------------------------------------------- state
def _write_state(**kw):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    st = status()
    st.update(kw, updated=dt.datetime.now().isoformat(timespec="seconds"))
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)
    return st


def status():
    try:
        with open(STATE) as f:
            st = json.load(f)
    except (OSError, ValueError):
        return {"phase": "none"}
    pid = st.get("pid")
    if st.get("phase") not in ("done", "failed", "none") and pid:
        try:
            os.kill(pid, 0)
        except OSError:
            st["phase"] = "stopped"
    return st


def connect(read_only=False):
    import duckdb
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = duckdb.connect(DB, read_only=read_only and os.path.exists(DB))
    if not read_only:
        con.execute("""CREATE TABLE IF NOT EXISTS files (
            id VARCHAR PRIMARY KEY, name VARCHAR, kind VARCHAR, path VARCHAR, where_ VARCHAR,
            peek VARCHAR, summary VARCHAR, indexed_at TIMESTAMP, modified DATE)""")
        con.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS modified DATE")
    return con


# ---------------------------------------------------------------- parsing what Drive shows
def parse_label(label):
    """'volunteer_register Google Sheets' -> ('volunteer_register', 'Google Sheets')."""
    label = (label or "").strip()
    for k in sorted(KINDS, key=len, reverse=True):
        if label.endswith(" " + k):
            return label[: -len(k) - 1].strip(), k
    return label, "Unknown"


MEDIA = ("Image", "Video", "Audio")
_MON3 = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


def parse_modified(text, today=None):
    """Drive's list shows when a file was last modified: '7 Nov 2025', 'Nov 7, 2025', 'Nov 7' (this year) or
    '10:01 AM' (today). Returns a date or None."""
    t = today or dt.date.today()
    s = (text or "").lower()
    for pat, order in ((r"\b(\d{1,2}) (" + _MON3 + r")[a-z]* (\d{4})\b", "dmy"), (r"\b(" + _MON3 + r")[a-z]* (\d{1,2}),? (\d{4})\b", "mdy"),
                       (r"\b(\d{1,2}) (" + _MON3 + r")[a-z]*\b", "dm"), (r"\b(" + _MON3 + r")[a-z]* (\d{1,2})\b", "md")):
        m = re.search(pat, s)
        if not m:
            continue
        g = m.groups()
        try:
            if order == "dmy":
                return dt.date(int(g[2]), MONTHS3[g[1]], int(g[0]))
            if order == "mdy":
                return dt.date(int(g[2]), MONTHS3[g[0]], int(g[1]))
            d = dt.date(t.year, MONTHS3[g[1] if order == "dm" else g[0]], int(g[0] if order == "dm" else g[1]))
            return d if d <= t else d.replace(year=t.year - 1)
        except ValueError:
            continue
    if re.search(r"\b\d{1,2}:\d{2}\s?(am|pm)?\b", s):
        return t
    return None


MONTHS3 = {m: i for i, m in enumerate(_MON3.split("|"), 1)}


def is_folder(kind):
    return kind in ("Folder", "Shared folder")


# ---------------------------------------------------------------- crawl (browser)
SETTLE = float(os.environ.get("IDLI_INDEX_SETTLE") or 2.5)
SCROLL_WAIT = float(os.environ.get("IDLI_INDEX_SCROLL_WAIT") or 1.0)


def _rows(tab, url, deadline, max_scrolls=200):
    """Every row of a Drive list page. Big folders load more rows as the list scrolls (ROWS_JS scrolls to the
    bottom each time), so keep going until two reads in a row add nothing."""
    from lib.browser import evaluate, paseo
    paseo("browser_navigate", browserId=tab, url=url)
    time.sleep(SETTLE)
    seen, order, same = set(), [], 0
    for _ in range(max_scrolls):
        new = 0
        for r in evaluate(tab, ROWS_JS) or []:
            if r["id"] not in seen:
                seen.add(r["id"])
                order.append(r)
                new += 1
        same = 0 if new else same + 1
        if same >= 2 or time.time() > deadline:
            break
        time.sleep(SCROLL_WAIT)
    return order


def crawl(tabs, deadline, max_depth=10, max_files=5000):
    """Breadth first from My Drive and Shared with me, into folders up to max_depth levels, several folders at
    once (one per tab). Shallow files are found first, so a time limit cuts off only the deepest corners. A
    folder is opened once even if it shows up in several places (shortcuts, shared folders also in My Drive),
    so loops can't happen. Returns (files, folders_not_opened)."""
    from sites.google import tools as g
    if isinstance(tabs, str):
        tabs = [tabs]
    found, opened = {}, set()
    queue = [("my-drive", "My Drive", g.drive_url("my-drive"), 0, "root:my-drive"),
             ("shared", "Shared with me", g.drive_url("shared-with-me"), 0, "root:shared")]
    free = list(tabs)
    with cf.ThreadPoolExecutor(len(tabs)) as ex:
        running = {}
        while (queue or running) and len(found) < max_files:
            while queue and free and time.time() < deadline:
                item = queue.pop(0)
                if item[4] in opened:
                    continue
                opened.add(item[4])
                t = free.pop()
                running[ex.submit(_rows, t, item[2], deadline)] = (item, t)
            if not running:
                break
            done, _ = cf.wait(running, return_when=cf.FIRST_COMPLETED)
            for fut in done:
                (root, path, url, depth, fid), t = running.pop(fut)
                free.append(t)
                try:
                    rows = fut.result()
                except Exception:
                    continue  # one folder that won't load doesn't stop the rest
                for r in rows:
                    name, kind = parse_label(r["label"])
                    if not name:
                        continue
                    if r["id"] not in found:
                        found[r["id"]] = {"id": r["id"], "name": name, "kind": kind, "path": path, "where_": root,
                                          "modified": parse_modified((r.get("text") or "").replace(name, " ", 1))}
                    if is_folder(kind) and depth < max_depth and r["id"] not in opened:
                        queue.append((root, f"{path} / {name}", g.drive_url(f"folders/{r['id']}"), depth + 1, r["id"]))
            _write_state(phase="listing", files=len(found), folders_opened=len(opened), folders_left=len(queue))
    return list(found.values()), len({q[4] for q in queue} - opened)


def peek(tab, f):
    """A few lines of what's inside: first rows of a Google Sheet, opening lines of a Google Doc."""
    from lib.browser import paseo, snapshot
    from sites.google import tools as g
    try:
        if f["kind"] == "Google Sheets":
            paseo("browser_navigate", browserId=tab,
                  url=g.sheets_url(f["id"], "gviz/tq?tqx=out:html&tq=" + urllib.request.quote("select * limit 6")))
            snap = snapshot(tab, lambda s: "- table" in s or "Error" in s[:400], tries=5)
            rows = g.parse_gviz_table(snap)
            return " | ".join(", ".join(c for c in r if c)[:160] for r in rows[:6])[:700]
        if f["kind"] == "Google Docs":
            _, paras = g.doc_text(tab, f["id"])
            return " ".join(paras)[:700]
    except Exception as e:  # one unreadable file never stops the index
        return f"(not read: {type(e).__name__})"
    return ""


def summarise(batch, timeout=180):
    """One line per file from Muse. batch: list of file dicts. Returns {id: summary}."""
    items = [{"n": i + 1, "name": f["name"], "kind": f["kind"], "folder": f["path"], "inside": (f.get("peek") or "")[:400]}
             for i, f in enumerate(batch)]
    prompt = ("For each file, write one short line: what it is and the key words someone might search for "
              "(people, places, projects, topics, years). Use only what is shown. Reply with JSON only: "
              '{"1": "...", "2": "..."}\n\n' + json.dumps(items, ensure_ascii=False))
    body = {"model": "muse-glimmer-30b", "temperature": 0, "max_tokens": 4000, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(MUSE, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.load(r)["choices"][0]["message"]["content"] or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    got = json.loads(m.group(0)) if m else {}
    return {batch[int(k) - 1]["id"]: str(v)[:300] for k, v in got.items() if str(k).isdigit() and 0 < int(k) <= len(batch)}


def build(minutes=5.0, workers=5, muse_parallel=4):
    from lib.browser import paseo
    started = time.time()
    deadline = started + minutes * 60
    _write_state(phase="listing", pid=os.getpid(), started=dt.datetime.now().isoformat(timespec="seconds"),
                 files=0, peeked=0, summarised=0, error=None)
    tabs = []
    try:
        for _ in range(max(1, workers)):
            out = paseo("browser_new_tab", url="https://drive.google.com/drive/my-drive")
            m = re.search(r"browserId=(\S+)", out) or re.search(r'"browserId"\s*:\s*"([^"]+)"', out)
            if m:
                tabs.append(m.group(1))
        if not tabs:
            raise RuntimeError("could not open a browser tab")
        files, unopened = crawl(tabs, started + minutes * 60 * 0.5)
        _write_state(folders_not_opened=unopened)
        con = connect()
        now = dt.datetime.now()
        con.execute("DELETE FROM files")
        for f in files:
            con.execute("INSERT INTO files (id, name, kind, path, where_, indexed_at, modified) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [f["id"], f["name"], f["kind"], f["path"], f["where_"], now, f.get("modified")])
        con.close()
        _write_state(phase="reading", files=len(files))
        todo = [f for f in files if f["kind"] in ("Google Sheets", "Google Docs")]
        done = 0
        with cf.ThreadPoolExecutor(len(tabs)) as ex:
            free = list(tabs)
            futs = {}
            it = iter(todo)
            def submit():
                f = next(it, None)
                if f is not None and free and time.time() < deadline - 60:
                    t = free.pop()
                    futs[ex.submit(peek, t, f)] = (f, t)
            for _ in range(len(tabs)):
                submit()
            while futs:
                d, _ = cf.wait(futs, return_when=cf.FIRST_COMPLETED)
                for fut in d:
                    f, t = futs.pop(fut)
                    f["peek"] = fut.result()
                    free.append(t)
                    done += 1
                    submit()
                _write_state(peeked=done)
        con = connect()
        for f in todo:
            if f.get("peek") is not None:
                con.execute("UPDATE files SET peek = ? WHERE id = ?", [f["peek"], f["id"]])
        con.close()
    except Exception as e:
        _write_state(phase="failed", error=f"{type(e).__name__}: {e}"[:300])
        raise
    finally:
        for t in tabs:
            try:
                paseo("browser_close_tab", browserId=t)
            except Exception:
                pass
    # Muse summaries, several batches at once (Muse serves 4 slots), while time remains; search works already
    _write_state(phase="summarising")
    # media (photos, videos) and folders keep their metadata only: name, folder, date
    order = [f for f in sorted(files, key=lambda f: 0 if f.get("peek") else 1)
             if not is_folder(f["kind"]) and f["kind"] not in MEDIA]
    batches = [order[i:i + 12] for i in range(0, len(order), 12)]
    n = 0
    with cf.ThreadPoolExecutor(max(1, muse_parallel)) as ex:
        futs = {ex.submit(summarise, b, max(30, int(deadline - time.time()))): b for b in batches}
        try:
            for fut in cf.as_completed(futs, timeout=max(5, deadline - time.time())):
                try:
                    got = fut.result()
                except Exception:
                    continue
                con = connect()
                for fid, s_ in got.items():
                    con.execute("UPDATE files SET summary = ? WHERE id = ?", [s_, fid])
                con.close()
                n += len(got)
                _write_state(summarised=n)
        except cf.TimeoutError:
            for f in futs:
                f.cancel()
    _write_state(phase="done", finished=dt.datetime.now().isoformat(timespec="seconds"),
                 seconds=int(time.time() - started), files=len(files), summarised=n)


# ---------------------------------------------------------------- search
STOP = {"the", "a", "an", "of", "for", "in", "on", "to", "and", "my", "our", "me", "find", "open", "show", "get", "can",
        "you", "please", "pls", "where", "is", "it", "that", "this", "with", "from", "file", "files", "doc", "document",
        "sheet", "sheets", "spreadsheet", "excel", "form", "drive", "google", "i", "im", "looking", "want", "need",
        "which", "what", "about", "called", "named", "one", "some", "any", "do", "we", "have", "there", "up"}
KIND_WORDS = {"sheet": "sheet", "sheets": "sheet", "spreadsheet": "sheet", "excel": "sheet", "xlsx": "sheet",
              "datasheet": "sheet", "doc": "doc", "document": "doc", "pdf": "pdf", "slides": "slides", "deck": "slides",
              "folder": "folder", "photo": "image", "image": "image", "picture": "image"}


def _tokens(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text or ""))
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def _kind_family(kind):
    k = kind.lower()
    if "sheet" in k or "excel" in k or "csv" in k:
        return "sheet"
    if "docs" in k or "word" in k or "text" in k:
        return "doc"
    if "pdf" in k:
        return "pdf"
    if "slides" in k or "powerpoint" in k:
        return "slides"
    if "folder" in k:
        return "folder"
    if "image" in k:
        return "image"
    return "other"


def _match(q, words):
    """Best match of one query word against a list of words: 1.0 exact, ~0.9 prefix, ratio for close spellings."""
    best = 0.0
    if q.isdigit():  # years, plot numbers: exact only
        return 1.0 if q in words else 0.0
    for w in words:
        if w == q:
            return 1.0
        if w.isdigit():
            continue
        if len(q) >= 3 and (w.startswith(q) or q.startswith(w)) and min(len(w), len(q)) >= 3:
            best = max(best, 0.9)
        elif len(q) >= 4 and len(w) >= 4:
            r = difflib.SequenceMatcher(None, q, w).ratio()
            if r >= 0.75:
                best = max(best, r * 0.85)
    return best


def search(query, limit=5):
    """Rank indexed files for the user's words. Returns {"status": found|choose|none|no_index, "results": [...]}."""
    if not os.path.exists(DB):
        return {"status": "no_index", "results": []}
    con = connect(read_only=True)
    rows = con.execute("SELECT id, name, kind, path, coalesce(peek, ''), coalesce(summary, ''), modified FROM files").fetchall()
    con.close()
    if not rows:
        return {"status": "no_index", "results": []}
    from lib.formkit import parse_when
    when = parse_when(query)
    date_words = set(MONTHS3) | {m for m in ("january", "february", "march", "april", "june", "july", "august",
                                             "september", "october", "november", "december", "sept")} | \
        {"last", "this", "month", "year", "week", "quarter", "days", "since", "before", "after", "ago", "fy"}
    qt = [t for t in _tokens(query) if t not in STOP and t not in KIND_WORDS and len(t) > 1
          and not (when and t in date_words)]
    want = {KIND_WORDS[t] for t in _tokens(query) if t in KIND_WORDS}
    if not qt and not when:
        return {"status": "none", "results": [], "why": "no searchable words"}
    scored = []
    lo = dt.date.fromisoformat(when[0]) if when and when[0] else None
    hi = dt.date.fromisoformat(when[1]) if when and when[1] else None
    for fid, name, kind, path, pk, summ, modified in rows:
        nt, pt, ct = _tokens(name), _tokens(path), _tokens(pk + " " + summ)
        s, why = 0.0, []
        for q in qt:
            a, b, c = _match(q, nt), _match(q, pt), _match(q, ct)
            best = max(a * 1.0, b * 0.6, c * 0.7)
            s += best
            if best >= 0.5:
                why.append(f"'{q}' in {'name' if best == a else 'folder' if best == b * 0.6 else 'contents'}")
        s = s / len(qt) if qt else 0.5
        if when:
            inside = modified is not None and (lo is None or modified >= lo) and (hi is None or modified <= hi)
            s += 0.25 if inside else -0.2
            if inside:
                why.append(f"modified {modified.isoformat()}")
        if want:
            fam = _kind_family(kind)
            s += 0.08 if fam in want else (-0.3 if fam == "folder" else -0.05)
        if s > 0.15:
            scored.append((round(min(s, 1.0), 2), {"id": fid, "name": name, "kind": kind, "folder": path,
                                                   "about": (summ or pk)[:160], "why": ", ".join(why),
                                                   "modified": modified.isoformat() if modified else None}))
    scored.sort(key=lambda x: -x[0])
    top = [dict(r, score=s) for s, r in scored[:limit]]
    if not top or top[0]["score"] < 0.35:
        return {"status": "none", "results": top[:3]}
    clear = top[0]["score"] >= 0.6 and (len(top) == 1 or top[1]["score"] <= top[0]["score"] - 0.15)
    return {"status": "found" if clear else "choose", "results": top if not clear else top[:3]}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "build":
        build(float(os.environ.get("IDLI_INDEX_MINUTES") or 5), int(os.environ.get("IDLI_INDEX_TABS") or 5))
    elif cmd == "status":
        print(json.dumps(status(), indent=1))
    elif cmd == "find":
        print(json.dumps(search(" ".join(sys.argv[2:])), indent=1, ensure_ascii=False))
    else:
        sys.exit(__doc__)
