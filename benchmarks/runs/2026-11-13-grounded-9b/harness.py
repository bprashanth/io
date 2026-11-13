"""Play Claude Code for Idli's chat, offline: the chat goes to lib/modes.respond (the real 9B), tool calls run against
the synthetic households file, and a script answers like the owner does (typed messages, card picks).

  python3 harness.py <mode> <script id>... [--fault drop_series]     modes: idli-9b, idli-9b-careful, idli-9b-auto
Writes traces/<mode>-<script>.json and prints each turn.
Needs: the 9B on 127.0.0.1:8291, a router on 8186 for the spec calls (MUSE_URL), the cowork .venv.
"""
import json
import os
import re
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
COWORK = os.path.join(os.path.dirname(HERE), "2026-11-06-oss-desktop-independent", "cowork")
sys.path.insert(0, COWORK)

SCRIPTS = {
    # the owner's own words (chats 309d9db3, 37b9cde2, cdb532f2, 409bec47 on the laptop)
    "yerawada": ["help me understand why yerawada ward is so high",
                 {"pick": "vulnerability"},
                 "what is the graph you showed telling me? what is on the y vs x axis (i guess x is vulnerability score)",
                 "how are you combining all thos enumbers here? all im seeing is a single blue bar?",
                 "why might it be higher?"],
    "debt": ["why is yearwada ward's debt so high?",
             {"pick": "debt"},
             "right i want to know why average monthly income is low (or is it?)",
             {"pick": "income"},
             "what is average months of income owed? are you saying over 12 months of income you divided income / debt?"],
    # the proposals' scripts
    "state": ["show average debt by ward as a chart", "now show vulnerability by ward as a chart",
              "what's the y-axis?", "what was it on the previous chart?", "put it in a table"],
    "falsepush": ["compare average debt across yerawada, kasewadi and ramtekdi as a chart",
                  "wait, why is there only one bar on the chart? where are kasewadi and ramtekdi?"],
    "nodata": ["how has vulnerability changed from last year?", "can you just estimate it?",
               "show yerawada household debt in 2031"],
    "panels": ["plot average income and vulnerability score for all wards on one bar chart",
               "what is the graph telling me?", "all im seeing is one panel with income, where is the score?"],
}
# HELD OUT (written 2026-11-14 00:55 before any run; code frozen at that commit; never tuned on). New wording, the
# proposals' cases not used above, and a second taught file never looked at during development. A card is answered
# with the option matching `card` (the person's intent), else the first option.
HOLDOUT = {
    "h_struggle": {"card": "vulnerab", "turns": [
        "which ward is struggling the most and why?",
        "the chart looks like it only has one ward on it",
        "ok show savings instead"]},
    "h_modify": {"turns": [
        "compare kasewadi's average debt with the rest of the wards",
        "now income instead", "make that median", "show the numbers as a table"]},
    "h_share": {"turns": [
        "what share of ramtekdi households owe more than a year of income?",
        "how many households were left out because of missing data?",
        "and how does that share compare with the other wards?"]},
    "h_causal": {"card": "saving", "turns": [
        "hadapsar ward savings look really high",
        "could a couple of households be skewing that?",
        "so does having more savings make households less vulnerable?"]},
    "f_money": {"file": "drive/field_programme_tracker.xlsx", "card": "disburs", "turns": [
        "why is village C getting so much money?",
        "what's on the bottom axis of that chart?",
        "that's not right, I can only see one bar"]},
    "f_time": {"file": "drive/field_programme_tracker.xlsx", "turns": [
        "how has disbursement changed month by month?",
        "which officer did the most visits?",
        "what does disbursed mean exactly, is it per visit?"]},
}


def tool_defs():
    from sites.files import tools as T
    out = []
    for name in ["start", "file_get", "file_open", "file_ask", "teach_file", "teach_send", "chart_request",
                 "chart_show", "form_explain"]:
        fn, desc, props, req = T.TOOLS[name]
        out.append({"name": "mcp__cowork__" + name, "description": desc,
                    "input_schema": {"type": "object", "properties": props, "required": req}})
    out.append({"name": "AskUserQuestion", "description": "Ask the user a question with options.",
                "input_schema": {"type": "object", "properties": {"questions": {"type": "array"}},
                                 "required": ["questions"]}})
    return out


def run_tool(name, inp):
    from sites.files import tools as T
    short = name.split("__")[-1]
    if short == "file_get":  # offline: the link is this script's fixture file (no download)
        return T.t_file_open(CURRENT[0], show_form=False, goal=inp.get("goal"))
    if short in ("teach_send", "chart_request_send"):  # needs Paseo + Claude: recorded as a detour, not run
        return {"started": False, "error": "teaching isn't available in this offline test (recorded as a detour)"}
    fn = T.TOOLS[short][0]
    try:
        return fn(**inp)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


CURRENT = ["drive/households.xlsx"]
LINKS = {"drive/households.xlsx": "https://docs.google.com/spreadsheets/d/1HhFixtureHouseholds0000000000000/edit?gid=0",
         "drive/field_programme_tracker.xlsx": "https://docs.google.com/spreadsheets/d/1FfFixtureTracker00000000000000/edit"}
MUSE_ROUTER = os.environ.get("IDLI_ROUTER", "http://127.0.0.1:8185")


def muse(j):
    """Today's product: Muse 30B through the DGX router (which rewrites the request exactly as for the app), with
    Idli's instructions as Claude Code gives them (CLAUDE.md in the system prompt)."""
    import urllib.request
    sysmsg = ("You are Claude Code, Anthropic's official CLI for Claude.\n\nContents of CLAUDE.md (project "
              "instructions):\n\n" + open(os.path.join(COWORK, "idli", "CLAUDE.md")).read())
    body = {"model": "muse-glimmer-30b", "max_tokens": 4096, "system": sysmsg, **j}
    req = urllib.request.Request(MUSE_ROUTER + "/v1/messages", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "anthropic-version": "2023-06-01",
                                  "x-api-key": "none"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def card_answer(card, pick):
    qs = card.get("questions") if isinstance(card, dict) else None
    q = (qs or [{}])[0] if isinstance(qs, list) else {}
    q = q if isinstance(q, dict) else {}
    q.setdefault("question", str(card)[:80])
    opts = [o.get("label") if isinstance(o, dict) else str(o) for o in q.get("options") or []]
    got = next((o for o in opts if pick.lower() in o.lower()), pick)
    return got, f'User has answered your questions: "{q["question"]}"="{got}". You can now continue with the user\'s answers in mind.'


def main():
    from lib import modes
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode, ids = args[0], args[1:]
    allscripts = {**{k: {"turns": v} for k, v in SCRIPTS.items()}, **HOLDOUT}
    tools = tool_defs()
    os.makedirs(os.path.join(HERE, "traces"), exist_ok=True)
    for sid in ids:
        from sites.files import tools as T
        T._threads.clear()
        from lib import careful, auto
        careful._state.clear()
        auto._threads.clear()
        sc = allscripts[sid]
        fname = sc.get("file", "drive/households.xlsx")
        CURRENT[0] = fname
        # the start as in the app: the person pastes the link, file_get opens it, its card is answered
        opened = run_tool("mcp__cowork__file_get", {"link": LINKS[fname], "goal": "analyse"})
        tid, cid = "toolu_" + uuid.uuid4().hex[:20], "toolu_" + uuid.uuid4().hex[:20]
        msgs = [{"role": "user", "content": LINKS[fname]},
                {"role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": "mcp__cowork__file_get",
                                                   "input": {"link": LINKS[fname], "goal": "analyse"}}]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid,
                                              "content": json.dumps(opened, ensure_ascii=False, default=str)}]}]
        card0 = opened.get("card") if isinstance(opened, dict) else None
        if isinstance(card0, dict):
            labels = [o.get("label", "") for q in card0.get("questions") or [] for o in q.get("options") or []]
            pick = next((l for l in labels if l.startswith("I have a question")), None) or \
                next((l for l in labels if l.startswith("No, analyse")), labels[0] if labels else "OK")
            _, text = card_answer(card0, pick)
            msgs += [{"role": "assistant", "content": [{"type": "tool_use", "id": cid, "name": "AskUserQuestion",
                                                        "input": card0}]},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": cid, "content": text}]}]
        msgs.append({"role": "assistant", "content": [{"type": "text", "text": "What would you like to know?"}]})
        trace = []
        steps = list(sc["turns"])
        pending_card = None
        while steps:
            step = steps.pop(0)
            if isinstance(step, dict):
                if not pending_card:
                    trace.append({"skipped_pick": step["pick"]})
                    continue
                label, text = card_answer(pending_card[1], step["pick"])
                msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": pending_card[0],
                                                          "content": text}]})
                turn = {"user": f"[card] {label}", "calls": []}
                pending_card = None
            else:
                if pending_card:  # typed instead of picking: Claude Code sends it as the card's answer ("Other")
                    _, text = card_answer(pending_card[1], step)
                    msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": pending_card[0],
                                                              "content": text}]})
                    pending_card = None
                else:
                    msgs.append({"role": "user", "content": step})
                turn = {"user": step, "calls": []}
            t0 = time.time()
            for _ in range(8):
                resp = (muse({"messages": msgs, "tools": tools}) if mode == "muse-glimmer-30b" else
                        modes.respond({"model": mode, "messages": msgs, "tools": tools}))
                resp["content"] = [b for b in resp["content"] if b.get("type") in ("text", "tool_use")]
                msgs.append({"role": "assistant", "content": resp["content"]})
                uses = [b for b in resp["content"] if b["type"] == "tool_use"]
                texts = [b["text"] for b in resp["content"] if b["type"] == "text" and b["text"].strip()]
                if texts:
                    turn["reply"] = "\n".join(texts)
                if not uses:
                    break
                u = uses[0]
                if u["name"] == "AskUserQuestion":
                    turn["card"] = u["input"]
                    if sid in HOLDOUT:  # the person answers by their intent, then the turn goes on
                        opts = [o["label"] for o in (u["input"].get("questions") or [{}])[0].get("options") or []]
                        want = sc.get("card") or ""
                        pick = next((o for o in opts if want and want in o.lower()), opts[0] if opts else "OK")
                        _, text = card_answer(u["input"], pick)
                        turn["calls"].append({"tool": "AskUserQuestion", "picked": pick})
                        msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": u["id"],
                                                                  "content": text}]})
                        continue
                    pending_card = (u["id"], u["input"])
                    break
                res = run_tool(u["name"], u["input"])
                turn["calls"].append({"tool": u["name"].split("__")[-1], "input": u["input"],
                                      "result": {k: v for k, v in res.items() if k in
                                                 ("reply", "answer", "render_receipt", "gate", "form_fill", "intent",
                                                  "card", "error", "chart_markdown", "cannot")}
                                      if isinstance(res, dict) else res,
                                      "manifest": (res.get("manifest") if isinstance(res, dict) else None)})
                msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": u["id"],
                                                          "content": json.dumps(res, ensure_ascii=False, default=str)}]})
            turn["secs"] = round(time.time() - t0, 1)
            trace.append(turn)
            print(f"\n>>> {turn['user']}")
            for c in turn["calls"]:
                print(f"    [{c['tool']}] {json.dumps(c.get('input') or c.get('picked'), ensure_ascii=False)[:160]}")
            if turn.get("card"):
                q = turn["card"]["questions"][0]
                print(f"    [card] {q['question']} :: {[o['label'] for o in q.get('options') or []]}")
            print("<<< " + (turn.get("reply") or "(no text)").replace("\n", "\n    ")[:1600] + f"  ({turn['secs']}s)")
        out = os.path.join(HERE, "traces", f"{mode}-{sid}{'-fault' if '--fault' in sys.argv else ''}.json")
        with open(out, "w") as f:
            json.dump(trace, f, indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
