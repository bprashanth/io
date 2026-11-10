"""Run one scripted conversation against one model, the way Idli runs in the app, and write a transcript.

The loop plays Claude Code's part: the system prompt carries Idli's instructions (idli/CLAUDE.md, or a
variant), the model gets Idli's real tools plus AskUserQuestion (the card), tool calls run against the fake
Drive (idli.py), and a card waits for the scripted user's click. Claude Code's own ~10k-token system prompt
is not reproduced: every model gets the same lean one, so the comparison is about the model.

A script is a list of steps: {"user": "..."} (a typed message) or {"pick": "<regex on option labels>"} (a
click on the card that should be showing). If the model asks in plain text where a card was expected, the
user types the option's words instead; if it shows a card where the user would type, the user types their
message into the card's "Other" box. Both are recorded as deviations.

  python harness/convo.py --model <id> --scenario <file.json> --conv <id> --out <transcript.json>
                          [--variant <name>]
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)

MAX_STEPS = 12      # model calls per user turn
TURN_SECONDS = 300  # per user turn
SAME_CALL_LOOP = 3  # the same tool call this many times in one turn = a loop


def load_models():
    with open(os.path.join(BENCH, "models.json")) as f:
        return json.load(f)


def api_key(spec):
    k = spec.get("key_file")
    if not k:
        return spec.get("key", "none")
    with open(os.path.expanduser(k)) as f:
        return json.load(f)["api_key"]


def chat(spec, messages, tools, timeout=240):
    body = {"model": spec["model"], "messages": messages, "tools": tools, "tool_choice": "auto",
            "max_tokens": spec.get("max_tokens", 4096), "temperature": spec.get("temperature", 0.6)}
    body.update(spec.get("extra") or {})
    req = urllib.request.Request(spec["base"].rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + api_key(spec)})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.load(r)
            if out.get("error"):
                raise RuntimeError(str(out["error"])[:300])
            return out
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError, ConnectionError) as e:
            detail = e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else str(e)
            last = f"{type(e).__name__}: {detail}"
            if isinstance(e, urllib.error.HTTPError) and e.code in (400, 401, 403, 404):
                break
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(last)


def system_prompt(variant):
    vdir = os.path.join(BENCH, "variants", variant)
    path = os.path.join(vdir, "CLAUDE.md") if variant != "base" else os.path.join(
        os.path.dirname(os.path.dirname(BENCH)), "runs", "2026-11-06-oss-desktop-independent", "cowork", "idli", "CLAUDE.md")
    with open(path) as f:
        text = f.read()
    return ("You are the assistant in Idli, a desktop app. The user sees your replies in a chat and clicks cards you "
            "show with AskUserQuestion. Today is 2026-11-10.\n\nInstructions from the workspace (CLAUDE.md):\n\n" + text)


def card_answer(card, pick):
    """Claude Code's AskUserQuestion result text for a click (or typed Other)."""
    parts = []
    for q in (card.get("questions") or []):
        opts = [o.get("label", "") for o in (q.get("options") or [])]
        if pick.get("pick"):
            rx = re.compile(pick["pick"], re.I)
            chosen = [o for o in opts if rx.search(o)]
            if q.get("multiSelect"):
                ans = ", ".join(chosen) if chosen else (opts[0] if opts else "")
            else:
                ans = chosen[0] if chosen else None
            if ans is None:
                ans = pick.get("say") or pick["pick"]
        else:
            ans = pick["user"]
        parts.append(f'"{q.get("question", "")}"="{ans}"')
    return "User has answered your questions: " + ", ".join(parts) + ". You can now continue with the user's answers in mind."


def matched(card, pick):
    if not pick.get("pick"):
        return False
    rx = re.compile(pick["pick"], re.I)
    return any(rx.search(o.get("label", "")) for q in (card.get("questions") or []) for o in (q.get("options") or []))


def run(model_id, scenario_file, conv_id, out_path, variant="base"):
    import idli
    spec = load_models()[model_id]
    with open(scenario_file) as f:
        sc = json.load(f)
    conv = next(c for c in sc["conversations"] if c["id"] == conv_id)
    home = tempfile.mkdtemp(prefix=f"idli9b-{model_id}-{conv_id}-", dir=os.environ.get("IDLI9B_TMP") or None)
    mcp = idli.setup(home)
    only = None
    vtools = os.path.join(BENCH, "variants", variant, "tools.json")
    if variant != "base" and os.path.exists(vtools):
        with open(vtools) as f:
            only = set(json.load(f))
    tools = idli.schemas(mcp, only)
    if variant != "base":
        hook = os.path.join(BENCH, "variants", variant, "hook.py")
        if os.path.exists(hook):
            import importlib.util
            m = importlib.util.spec_from_file_location("variant_hook", hook)
            mod = importlib.util.module_from_spec(m)
            m.loader.exec_module(mod)
            mod.apply(mcp, tools)
    messages = [{"role": "system", "content": system_prompt(variant)}]
    steps = list(conv["steps"])
    log = {"model": model_id, "variant": variant, "scenario": os.path.basename(scenario_file), "conv": conv_id,
           "segments": conv.get("segments", []), "turns": []}
    i = 0
    t_conv = time.time()
    while i < len(steps):
        step = steps[i]
        if step.get("optional"):  # a card that didn't show: nothing to click
            log["turns"].append({"step": i, "input": step, "events": [], "deviations": [], "skipped": True})
            i += 1
            continue
        turn = {"step": i, "input": step, "events": [], "deviations": []}
        log["turns"].append(turn)
        i += 1
        if step.get("pick"):
            turn["deviations"].append("no_card_shown")
            text = step.get("say") or re.sub(r"[\\^$().|?*+\[\]]", "", step["pick"]).split("|")[0]
            messages.append({"role": "user", "content": text})
        else:
            messages.append({"role": "user", "content": step["user"]})
        t0 = time.time()
        calls_seen = {}
        for n in range(MAX_STEPS):
            if time.time() - t0 > TURN_SECONDS:
                turn["deviations"].append("turn_timeout")
                break
            t1 = time.time()
            try:
                resp = chat(spec, messages, tools)
            except Exception as e:
                turn["events"].append({"type": "api_error", "error": str(e)[:400]})
                break
            msg = resp["choices"][0]["message"]
            fin = resp["choices"][0].get("finish_reason")
            usage = resp.get("usage") or {}
            content = msg.get("content") or ""
            if isinstance(content, list):
                content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
            tcs = msg.get("tool_calls") or []
            turn["events"].append({"type": "model", "secs": round(time.time() - t1, 1), "finish": fin,
                                   "text": content, "tool_calls": [{"name": c["function"]["name"],
                                                                   "args": c["function"].get("arguments")} for c in tcs],
                                   "reasoning_chars": len(msg.get("reasoning_content") or msg.get("reasoning") or ""),
                                   "usage": {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens")}})
            am = {"role": "assistant", "content": content or None}
            if tcs:
                am["tool_calls"] = [{"id": c.get("id") or f"call_{n}_{j}", "type": "function",
                                     "function": {"name": c["function"]["name"],
                                                  "arguments": c["function"].get("arguments") or "{}"}}
                                    for j, c in enumerate(tcs)]
            messages.append(am)
            if not tcs:
                break
            for c in am["tool_calls"]:
                name, raw = c["function"]["name"], c["function"]["arguments"]
                try:
                    args = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except ValueError:
                    args = None
                key = name + json.dumps(args, sort_keys=True)
                calls_seen[key] = calls_seen.get(key, 0) + 1
                if args is None:
                    result = {"error": "The arguments were not valid JSON. Call the tool again with a JSON object."}
                    turn["events"].append({"type": "tool", "name": name, "args": raw, "error": "bad_json"})
                elif name == "AskUserQuestion":
                    while i < len(steps) and steps[i].get("optional") and not matched(args, steps[i]):
                        log["turns"].append({"step": i, "input": steps[i], "events": [], "deviations": [],
                                             "skipped": True})
                        i += 1
                    nxt = steps[i] if i < len(steps) else None
                    if nxt is None:
                        result = "The user closed the card without answering."
                        turn["events"].append({"type": "card", "card": args, "answer": None})
                    else:
                        if nxt.get("pick") and not matched(args, nxt):
                            turn["deviations"].append("card_without_expected_option")
                        if not nxt.get("pick"):
                            turn["deviations"].append("card_where_user_types")
                        result = card_answer(args, nxt)
                        turn["events"].append({"type": "card", "card": args, "answer": result, "answered_step": i})
                        i += 1
                        log["turns"].append(turn := {"step": i - 1, "input": nxt, "events": [], "deviations": [],
                                                     "via_card": True})
                        t0 = time.time()
                        calls_seen = {}
                else:
                    t2 = time.time()
                    import idli as _i
                    out, err = _i.call(mcp, name, args)
                    result = out
                    turn["events"].append({"type": "tool", "name": name, "args": args, "secs": round(time.time() - t2, 2),
                                           "result": out, "error": bool(err)})
                messages.append({"role": "tool", "tool_call_id": c["id"],
                                 "content": result if isinstance(result, str) else
                                 json.dumps(result, ensure_ascii=False, indent=1, default=str)})
            if any(v >= SAME_CALL_LOOP for v in calls_seen.values()):
                turn["deviations"].append("loop_same_call")
                break
        else:
            turn["deviations"].append("step_cap")
        turn["secs"] = round(time.time() - t0, 1)
    log["secs"] = round(time.time() - t_conv, 1)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(log, f, indent=1, default=str)
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--conv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", default="base")
    a = ap.parse_args()
    run(a.model, a.scenario, a.conv, a.out, a.variant)
