"""Rescore E3 hops and replay shown charts against real fixtures, offline.

Run with ../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python
harness/e3_rescore.py [results/e3/<run>[/<chat>.json]].
The optional input selects logs; output always goes to results/e3/rescore.json.
"""

import argparse
import contextlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[1]
COWORK = ROOT.parent / "2026-11-06-oss-desktop-independent/cowork"
ROUTES = {"teach_file", "chart_request"}
sys.dont_write_bytecode = True


def read_json(path):
    """A producer may not have finished writing this file yet."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def obj(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def successful(event):
    result = obj(event.get("result"))
    return (not event.get("error") and not result.get("error")
            and not result.get("isError") and result.get("ok") is not False
            and event.get("result") is not None)


def numbers(text):
    return [float(n.replace(",", "")) for n in re.findall(
        r"(?<![\w.])[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?",
        text or "")]


def matches(ref, got):
    return bool(ref) and all(any(abs(r - g) <= 0.6 for g in got) for r in ref)


def contained(base, name):
    """Only read artifacts inside the specified local directory."""
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("artifact path escapes its directory")
    return path


def plotted_values(skill_dir, chart_id, fixture):
    """Use Idli's exact cleaned tables, but inspect the figure in-process."""
    from lib import chartkit
    import matplotlib.pyplot as plt
    from matplotlib.container import BarContainer
    from matplotlib.patches import Rectangle

    chart_py = contained(skill_dir / "charts", chart_id + ".py")
    src = chart_py.read_text()
    if chartkit.check(src):
        raise ValueError("chart failed Idli code checks")
    skill = read_json(skill_dir / "skill.json")
    if not isinstance(skill, dict):
        raise ValueError("missing or incomplete skill")
    skill["_dir"] = str(skill_dir)
    try:
        tables = chartkit.tables(str(fixture), skill)
        chartkit.style(plt)
        namespace = {"__name__": "e3_chart", "__file__": str(chart_py)}
        exec(compile(src, str(chart_py), "exec"), namespace)
        fig = namespace["make"](tables, plt)
        values = []
        for ax in fig.axes:
            seen = set()
            for container in ax.containers:
                if isinstance(container, BarContainer):
                    horizontal = container.orientation == "horizontal"
                    for patch in container.patches:
                        seen.add(id(patch))
                        values.append(patch.get_width() if horizontal else patch.get_height())
            for patch in ax.patches:
                if id(patch) not in seen and isinstance(patch, Rectangle):
                    # For hand-built bars, follow the axis's declared orientation.
                    # Never count bar thickness as an additional answer value.
                    horizontal = (getattr(ax, "orientation", None) == "horizontal"
                                  or (ax.yaxis_inverted() and not ax.xaxis_inverted()))
                    values.append(patch.get_width() if horizontal else patch.get_height())
            for line in ax.lines:
                values.extend(line.get_ydata(orig=False))
        return [float(v) for v in values if math.isfinite(float(v))]
    finally:
        plt.close("all")


def score(path, log, scenario):
    events = [(turn.get("step"), event) for turn in log.get("turns", [])
              for event in turn.get("events", [])]
    tools = [(step, event) for step, event in events if event.get("type") == "tool"]
    control = [e.get("name") for step, e in tools if step == 2]
    routes = list(dict.fromkeys(e["name"] for step, e in tools
                               if step == 3 and e.get("name") in ROUTES))
    sends = [e for step, e in tools if step == 4 and e.get("name") == "teach_send"
             and obj(e.get("result")).get("done") is True]
    bounced = False
    returned = False
    shows = []
    for step, event in tools:
        if step == 4 and event in sends:
            bounced = True
        elif step in (4, 5) and successful(event):
            if event.get("name") in ("file_ask", "chart_show") and bounced:
                returned = True
            if event.get("name") == "chart_show":
                shows.append(event)

    check = scenario["steps"][5].get("check", {})
    ref = [float(v) for v in check.get("ref", {}).get("numbers", [])]
    results = [obj(e.get("result")) for e in sends]
    row = {
        "run": path.parent.name, "chat": path.stem,
        "control_ok": "file_ask" in control and not ROUTES.intersection(control),
        "wrong_bounce": int(bool(ROUTES.intersection(control))),
        "routed": bool(routes), "route": ",".join(routes) or None,
        "sent": bool(sends), "claude_done": bool(sends),
        "minutes": sum(float(r.get("secs") or 0) / 60 for r in results),
        "claude_cost": sum(float(r.get("claude_cost") or 0) for r in results),
        "cards": results[0].get("cards") if len(results) == 1 else
                 [r.get("cards") for r in results],
        "came_back": returned, "never_returned": bool(sends) and not returned,
        "answered_right": False, "answered_how": "none", "got": [], "ref": ref,
        "secs": log.get("secs"),
    }
    teach_dir = ROOT / "results/e3-logs" / row["run"] / row["chat"] / "teach"
    artifacts = []
    # Associate each displayed chart with the most recent preceding send request.
    chart_jobs = []
    for step, event in tools:
        if step == 4 and event.get("name") == "teach_send":
            rid = obj(event.get("args")).get("request_id")
            if isinstance(rid, str):
                skill_dir = contained(teach_dir, rid) / "skill"
                artifacts.append(skill_dir)
        if step in (4, 5) and event.get("name") == "chart_show" and successful(event):
            ids = obj(event.get("args")).get("charts", [])
            if isinstance(ids, str):
                ids = [ids]
            for chart_id in ids:
                if isinstance(chart_id, str):
                    skill_dir = next((s for s in reversed(artifacts)
                                      if contained(s / "charts", chart_id + ".py").is_file()), None)
                    chart_jobs.append((skill_dir, chart_id))
    produced_chart = (any(r.get("charts") for r in results)
                      or any(list((s / "charts").glob("*.py")) for s in artifacts))
    if produced_chart or chart_jobs:
        if chart_jobs:
            row["answered_how"] = "chart"
        fixture = contained(ROOT / "fixtures", scenario["ref_file"] + ".xlsx")
        for skill_dir, chart_id in chart_jobs:
            if skill_dir is None:
                row.setdefault("chart_errors", []).append({"chart": chart_id, "reason": "missing code"})
                continue
            try:
                # Chart code and imported helpers must not leak arbitrary output (or keys).
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    row["got"].extend(plotted_values(skill_dir, chart_id, fixture))
            except Exception as exc:
                row.setdefault("chart_errors", []).append(
                    {"chart": chart_id, "reason": type(exc).__name__})
        got = row["got"]
        if got and all(0 <= v <= 1 for v in got) and any(v > 1 for v in ref):
            row["got"] = [v * 100 for v in got]
            row["scaled_percent"] = True
        row["answered_right"] = matches(ref, row["got"])
    else:
        texts = []
        for step, event in events:
            if step not in (4, 5):
                continue
            if event.get("type") == "model" and isinstance(event.get("text"), str):
                texts.append(event["text"])
            if event.get("type") == "tool" and event.get("name") == "file_ask" and successful(event):
                answer = obj(event.get("result")).get("answer")
                if isinstance(answer, str):
                    texts.append(answer)
        row["got"] = numbers("\n".join(texts))
        row["answered_how"] = "text" if any(texts) else "none"
        row["answered_right"] = matches(ref, row["got"])
    if not ref and "chart_show" in check.get("tools_any", []):
        row["answered_right"] = bool(shows)
        if shows:
            row["answered_how"] = "chart"
    return row


def print_tables(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["run"]].append(row)
    for run, chats in sorted(groups.items()):
        print(f"\n{run}\n")
        print("| Chats | Control ok | Wrong bounces | Routed | Sent | Claude done | Came back | Answered right | Mean min/bounce | Mean $/bounce |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        keys = ("control_ok", "wrong_bounce", "routed", "sent", "claude_done", "came_back", "answered_right")
        counts = [sum(c[k] for c in chats) for k in keys]
        sent = counts[3]
        minutes = sum(c["minutes"] for c in chats) / sent if sent else 0
        cost = sum(c["claude_cost"] for c in chats) / sent if sent else 0
        print("| " + " | ".join(map(str, [len(chats), *counts, f"{minutes:.2f}", f"{cost:.4f}"])) + " |")
    print("\n| Run | Chat | Route | Answered right | How | Plotted/got | Ref |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        fmt = lambda values: ", ".join(f"{v:.4f}".rstrip("0").rstrip(".") for v in values)
        cells = [row["run"], row["chat"], row["route"] or "—",
                 str(row["answered_right"]), row["answered_how"], fmt(row["got"]), fmt(row["ref"])]
        print("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=ROOT / "results/e3")
    args = parser.parse_args()
    source = args.input.resolve()
    if not source.is_relative_to(ROOT):
        parser.error("input must be inside this eval folder")
    scenarios = read_json(ROOT / "scenarios/e3.json")
    by_id = {c["id"]: c for c in scenarios["conversations"]}
    paths = [source] if source.is_file() else sorted(source.glob("**/*.json"))
    rows = []
    sys.path.insert(0, str(COWORK))
    # Keep matplotlib's temporary cache inside this folder and remove it afterwards.
    with tempfile.TemporaryDirectory(prefix=".e3-rescore-", dir=ROOT) as cache:
        os.environ["MPLCONFIGDIR"] = cache
        os.environ["MPLBACKEND"] = "Agg"
        for path in paths:
            log = read_json(path)
            if not isinstance(log, dict) or not isinstance(log.get("turns"), list):
                continue
            scenario = by_id.get(log.get("conv", path.stem))
            if scenario is not None:
                rows.append(score(path, log, scenario))
    out = ROOT / "results/e3/rescore.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    print_tables(rows)


if __name__ == "__main__":
    main()
