"""Run one E3 conversation and bounce teach/chat requests through the headless teach-file workflow."""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
B9 = os.path.join(os.path.dirname(EVAL), "2026-11-10-idli-9b")
PY = "/tmp/claude-1000/b9/sdkvenv/bin/python"
FIXTURES = os.path.join(EVAL, "fixtures")
RESULTS = os.path.join(EVAL, "results")
LOGS = os.path.join(RESULTS, "e3-logs")
TEACH_RUN = os.path.join(HERE, "teach_run.py")

os.environ.setdefault("IDLI9B_VARIANTS", os.path.join(EVAL, "variants"))
os.environ.setdefault("IDLI9B_SCENARIOS", os.path.join(EVAL, "scenarios"))
os.environ.setdefault("IDLI9B_RESULTS", os.path.join(EVAL, "results"))
os.environ.setdefault("IDLI9B_FIXTURES", FIXTURES)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _copy_skill(home, stem, source="fake"):
    src = os.path.join(RESULTS, "e6", source, stem, "skill")
    if not os.path.isdir(src):
        return False
    dst = os.path.join(home, "file-skills", stem)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return True


def _replace_skill_dir(home, skill_name, source_dir):
    dst = os.path.join(home, "file-skills", skill_name)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(source_dir, dst)


def _run_teach(fixture, out_dir, request_dir=None):
    os.makedirs(out_dir, exist_ok=True)
    cmd = [PY, TEACH_RUN, fixture, out_dir]
    if request_dir:
        cmd += ["--request-dir", request_dir]
    import time
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1500)
    except subprocess.TimeoutExpired:
        # 2026-11-11: teach_run sometimes hangs after Claude has finished (done.json written). The product's watcher
        # acts on done.json/go_back, so do the same; without done.json it's a real failure.
        if request_dir and os.path.exists(os.path.join(request_dir, "done.json")):
            import glob
            done = json.load(open(os.path.join(request_dir, "done.json")))
            ws_skill = done.get("skill")
            rid = os.path.basename(request_dir.rstrip("/"))
            for inbox in glob.glob(f"/tmp/pipe-teach-*/cowork/teach/inbox/{rid}"):
                src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(inbox))), "file-skills", ws_skill or "")
                if ws_skill and os.path.isdir(src):
                    shutil.copytree(src, os.path.join(out_dir, "skill"), dirs_exist_ok=True)
            return {"done": True, "secs": round(time.time() - t0), "hung_after_done": True, "skill": ws_skill}
        raise
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-2000:])
    return json.load(open(os.path.join(out_dir, "transcript.json")))


def _parse_link(step_text):
    m = re.search(r"/d/([\w-]{20,})|[?&]id=([\w-]{20,})", step_text or "")
    return (m.group(1) or m.group(2)) if m else None


def _ensure_learned(mcp, home, stem, link):
    if not stem or not link:
        return
    fixture = os.path.join(FIXTURES, stem + ".xlsx")
    if not os.path.exists(fixture):
        return
    idli = sys.modules.get("idli")
    if not idli:
        return
    got, err = idli.call(mcp, "file_get", {"link": link, "open_after": False})
    if err or got.get("error") or not got.get("file"):
        return
    opened, _ = idli.call(mcp, "file_open", {"file": got["file"]})
    if opened.get("known"):
        return
    out_dir = os.path.join(LOGS, "preteach", stem)
    t = _run_teach(fixture, out_dir)
    skill = t.get("skill")
    skill_dir = os.path.join(out_dir, "skill")
    if skill and os.path.isdir(skill_dir):
        _replace_skill_dir(home, skill, skill_dir)


def _wrap_teach_send(mcp, home, stem, model_id, conv_id):
    fn, desc, props, req = mcp.TOOLS["teach_send"]

    def teach_send(request_id, **kwargs):
        rdir = os.path.join(os.environ["IDLI_TEACH_DIR"], request_id)
        fixture = os.path.join(FIXTURES, stem + ".xlsx")
        out_dir = os.path.join(LOGS, model_id, conv_id, "teach", request_id)
        t = _run_teach(fixture, out_dir, request_dir=rdir)
        skill = t.get("skill")
        skill_dir = os.path.join(out_dir, "skill")
        if skill and os.path.isdir(skill_dir):
            _replace_skill_dir(home, skill, skill_dir)
        done = {}
        done_path = os.path.join(rdir, "done.json")
        if os.path.exists(done_path):
            done = json.load(open(done_path))
        if done.get("charts"):
            msg = (f"Claude finished: {done.get('summary') or 'new charts'}. Charts made: "
                   f"{', '.join(done['charts'])}. Call chart_show once with the file we were working on and "
                   f"charts={json.dumps(done['charts'])}, then carry on.")
        else:
            msg = (f"Teaching finished: {done.get('summary') or 'the file skill is ready'}. "
                   "Open the file again with file_open (same goal as before) and continue with my question.")
        return {
            "started": True,
            "teach_chat": ("Chart: " if done.get("charts") else "Teach: ") + (done.get("summary") or stem),
            "done": bool(done.get("skill") or t.get("done")),
            "skill": skill,
            "secs": t.get("secs"),
            "claude_cost": t.get("claude_cost"),
            "cards": t.get("cards"),
            "charts": done.get("charts") or [],
            "share_labels": kwargs.get("share_labels") or [],
            "tell_the_user": msg,
        }

    mcp.TOOLS["teach_send"] = (teach_send, desc, props, req)
    return teach_send


def _numbers(text):
    return [float(x.replace(",", "")) if "." in x or "," in x else int(x.replace(",", ""))
            for x in re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?", text or "")]


def _approx_match(expected, got, tol=0.05):
    if not expected:
        return False
    if len(expected) != len(got):
        return False
    return all(abs(float(a) - float(b)) <= tol for a, b in zip(expected, got))


def _final_numbers_match(turn, ref):
    if ref is None:
        return True
    texts = [e.get("text", "") for e in (turn or {}).get("events", []) if e.get("type") == "model" and e.get("text")]
    got = _numbers("\n".join(texts))
    if not got:
        return False
    return _approx_match([float(x) for x in ref], got[:len(ref)])


def _summarize(log, conv):
    steps = conv["steps"]
    turn_by_step = {t["step"]: t for t in log["turns"] if isinstance(t.get("step"), int)}
    control_idx = 2 if len(steps) > 2 else None
    teach_idx = 3 if len(steps) > 3 else None
    reask_idx = 5 if len(steps) > 5 else None

    control_turn = turn_by_step.get(control_idx, {})
    teach_turn = turn_by_step.get(teach_idx, {})
    card_turn = turn_by_step.get(teach_idx + 1, {})
    reask_turn = turn_by_step.get(reask_idx, {})
    reask_check = ((steps[reask_idx] if reask_idx is not None else {}) or {}).get("check") or {}
    reask_ref = (reask_check.get("ref") or {}).get("numbers")

    routed = any(e.get("name") in ("teach_file", "chart_request") for e in control_turn.get("events", []))
    wrong_bounce = 1 if routed else 0
    sent = any(e.get("name") == "teach_send" for e in card_turn.get("events", []))
    teach_evt = next((e for e in card_turn.get("events", []) if e.get("name") == "teach_send"), {})
    teach_res = teach_evt.get("result") if isinstance(teach_evt.get("result"), dict) else {}
    claude_done = bool(teach_res.get("done"))
    came_back = bool(sent and reask_turn)
    chart_ok = bool(teach_res.get("charts")) and any(
        e.get("name") == "chart_show" and not (isinstance(e.get("result"), dict) and e["result"].get("error"))
        for e in card_turn.get("events", [])
    )
    if chart_ok:
        final_match = True
    elif reask_ref is not None:
        final_match = _final_numbers_match(reask_turn, reask_ref)
    elif "chart_show" in (reask_check.get("tools_any") or []):
        final_match = any(e.get("name") == "chart_show" for e in reask_turn.get("events", []))
    else:
        final_match = True
    never_returned = 1 if sent and not final_match else 0
    mins = round((teach_res.get("secs") or 0) / 60.0, 2)
    cost = round(float(teach_res.get("claude_cost") or 0.0), 4)
    return {
        "routed_right": bool(routed or any(e.get("name") in ("file_ask", "chart_request", "teach_file") for e in teach_turn.get("events", []))),
        "sent": bool(sent),
        "claude_done": bool(claude_done),
        "came_back": bool(came_back),
        "answered_right_after": bool(final_match),
        "wrong_bounces": wrong_bounce,
        "never_returned": never_returned,
        "minutes": mins,
        "cost": cost,
    }


def run(model_id, scenario_file, conv_id, out_path, variant="e7-soft12"):
    convo = _load_module("e3_b9_convo", os.path.join(B9, "harness", "convo.py"))
    idli = _load_module("idli", os.path.join(B9, "harness", "idli.py"))
    with open(scenario_file) as f:
        sc = json.load(f)
    conv = next(c for c in sc["conversations"] if c["id"] == conv_id)
    stem = conv.get("ref_file") or ""
    link = _parse_link(conv["steps"][0].get("user", ""))
    current = {"stem": stem, "link": link, "model": model_id, "conv": conv_id, "home": None}
    orig_setup = idli.setup
    orig_apply_variant = convo.apply_variant

    def setup(home):
        current["home"] = home
        mcp = orig_setup(home)
        if stem:
            _copy_skill(home, stem)
            _ensure_learned(mcp, home, stem, link)
        teach_send = _wrap_teach_send(mcp, home, stem or conv_id, os.path.basename(os.path.dirname(out_path)), conv_id)
        mcp.e3_teach_send = teach_send
        return mcp

    def apply_variant(mcp, variant_name):
        orig_apply_variant(mcp, variant_name)
        orig_on_card = getattr(mcp, "on_card", None)

        def on_card(card, answer):
            a = str(answer).lower()
            rid = getattr(mcp, "e7_state", {}).get("teach_rid")
            if rid and "yes" in a and ("send" in a or "switch" in a or "draw" in a or "back" in a):
                if getattr(mcp, "e7_state", None):
                    mcp.e7_state["phase"] = "analyse"
                return {"name": "teach_send", "args": {"request_id": rid}, "result": mcp.e3_teach_send(rid)}
            return orig_on_card(card, answer) if orig_on_card else None

        if orig_on_card:
            mcp.on_card = on_card

    convo.apply_variant = apply_variant
    idli.setup = setup
    log = convo.run(model_id, scenario_file, conv_id, out_path, variant)
    log["e3"] = _summarize(log, conv)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(log, f, indent=1, default=str)
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--conv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", default="e7-soft12")
    a = ap.parse_args()
    # idli.setup() chdirs into a temp home, so a relative --out would land there (the 2026-11-11 bug: exit 0, no
    # file). Resolve it now; a directory means <dir>/<conv>.json, as e3_all.sh passes it.
    out = os.path.abspath(a.out)
    if os.path.isdir(out) or not out.endswith(".json"):
        out = os.path.join(out, a.conv + ".json")
    run(a.model, os.path.abspath(a.scenario), a.conv, out, a.variant)


if __name__ == "__main__":
    main()
