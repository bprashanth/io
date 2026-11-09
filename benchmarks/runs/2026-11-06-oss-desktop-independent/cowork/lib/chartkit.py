"""Charts for a taught file: written by Claude on fake data, run by Idli on the real data.

A chart is file-skills/<skill>/charts/<id>.py:

    TITLE = "Species found in each plot"
    QUESTION = "what grows in each plot"          # what it answers, in the person's words
    def make(tables, plt):
        df = tables["Raw 10x10m Data"]           # the form's cleaned table for that tab (slug columns)
        fig, ax = plt.subplots(figsize=(9, 5))
        ...
        return fig

`tables` holds exactly what the form reads: one DataFrame per taught tab, after the skill's clean-ups, with
skipped layout rows left out and lookups joined in. The code may import only pandas, numpy, matplotlib and a few
standard modules (checked before it runs) and gets no file names: it can't read anything but `tables`.

Quick charts (no Claude): `bar_svg()` draws a form answer (one or two breakdowns, one measure).

  .venv/bin/python -m lib.chartkit try file-skills/<skill> <chart-id>    # Claude: render on the skill's mock.xlsx
  .venv/bin/python -m lib.chartkit check file-skills/<skill>/charts/<id>.py
"""
import ast
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = {"pandas", "numpy", "matplotlib", "math", "textwrap", "collections", "re", "datetime", "itertools",
           "statistics", "functools"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "globals", "locals", "vars", "getattr",
                "setattr", "delattr", "breakpoint", "memoryview"}
PALETTE = ["#2E6F95", "#E07A1F", "#4C9A2A", "#B23A48", "#7A5195", "#8C6D31", "#5F6B73", "#D4A017"]


def check(src):
    """Reasons the chart code can't run (empty list = fine)."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            bad += [f"import {m}" for m in mods if m.split(".")[0] not in ALLOWED]
        elif isinstance(n, ast.Name) and n.id in BANNED_NAMES:
            bad.append(f"uses {n.id}")
        elif isinstance(n, ast.Attribute) and n.attr.startswith("__"):
            bad.append(f"uses {n.attr}")
        elif isinstance(n, ast.Attribute) and n.attr in ("to_csv", "to_excel", "to_pickle", "to_json", "to_parquet",
                                                         "read_csv", "read_excel", "read_json", "read_parquet",
                                                         "read_pickle", "savefig", "read_sql", "to_sql", "to_html"):
            bad.append(f"uses .{n.attr} (charts get their data only from `tables`)")
    names = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "make" not in funcs:
        bad.append("no make(tables, plt) function")
    if "TITLE" not in names:
        bad.append("no TITLE")
    return bad


def info(chart_py):
    """{"id", "title", "question"} without running the code."""
    src = open(chart_py).read()
    out = {"id": os.path.splitext(os.path.basename(chart_py))[0], "title": "", "question": ""}
    try:
        for n in ast.parse(src).body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id in ("TITLE", "QUESTION"):
                        out[t.id.lower()] = str(n.value.value)
    except SyntaxError:
        pass
    return out


def charts_of(skill):
    d = os.path.join(skill["_dir"], "charts")
    if not os.path.isdir(d):
        return []
    return [info(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith(".py")]


def tables(path, skill):
    """{tab: DataFrame} exactly as the form reads the file."""
    import duckdb

    from lib import filekit as fk
    from lib import formkit as fm
    con = duckdb.connect()
    built = fm.build(con, path, skill, fk.slug(skill["id"]))
    return {tab: con.execute(f'SELECT * EXCLUDE ("_row") FROM "{b["table"]}"').fetchdf() if "_row" in
            [r[0] for r in con.execute(f'DESCRIBE "{b["table"]}"').fetchall()] else
            con.execute(f'SELECT * FROM "{b["table"]}"').fetchdf() for tab, b in built.items()}


def render(skill_dir, chart_id, data_path, out_svg, timeout=90):
    """Run one chart on a file (real or mock) in a separate process; returns {"ok", "svg"} or {"ok": False, "error"}."""
    chart_py = os.path.join(skill_dir, "charts", chart_id + ".py")
    if not os.path.exists(chart_py):
        return {"ok": False, "error": f"no chart '{chart_id}'"}
    bad = check(open(chart_py).read())
    if bad:
        return {"ok": False, "error": "chart code not allowed: " + "; ".join(bad)}
    os.makedirs(os.path.dirname(out_svg) or ".", exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PASEO_", "OPENROUTER", "ANTHROPIC"))}
    env["MPLBACKEND"] = "Agg"
    env["MPLCONFIGDIR"] = os.path.join(os.path.dirname(out_svg) or ".", ".mpl")
    cmd = [sys.executable, "-I", "-c", RUNNER, HERE, skill_dir, chart_py, data_path, out_svg]
    r = subprocess.run(wall(cmd, reads=[HERE, skill_dir, data_path], writes=[os.path.dirname(out_svg)]),
                       capture_output=True, text=True, timeout=timeout, env=env, cwd=HERE)
    if r.returncode or not os.path.exists(out_svg):
        return {"ok": False, "error": (r.stderr or r.stdout).strip()[-600:]}
    return {"ok": True, "svg": out_svg}


def wall(cmd, reads=(), writes=()):
    """Run chart code inside a bubblewrap wall (as io's Codex sandbox did): no network, the whole filesystem
    read-only, every home folder hidden except the code, the skill and the one data file, and only the output folder
    writable. Without bwrap (macOS, Windows) the code still runs, after the import/name check above."""
    import shutil
    bw = shutil.which("bwrap")
    if not bw or os.environ.get("IDLI_NO_WALL"):
        return cmd
    py = os.path.realpath(sys.executable)
    keep = [os.path.realpath(p) for p in (*reads, sys.prefix, sys.base_prefix, os.path.dirname(os.path.dirname(py)))]
    args = [bw, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--unshare-all",
            "--die-with-parent", "--new-session"]
    for home in ("/home", "/root", "/Users"):
        if os.path.isdir(home):
            args += ["--tmpfs", home]
    for p in keep:
        if os.path.exists(p):
            args += ["--ro-bind", p, p]
    for p in writes:
        os.makedirs(p, exist_ok=True)
        args += ["--bind", os.path.realpath(p), os.path.realpath(p)]
    return args + ["--"] + cmd


RUNNER = r"""
import json, os, sys
here, skill_dir, chart_py, data_path, out = sys.argv[1:6]
sys.path.insert(0, here)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import chartkit
from lib import filekit as fk
skill = json.load(open(os.path.join(skill_dir, "skill.json")))
skill["_dir"] = skill_dir
t = chartkit.tables(data_path, skill)
chartkit.style(plt)
ns = {}
exec(compile(open(chart_py).read(), chart_py, "exec"), ns)
fig = ns["make"](t, plt)
fig.savefig(out, format="svg", bbox_inches="tight")
"""


def style(plt):
    """One look for every chart: plain, readable, colour-blind-safe."""
    from cycler import cycler
    plt.rcParams.update({
        "figure.figsize": (9, 5), "figure.dpi": 100, "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#E5E5E5",
        "axes.axisbelow": True, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10, "font.family": "sans-serif",
        "legend.frameon": False, "axes.prop_cycle": cycler(color=PALETTE), "svg.fonttype": "path"})


# ---------------------------------------------------------------- quick charts from a form answer
def bar_svg(res, title, out_svg, top=15):
    """A form answer as a bar chart: one breakdown -> bars; two -> stacked bars (second breakdown as colours).
    res is formkit.run()'s result. Returns out_svg, or None if the answer has no breakdown or measure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    rows = res["rows"]
    if not rows:
        return None
    total = res.get("total") or {}
    cols = res["columns"]
    if total:  # the total row has exactly the measures; the rest are breakdowns (even numeric ones: transect 1-7)
        num = [c for c in cols if c in total]
    else:
        num = [c for c in cols if all(isinstance(r.get(c), (int, float)) or r.get(c) is None for r in rows)
               and any(isinstance(r.get(c), (int, float)) for r in rows)]
    groups = [c for c in cols if c not in num]
    if not groups or not num:
        return None
    m = num[0]
    df = pd.DataFrame(rows)
    df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0)
    style(plt)
    if len(groups) == 1:
        g = groups[0]
        d = df[[g, m]].copy()
        d[g] = d[g].fillna("(blank)").astype(str)
        d = d.groupby(g, as_index=False)[m].sum().sort_values(m, ascending=False)
        if len(d) > top:
            rest = d.iloc[top:][m].sum()
            d = pd.concat([d.iloc[:top], pd.DataFrame({g: [f"{len(d) - top} others"], m: [rest]})])
        d = d.iloc[::-1]
        fig, ax = plt.subplots(figsize=(9, max(2.6, 0.38 * len(d) + 1.2)))
        bars = ax.barh(d[g], d[m], color=PALETTE[0])
        ax.bar_label(bars, labels=[_num(v) for v in d[m]], padding=3, fontsize=9)
        ax.set_xlabel(m)
        ax.grid(axis="y", visible=False)
    else:  # two breakdowns: a grid (rows x columns), the value in each cell; works for counts, shares and averages
        import numpy as np
        g1, g2 = groups[0], groups[1]
        d = df[[g1, g2, m]].copy()
        d[[g1, g2]] = d[[g1, g2]].fillna("(blank)").astype(str)
        p = d.pivot_table(index=g1, columns=g2, values=m, aggfunc="sum")
        def order(ix):
            try:
                return sorted(ix, key=lambda x: float(x))
            except ValueError:
                return sorted(ix)
        p = p.loc[order(p.index)[:25], order(p.columns)[:20]]
        fig, ax = plt.subplots(figsize=(min(11, 2 + 0.8 * len(p.columns)), max(2.6, 0.5 * len(p) + 1.4)))
        vals = p.values.astype(float)
        im = ax.imshow(np.ma.masked_invalid(vals), cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(len(p.columns)), [str(c) for c in p.columns])
        ax.set_yticks(range(len(p.index)), [str(i) for i in p.index])
        ax.set_xlabel(g2)
        ax.set_ylabel(g1)
        ax.grid(False)
        hi = np.nanmax(vals) if np.isfinite(vals).any() else 0
        for (i, j), v in np.ndenumerate(vals):
            if np.isfinite(v):
                ax.text(j, i, _num(v), ha="center", va="center", fontsize=9,
                        color="white" if hi and v > 0.6 * hi else "#1d1d1b")
            else:
                ax.text(j, i, "–", ha="center", va="center", fontsize=9, color="#9a9a9a")
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label(m)
    ax.set_title(title)
    if total and m in total and total[m] is not None:
        fig.text(0.01, -0.02, f"All: {_num(total[m])}", fontsize=9, color="#5F6B73")
    os.makedirs(os.path.dirname(out_svg), exist_ok=True)
    fig.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.close(fig)
    return out_svg


def _num(v):
    if v is None:
        return ""
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return f"{int(v):,}"


def _main():
    if len(sys.argv) >= 3 and sys.argv[1] == "check":
        bad = check(open(sys.argv[2]).read())
        print("OK" if not bad else "NOT ALLOWED: " + "; ".join(bad))
        return
    if len(sys.argv) == 4 and sys.argv[1] == "try":
        skill_dir, cid = os.path.abspath(sys.argv[2]), sys.argv[3]
        mock = os.path.join(skill_dir, "mock.xlsx")
        out = os.path.join(skill_dir, "charts", f"{cid}.mock.svg")
        os.environ["IDLI_NO_WALL"] = "1"  # fake data, and Claude's own sandbox can't start another bubblewrap inside
        r = render(skill_dir, cid, mock, out)
        if r["ok"]:
            print(f"OK: rendered on the fake data -> {out}\nShow it in the chat as: ![{cid}]({out})")
        else:
            print("FAILED:", r["error"])
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    _main()
