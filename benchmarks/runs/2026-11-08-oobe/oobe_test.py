#!/usr/bin/env python3
"""Play a new user through Start here (the first-run chat) on the laptop's Paseo, and time it.

Each case: put a variant of Start here's instructions in place, open a fresh Start here chat ("hello", as the
bootstrap does), reply the way a person would (typed text, or the answer on a question card), and watch:
  greet_s     hello -> greeting (or the question card) shown
  act_s       reply -> drive_index called (how long the model spent deciding)
  lines       progress lines written in the chat while indexing
  finish      the "Done ... Next: go to Idli" message reached the chat
Runs from the DGX through the tunnel (desktop/paseo-remote.sh) and a laptop terminal. Google sign-in is kept.

  python3 oobe_test.py --provider t4gc-cowork --thinking high --variant text --reply yes [--full]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COWORK = os.path.join(HERE, "..", "2026-11-06-oss-desktop-independent", "cowork")
P = os.path.join(COWORK, "desktop", "paseo-remote.sh")
LAPTOP_COWORK = "/home/desinotorious/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork"
START_WS = os.environ.get("START_WS", "wks_1a227cf4ee442370")
TEACH_WS = "wks_7396ac6f2a5e1fd7"
PROGRESS = re.compile(r"^(Opening your Drive|Listing your Drive|Reading inside|Summarising with)", re.M)


def paseo(*args, timeout=90):
    r = subprocess.run([P, *args], capture_output=True, text=True, timeout=timeout)
    return r.stdout


class Laptop:
    """A Paseo terminal on the laptop, for file changes (start-here instructions, the dry-run switch)."""

    def __init__(self):
        out = paseo("terminal", "create", "--workspace", TEACH_WS, "--name", "oobe-test")
        self.t = re.search(r"^([0-9a-f]{8})", out, re.M).group(1)
        time.sleep(2)

    def run(self, cmd, wait=20):
        mark = f"DONE{int(time.time() * 1000) % 100000}"
        paseo("terminal", "send-keys", self.t, f"clear; cd {LAPTOP_COWORK}; {cmd}; echo {mark}", "Enter")
        for _ in range(wait * 2):
            time.sleep(0.5)
            out = paseo("terminal", "capture", self.t, "-S")
            if re.search(rf"^{mark}$", out, re.M):
                return out
        return ""

    def close(self):
        paseo("terminal", "kill", self.t)


def agents():
    try:
        return json.loads(paseo("ls", "--json"))
    except ValueError:
        return []


def log(agent):
    return paseo("logs", agent, timeout=60)


def visible(text):
    """The chat as the person sees it: assistant text and tool calls, without thoughts."""
    out, skip = [], False
    for line in text.splitlines():
        if line.startswith("[Thought]"):
            skip = True
            continue
        if line.startswith("[") and not line.startswith("[Thought]"):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


def pending(agent):
    try:
        rows = json.loads(paseo("permit", "ls", "--json"))
    except ValueError:
        return []
    return [r for r in rows if agent.startswith(str(r.get("agentId", ""))[:7]) or str(r.get("agentId", "")).startswith(agent)]


def status(agent):
    a = next((a for a in agents() if a["id"].startswith(agent) or a.get("shortId") == agent), None)
    return a and a["status"]


class Screen:
    """What the person sees: the Start here chat as the app renders it (thoughts and tool details hidden)."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        b = self.pw.chromium.connect_over_cdp("http://127.0.0.1:49333")
        self.pg = next(pg for c in b.contexts for pg in c.pages if pg.url.startswith("paseo://app"))

    def show(self, ws, tab="Start here"):
        base = self.pg.url.split("/workspace/")[0]
        self.pg.evaluate(f"location.href = {json.dumps(base + '/workspace/' + ws)}")
        self.pg.wait_for_timeout(2500)
        self.pg.evaluate("""(t) => { for (const e of document.querySelectorAll('*')) { const r = e.getBoundingClientRect();
            if (e.childElementCount === 0 && (e.innerText || '').trim() === t && r.top > 40 && r.top < 66) { e.click(); return true; } } return false; }""", tab)
        self.pg.wait_for_timeout(1000)

    def text(self):
        try:
            return self.pg.evaluate("""() => { const m = [...document.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect();
                return r.left >= 320 && r.top > 70 && r.height > 300 && e.scrollHeight > 0 && e.childElementCount > 0; });
                m.sort((a, b) => b.innerText.length - a.innerText.length); return m.length ? m[0].innerText : ''; }""")
        except Exception:
            return ""

    def close(self):
        self.pw.stop()


def wait(cond, timeout, step=1.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = cond()
        if r:
            return r, time.time() - t0
        time.sleep(step)
    return None, time.time() - t0


def case(a, lap):
    variant = {"text": "idli/START-HERE.md", "card": "idli/START-HERE-card.md"}[a.variant]
    flag = "~/idli-insights/config/drive-index.dryrun"
    lap.run(f"cp {variant} ~/idli-insights/start-here/CLAUDE.md; "
            + (f"rm -f {flag}; pkill -f 'lib/driveindex.py build'; rm -f ~/idli-insights/config/drive-index.duckdb ~/idli-insights/config/drive-index.json" if a.full
               else f"touch {flag}; cd ~/idli-insights/config && for f in drive-index.json drive-index.duckdb; do [ -f $f ] && mv $f $f.hold; done; cd - >/dev/null"))
    for ag in agents():
        if ag["name"] == "Start here":
            paseo("archive", ag["id"])
    t0 = time.time()
    out = paseo("run", "--provider", a.provider, "--workspace", START_WS, "--mode", "bypassPermissions",
                "--thinking", a.thinking, "--title", "Start here", "--no-wait", "--json", "hello")
    try:
        agent = json.loads(out)["agentId"]
    except (ValueError, KeyError):
        agent = next(ag["id"] for ag in agents() if ag["name"] == "Start here")
    res = {"provider": a.provider, "thinking": a.thinking, "variant": a.variant, "reply": a.reply, "full": a.full}
    scr = Screen()
    time.sleep(2)
    scr.show(START_WS)
    seen = {}

    def note(txt):
        for key, pat in (("greeting", r"Hi, I.m Idli"), ("card", r"index your Drive now\?"), ("progress", PROGRESS.pattern),
                         ("finish", r"Next: go to Idli")):
            if key not in seen and re.search(pat, txt, re.M):
                seen[key] = round(time.time() - t0, 1)
        return txt

    def greeted():
        txt = note(scr.text())
        if a.variant == "card" and pending(agent):
            return "card"
        if "greeting" in seen and status(agent) == "idle":
            return "text"
        return None
    shown, el = wait(greeted, 180, 2)
    res["greet_s"] = round(time.time() - t0, 1)
    res["greeting"] = shown
    # reply
    t1 = time.time()
    if a.reply.startswith("card:"):
        req = pending(agent)
        if not req:
            res["error"] = "no question card"
            return res, agent
        answer = a.reply.split(":", 1)[1]
        paseo("permit", "allow", agent, str(req[0].get("id") or req[0].get("requestId")), "--input",
              json.dumps({"answers": {"Drive": answer}}))
    else:
        if pending(agent):  # a card is showing but the person types instead
            req = pending(agent)
            paseo("permit", "deny", agent, str(req[0].get("id") or req[0].get("requestId")))
            time.sleep(2)
        paseo("send", "--no-wait", agent, a.reply)
    acted, _ = wait(lambda: (note(scr.text()) and False) or "mcp__cowork__drive_index]" in log(agent) or None, 240, 1.5)
    res["act_s"] = round(time.time() - t1, 1) if acted else None
    # progress and finish, as seen on screen
    limit = 480 if a.full else 90
    lines = set()
    def finished():
        txt = note(scr.text())
        lines.update(m.group(0) for m in re.finditer(r"^(?:Opening|Listing|Reading|Summarising)[^\n]*$", txt, re.M))
        return "finish" in seen and status(agent) == "idle" or None
    wait(finished, limit, 2)
    res["progress_lines_seen"] = len(lines)
    res["seen_at_s"] = seen
    res["finish"] = "finish" in seen
    res["total_s"] = round(time.time() - t1, 1)
    res["screen_tail"] = scr.text().strip().splitlines()[-5:]
    scr.close()
    return res, agent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="t4gc-cowork")
    ap.add_argument("--thinking", default="high")
    ap.add_argument("--variant", default="text", choices=["text", "card"])
    ap.add_argument("--reply", default="yes", help='typed reply, or card:<option label>')
    ap.add_argument("--full", action="store_true", help="real index build (else the dry-run switch)")
    a = ap.parse_args()
    lap = Laptop()
    try:
        res, agent = case(a, lap)
    finally:
        lap.run("rm -f ~/idli-insights/config/drive-index.dryrun; cd ~/idli-insights/config && for f in drive-index.json drive-index.duckdb; do [ -f $f.hold ] && mv -f $f.hold $f; done; cd - >/dev/null")
        lap.close()
    print(json.dumps(res, ensure_ascii=False))
    with open(os.path.join(HERE, "results.jsonl"), "a") as f:
        f.write(json.dumps(dict(res, at=time.strftime("%H:%M:%S")), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
