"""Teach one file headless: Idli's own fake copy (filekit.make_mock) -> Claude Code with the teach-file skill (the
product's prompt) -> a skill. A scripted user (Haiku through `claude -p`) answers every card and chat question from
the file's documentation only (<stem>.doc.md); it never sees data, fake or real.

  sdkvenv/bin/python harness/teach_run.py <fixture.xlsx> <out_dir> [--model claude-sonnet-5-5] [--real-teach]

--real-teach skips the fake copy and gives Claude the real (synthetic) file as mock.xlsx (E2's upper bound).
Writes <out_dir>/skill.json (copied from the workspace), transcript.json, request.json.
"""
import argparse
import asyncio
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
COWORK = os.path.join(os.path.dirname(EVAL), "2026-11-06-oss-desktop-independent", "cowork")
SCRATCH = os.environ.get("PIPE_TMP") or tempfile.gettempdir()
QUESTION = "Check this file for mistakes so we can clean it, then I'll want to analyse it."
USER_MODEL = os.environ.get("PIPE_USER_MODEL", "claude-haiku-5-5")
MAX_ROUNDS = 30


def workspace():
    """A private copy of the Teach folder (Claude may add rules to lib/filekit.py)."""
    ws = tempfile.mkdtemp(prefix="pipe-teach-", dir=SCRATCH)
    shutil.copytree(COWORK, os.path.join(ws, "cowork"), symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "teach", ".venv"))
    os.symlink(os.path.realpath(os.path.join(COWORK, ".venv")), os.path.join(ws, "cowork", ".venv"))
    return os.path.join(ws, "cowork")


def make_request(ws, fixture, real_teach):
    py = os.path.join(ws, ".venv", "bin", "python")
    code = ("import sys, json; sys.path.insert(0, '.'); from lib import filekit as fk; "
            "req, mock, _ = fk.make_mock(sys.argv[1], sys.argv[2]); print(json.dumps({'id': req['id'], 'mock': mock}))")
    r = subprocess.run([py, "-c", code, fixture, QUESTION], cwd=ws, capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit("make_mock failed: " + r.stderr[-1500:])
    out = json.loads(r.stdout.strip().splitlines()[-1])
    if real_teach:  # E2 upper bound: Claude sees the real (synthetic) values
        shutil.copy(fixture, out["mock"])
    return out["id"], out["mock"]


def load_existing_request(ws, request_dir):
    """Reuse an inbox request already created by Idli."""
    rdir = os.path.abspath(request_dir)
    req = json.load(open(os.path.join(rdir, "request.json")))
    rid = req["id"]
    dest = os.path.join(ws, "teach", "inbox", rid)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(rdir, dest)
    return rid, os.path.join(dest, "mock.xlsx"), req


def restore_existing_skill(ws, request_dir, req):
    skill = req.get("existing_skill")
    if not skill:
        return
    src_home = os.path.dirname(os.path.dirname(os.path.abspath(request_dir)))
    src = os.path.join(src_home, "file-skills", skill)
    dst = os.path.join(ws, "file-skills", skill)
    if os.path.isdir(src):
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)


def scripted_user(doc, history, ask):
    """One reply from the person, as JSON. `ask` is a card (dict) or Claude's chat text (str)."""
    if isinstance(ask, dict):
        what = ("Claude shows you a card. Answer every question on it. For a multi-select question you may pick "
                "several labels (comma-separated). If none fits, write your own short answer instead of a label.\n"
                "Card: " + json.dumps(ask, ensure_ascii=False) +
                '\nReply with JSON only: {"<question text>": "<label(s) or your own words>", ...}')
    else:
        what = ("Claude wrote this to you in the chat:\n---\n" + ask[-4000:] + "\n---\n"
                'Reply with JSON only: {"reply": "<what you type back, 1-3 sentences>"}')
    prompt = (
        "You are the team lead who owns a spreadsheet. Claude (an assistant) is setting up how a private tool reads, "
        "checks and analyses it. You only know what's in your notes below; you have not seen any values Claude "
        "mentions (they're fake). Be practical and brief, like a busy field coordinator. Accept sensible "
        "suggestions; when asked about checks or rules, say the rules from your notes that apply, in your own words; "
        "say a team convention is fine when your notes say so. If asked to choose, choose. When Claude says it's "
        "done and asks whether to go back, say yes.\n\nYour notes about the file:\n" + doc +
        "\n\nRecent conversation (newest last):\n" + "\n".join(history[-8:]) + "\n\n" + what)
    r = subprocess.run(["claude", "-p", "--model", USER_MODEL, "--setting-sources", "", "--max-turns", "1",
                        "--output-format", "json", prompt],
                       capture_output=True, text=True, timeout=180, cwd=SCRATCH)
    try:
        res = json.loads(r.stdout)
        text, cost = res.get("result", ""), res.get("total_cost_usd") or 0
    except ValueError:
        text, cost = r.stdout, 0
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {"reply": "You decide."}, cost
    except ValueError:
        return {"reply": "You decide."}, cost


async def teach(fixture, out_dir, model, real_teach, request_dir=None):
    from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
                                  ResultMessage, TextBlock, ToolUseBlock)
    ws = workspace()
    src_request_dir = os.path.abspath(request_dir) if request_dir else None
    if request_dir:
        rid, mock, req = load_existing_request(ws, request_dir)
        rdir = os.path.join(ws, "teach", "inbox", rid)
        stem = req["id"].split("-", 1)[0]
        restore_existing_skill(ws, request_dir, req)
        doc = open(os.path.join(EVAL, "fixtures", stem + ".doc.md")).read()
    else:
        stem = os.path.splitext(os.path.basename(fixture))[0]
        doc = open(os.path.splitext(fixture)[0] + ".doc.md").read()
        rid, mock = make_request(ws, os.path.abspath(fixture), real_teach)
        rdir = os.path.join(ws, "teach", "inbox", rid)
        req = json.load(open(os.path.join(rdir, "request.json")))
    prompt = (f"Idli asked to be taught a file. The request is in teach/inbox/{rid}/ (mock.xlsx with fake data "
              f"and a hidden _idli_teach sheet, plus request.json). Question: \"{req['question']}\". Use the teach-file skill.")
    if req.get("chart") is not None:
        prompt = (f"Idli asks for {'suggested analyses and charts' if not req['chart'] else 'a chart'} for "
                  f"{req['title']} (taught as file-skills/{req['existing_skill']}). The request is in "
                  f"teach/inbox/{rid}/ (mock.xlsx with fake data, request.json). "
                  + (f"The chart they asked for: \"{req['chart']}\". " if req["chart"] else
                     "They want you to suggest what to look at. ")
                  + "Use the teach-file skill, section 'Chart requests'.")
    log = {"fixture": stem, "model": model, "real_teach": real_teach, "request": rid, "events": [], "user_cost": 0.0,
           "workspace": ws}
    history = []

    async def can_use_tool(name, inp, ctx):
        if name != "AskUserQuestion":
            return PermissionResultAllow(updated_input=inp)
        qs = inp.get("questions") or []
        if any("back to idli" in str(o.get("label", "")).lower() for q in qs for o in q.get("options") or []):
            ans = {q.get("question", ""): next((o["label"] for o in q["options"] if "back" in o["label"].lower()),
                                               q["options"][0]["label"]) for q in qs}
            open(os.path.join(rdir, "go_back"), "w").close()
        else:
            got, cost = await asyncio.to_thread(scripted_user, doc, history, inp)
            log["user_cost"] += cost
            ans = {q.get("question", ""): str(got.get(q.get("question", ""), next(iter(got.values()), "You decide.")))
                   for q in qs}
        history.append("CARD: " + json.dumps([q.get("question") for q in qs], ensure_ascii=False) + " -> " +
                       json.dumps(ans, ensure_ascii=False))
        log["events"].append({"type": "card", "t": round(time.time() - t0), "card": inp, "answers": ans})
        return PermissionResultAllow(updated_input={**inp, "answers": ans})

    env = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "DISABLE_AUTOUPDATER": "1", "API_TIMEOUT_MS": "300000"}
    opts = ClaudeAgentOptions(cwd=ws, model=model, permission_mode="default", can_use_tool=can_use_tool,
                              setting_sources=["project"], env=env, max_turns=120,
                              disallowed_tools=["WebSearch", "WebFetch", "Agent", "Task"])
    t0 = time.time()
    done_path = os.path.join(rdir, "done.json")
    msg, rounds, cost = prompt, 0, 0.0
    async with ClaudeSDKClient(options=opts) as client:
        while rounds < MAX_ROUNDS:
            rounds += 1
            await client.query(msg)
            last_text = ""
            async for m in client.receive_response():
                if isinstance(m, AssistantMessage):
                    texts = [b.text for b in m.content if isinstance(b, TextBlock)]
                    for u in (b for b in m.content if isinstance(b, ToolUseBlock)):
                        log["events"].append({"type": "tool", "t": round(time.time() - t0), "name": u.name,
                                              "args": json.dumps(u.input, ensure_ascii=False)[:400]})
                    if texts:
                        last_text = "\n".join(texts).strip()
                        log["events"].append({"type": "text", "t": round(time.time() - t0), "text": last_text[:3000]})
                elif isinstance(m, ResultMessage):
                    cost += getattr(m, "total_cost_usd", 0) or 0
            history.append("CLAUDE: " + last_text[:1500])
            if os.path.exists(done_path):
                break
            got, ucost = await asyncio.to_thread(scripted_user, doc, history, last_text or "(no text)")
            log["user_cost"] += ucost
            msg = str(got.get("reply") or next(iter(got.values()), "You decide."))
            history.append("ME: " + msg)
            log["events"].append({"type": "user", "t": round(time.time() - t0), "text": msg})
    log.update({"secs": round(time.time() - t0), "rounds": rounds, "claude_cost": round(cost, 3),
                "done": os.path.exists(done_path), "cards": sum(e["type"] == "card" for e in log["events"])})
    os.makedirs(out_dir, exist_ok=True)
    done = json.load(open(done_path)) if os.path.exists(done_path) else {}
    sid = done.get("skill")
    cands = [os.path.join(ws, "file-skills", sid)] if sid else sorted(
        glob.glob(os.path.join(ws, "file-skills", "*")), key=os.path.getmtime)[-1:]
    if cands and os.path.exists(os.path.join(cands[0], "skill.json")):
        shutil.copytree(cands[0], os.path.join(out_dir, "skill"), dirs_exist_ok=True)
    log["skill"] = os.path.basename(cands[0]) if cands else None
    log["filekit_changed"] = subprocess.run(["diff", "-q", os.path.join(COWORK, "lib", "filekit.py"),
                                             os.path.join(ws, "lib", "filekit.py")], capture_output=True).returncode != 0
    if log["filekit_changed"]:
        shutil.copy(os.path.join(ws, "lib", "filekit.py"), os.path.join(out_dir, "filekit.py"))
    shutil.copy(os.path.join(rdir, "request.json"), os.path.join(out_dir, "request.json"))
    shutil.copy(mock, os.path.join(out_dir, "mock.xlsx"))
    with open(os.path.join(out_dir, "transcript.json"), "w") as f:
        json.dump(log, f, indent=1, default=str)
    if src_request_dir:
        for name in ("done.json", "teach_agent.json", "go_back"):
            sp = os.path.join(rdir, name)
            if os.path.exists(sp):
                shutil.copy2(sp, os.path.join(src_request_dir, name))
    print(json.dumps({k: log[k] for k in ("fixture", "secs", "rounds", "cards", "claude_cost", "user_cost", "done",
                                          "skill", "filekit_changed")}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture")
    ap.add_argument("out_dir")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--real-teach", action="store_true")
    ap.add_argument("--request-dir")
    a = ap.parse_args()
    asyncio.run(teach(a.fixture, a.out_dir, a.model, a.real_teach, a.request_dir))
