"""Tests for lib/driveindex.py against a simulated Drive (no browser, no Google account).

The fake Drive is deliberately awkward: folders nested 8 deep, a 260-file folder that loads 50 rows per
scroll, a shortcut that loops back to an ancestor, a shared folder that also appears in My Drive, files with
the same name in different folders, and Sheets/Docs whose contents are peeked.

  .venv/bin/python -m lib.test_driveindex
"""
import json
import os
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
TMP = tempfile.mkdtemp()
os.environ["IDLI_DRIVE_INDEX"] = os.path.join(TMP, "drive-index.duckdb")
os.environ["IDLI_INDEX_SETTLE"] = "0"
os.environ["IDLI_INDEX_SCROLL_WAIT"] = "0"
os.environ["MUSE_URL"] = "http://127.0.0.1:9"  # summaries fail fast: the index must still work without them

# ---------------------------------------------------------------- the fake Drive
TREE = {}  # folder id -> list of (id, label)
PEEKS = {}  # file id -> peek text (sheets: gviz rows, docs: paragraphs)


def fid(n):
    return f"id{n:0>24}"


counter = [0]


def new(label, folder, peek=None):
    counter[0] += 1
    i = fid(counter[0])
    TREE.setdefault(folder, []).append((i, label))
    if peek is not None:
        PEEKS[i] = peek
    return i


ROOT, SHARED = "root:my-drive", "root:shared"
proj = new("Projects Folder", ROOT)
new("Budget 2026 Google Sheets", ROOT, [["Head", "Amount"], ["Salaries", "120000"]])
new("Untitled document Google Docs", ROOT, ["random notes"])
new("Untitled document Google Docs", proj, ["more random notes"])  # same name, other folder
deep = proj
for lvl in range(1, 9):  # Projects / L1 / L2 / ... / L8
    deep = new(f"Level {lvl} Folder", deep)
    if lvl == 5:
        TARGET = new("BKM cestrum trial datasheet.xlsx Microsoft Excel", deep)
        new("Cestrum field notes Google Docs", deep, ["Observations on Cestrum nocturnum growth, plot B"])
    if lvl == 3:
        new("Shortcut to Projects Folder", deep)  # loop back up: must not hang
        TREE[fid(counter[0])] = TREE[proj]  # opening the shortcut shows Projects again
DEEPEST = new("Deepest secret plan Google Docs", deep, ["level eight"])
big = new("Photos 2025 Folder", ROOT)
for k in range(260):
    new(f"IMG_{k:04d}.jpg Image", big)
LAST_IN_BIG = fid(counter[0])
sh = new("[Shared] Bikapathymund experiment Shared folder", SHARED)
new("Bikapathymund plot register Google Sheets", sh,
    [["Plot", "Species", "Height cm", "Date"], ["P1", "Cestrum", "34", "01/09/2026"]])
TREE[ROOT].append((sh, "[Shared] Bikapathymund experiment Shared folder"))  # also added to My Drive
new("Volunteer register Google Sheets", ROOT, [["Volunteer name", "District", "Stipend"], ["Asha", "Pune", "300"]])
new("Broken sheet Google Sheets", ROOT, RuntimeError("boom"))  # peeking it fails

URLS = {}  # current url per tab
SCROLLS = {}  # how far each tab has "scrolled"
nav_log = []


def folder_of(url):
    if url.endswith("my-drive"):
        return ROOT
    if url.endswith("shared-with-me"):
        return SHARED
    return url.split("folders/")[1].split("?")[0] if "folders/" in url else None


def fake_paseo(tool, **a):
    if tool == "browser_new_tab":
        t = f"tab{len(URLS)}"
        URLS[t] = a.get("url")
        return f"browserId={t}"
    if tool == "browser_navigate":
        URLS[a["browserId"]] = a["url"]
        SCROLLS[a["browserId"]] = 1
        nav_log.append(a["url"])
        return "ok"
    if tool == "browser_close_tab":
        URLS.pop(a["browserId"], None)
        return "ok"
    raise AssertionError(tool)


def fake_evaluate(tab, js):
    f = folder_of(URLS[tab])
    rows = TREE.get(f, [])
    shown = rows[: 50 * SCROLLS[tab]]  # lazy list: 50 more rows each time it is scrolled
    SCROLLS[tab] += 1
    return [{"id": i, "label": label} for i, label in shown]


browser = types.ModuleType("lib.browser")
browser.paseo, browser.evaluate = fake_paseo, fake_evaluate
browser.snapshot = lambda tab, ready=None, tries=8: URLS[tab]
browser.tabs = lambda: []
sys.modules["lib.browser"] = browser

g = types.ModuleType("sites.google.tools")
g.drive_url = lambda path="": "https://drive.google.com/drive/" + path
g.sheets_url = lambda sid, path: f"sheet:{sid}"
def parse_gviz_table(snap):
    p = PEEKS[snap.split(":", 1)[1]]
    if isinstance(p, Exception):
        raise p
    return p
g.parse_gviz_table = parse_gviz_table
g.doc_text = lambda tab, doc_id: ("t", PEEKS[doc_id])
import sites  # noqa: E402
sys.modules["sites.google.tools"] = g
sites.google = types.ModuleType("sites.google")
sites.google.tools = g
sys.modules["sites.google"] = sites.google

from lib import driveindex as di  # noqa: E402

fails = 0


def ok(cond, what):
    global fails
    print(("ok   " if cond else "FAIL ") + what)
    fails += 0 if cond else 1


t0 = time.time()
di.build(minutes=2, workers=5)
took = time.time() - t0
st = di.status()
con = di.connect(read_only=True)
rows = {r[0]: r for r in con.execute("SELECT id, name, kind, path, where_, peek FROM files").fetchall()}
con.close()
ok(st["phase"] == "done", f"build finishes ({took:.1f}s, phase {st['phase']})")
ok(DEEPEST in rows, "finds a file 9 folders down")
ok(rows[DEEPEST][3].count(" / ") == 9, f"keeps the folder path: {rows[DEEPEST][3][:70]}...")
ok(LAST_IN_BIG in rows, "reads every row of a 260-file folder that loads 50 at a time")
ok(nav_log.count(nav_log[0]) == 1 and len(nav_log) == len(set(nav_log)), "opens each folder once (shortcut loop, shared folder in two places)")
ok(rows[TARGET][2] == "Microsoft Excel" and rows[TARGET][1] == "BKM cestrum trial datasheet.xlsx", "name and kind from Drive's label")
sheet = next(r for r in rows.values() if r[1] == "Bikapathymund plot register")
ok("Species" in (sheet[5] or ""), "peeks inside a Google Sheet (first rows)")
ok(next(r for r in rows.values() if r[1] == "Broken sheet")[5].startswith("(not read"), "an unreadable file doesn't stop the index")
ok(st.get("summarised") == 0, "no Muse: summaries skipped, index still usable")
ok(not URLS, "closes its own tabs")

for words, want, status in [
        ("the bikapathymund experiment datasheet", "Bikapathymund plot register", None),
        ("bikapathy mund plot", "Bikapathymund plot register", None),
        ("bikapatymund register", "Bikapathymund plot register", None),
        ("BKM cestrum datasheet", "BKM cestrum trial datasheet.xlsx", None),
        ("volunteer stipend sheet", "Volunteer register", "found"),
        ("cestrum", None, "choose"),
        ("untitled document", None, "choose"),
        ("quarterly tax filing for 2019", None, "none"),
]:
    r = di.search(words)
    names = [x["name"] for x in r["results"]]
    good = (want is None or (names and names[0] == want)) and (status is None or r["status"] == status)
    ok(good, f"search {words!r}: {r['status']} {names[:3]}")
print("ALL PASSED" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
