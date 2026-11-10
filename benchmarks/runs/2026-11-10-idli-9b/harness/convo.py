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
VARIANTS = os.environ.get("IDLI9B_VARIANTS") or os.path.join(BENCH, "variants")  # another eval's variants
SCENARIOS = os.environ.get("IDLI9B_SCENARIOS") or os.path.join(BENCH, "scenarios")
RESULTS = os.environ.get("IDLI9B_RESULTS") or os.path.join(BENCH, "results")
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
    vdir = os.path.join(VARIANTS, variant)
    path = os.path.join(vdir, "CLAUDE.md") if variant != "base" else os.path.join(
        os.path.dirname(os.path.dirname(BENCH)), "runs", "2026-11-06-oss-desktop-independent", "cowork", "idli", "CLAUDE.md")
    with open(path) as f:
        text = f.read()
    return ("You are the assistant in Idli, a desktop app. The user sees your replies in a chat and clicks cards you "
            "show with AskUserQuestion. Today is 2026-11-10.\n\nInstructions from the workspace (CLAUDE.md):\n\n" + text)


def _questions(card):
    """A card's questions, tolerating the shapes small models produce (a string, options as plain strings)."""
    qs = card.get("questions") if isinstance(card, dict) else None
    if isinstance(qs, str):
        try:
            qs = json.loads(qs)
        except ValueError:
            qs = [{"question": qs}]
    if isinstance(qs, dict):
        qs = [qs]
    out = []
    for q in qs or []:
        if not isinstance(q, dict):
            q = {"question": str(q)}
        opts = q.get("options") or []
        if isinstance(opts, str):
            opts = [opts]
        q = dict(q, options=[o if isinstance(o, dict) else {"label": str(o)} for o in opts])
        out.append(q)
    return out


def valid_card(card):
    qs = card.get("questions") if isinstance(card, dict) else None
    if not isinstance(qs, list) or not 1 <= len(qs) <= 4:
        return False
    for q in qs:
        if not isinstance(q, dict) or not isinstance(q.get("question"), str):
            return False
        opts = q.get("options")
        if not isinstance(opts, list) or not 2 <= len(opts) <= 4:
            return False
        if not all(isinstance(o, dict) and isinstance(o.get("label"), str) for o in opts):
            return False
    return True


def obvious_pick(card, conv):
    """The option a person would click without thinking: the one naming the file this conversation is about."""
    want = (conv.get("ref_file") or "").lower()
    if not want or not valid_card(card) or len(card["questions"]) != 1:
        return None
    hits = [o["label"] for o in card["questions"][0]["options"] if want in o["label"].lower()
            or want in str(o.get("description", "")).lower()]
    return hits[0] if len(hits) == 1 else None


def card_answer(card, pick):
    """Claude Code's AskUserQuestion result text for a click (or typed Other)."""
    parts = []
    for q in _questions(card):
        opts = [str(o.get("label", "")) for o in q["options"]]
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
    return any(rx.search(str(o.get("label", ""))) for q in _questions(card) for o in q["options"])


def apply_variant(mcp, variant):
    """A variant's hook.py changes tools (as a patch to sites/*/tools.py would) before the model sees them."""
    hook = os.path.join(VARIANTS, variant, "hook.py")
    if variant != "base" and os.path.exists(hook):
        import importlib.util
        m = importlib.util.spec_from_file_location("variant_hook", hook)
        mod = importlib.util.module_from_spec(m)
        m.loader.exec_module(mod)
        mod.apply(mcp, None)


def guard_reason(guards, turn_events, text, allowed, nudged):
    """What a Claude Code Stop hook would say to send the model back for one more step, or None.
    card: a tool in this turn returned a card the model was told to show, and no card was shown after it.
    numbers: the reply has numbers no tool, card or user gave (the model worked them out)."""
    if guards.get("card"):
        last_card, shown_after = None, False
        for e in turn_events:
            if e["type"] == "tool" and isinstance(e.get("result"), dict) and isinstance(e["result"].get("card"), dict) \
                    and "AskUserQuestion" in str(e["result"].get("then", "")):
                last_card, shown_after = e, False
            if e["type"] == "card" and last_card is not None:
                shown_after = True
        if last_card is not None and not shown_after and ("card", id(last_card)) not in nudged:
            nudged.add(("card", id(last_card)))
            return (f"Idli check: {last_card['name']} returned a card for the user, but you didn't show it. Call "
                    "AskUserQuestion now with exactly that `card` (its questions and options as they are). Don't write "
                    "its options as text.")
    if guards.get("numbers"):
        from score import numbers
        bad = [n for n in numbers(text) if n not in allowed and not re.fullmatch(r"[0-9]", n)]
        if bad and ("numbers", text) not in nudged:
            nudged.add(("numbers", text))
            return ("Idli check: these numbers in your reply didn't come from a tool: " + ", ".join(bad[:5]) +
                    ". Idli never works out numbers itself. Write the reply again with only numbers from tool answers "
                    "(call file_ask if you need another one).")
    return None


def run(model_id, scenario_file, conv_id, out_path, variant="base"):
    import idli
    spec = load_models()[model_id]
    with open(scenario_file) as f:
        sc = json.load(f)
    conv = next(c for c in sc["conversations"] if c["id"] == conv_id)
    home = tempfile.mkdtemp(prefix=f"idli9b-{model_id}-{conv_id}-", dir=os.environ.get("IDLI9B_TMP") or None)
    mcp = idli.setup(home)
    only = None
    vtools = os.path.join(VARIANTS, variant, "tools.json")
    if variant != "base" and os.path.exists(vtools):
        with open(vtools) as f:
            only = set(json.load(f))
    apply_variant(mcp, variant)
    tools = idli.schemas(mcp, only)
    gpath = os.path.join(VARIANTS, variant, "guards.json")
    guards = json.load(open(gpath)) if variant != "base" and os.path.exists(gpath) else {}
    messages = [{"role": "system", "content": system_prompt(variant)}]
    steps = list(conv["steps"])
    log = {"model": model_id, "variant": variant, "scenario": os.path.basename(scenario_file), "conv": conv_id,
           "segments": conv.get("segments", []), "turns": []}
    i = 0
    nudged = set()
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
                # a variant may change the tool list as the chat moves on (E7 hard phases)
                cur = idli.schemas(mcp, mcp.phase_tools()) if hasattr(mcp, "phase_tools") else tools
                resp = chat(spec, messages, cur)
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
                                   "provider": resp.get("provider"),
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
                if guards:
                    from score import numbers
                    allowed = set()
                    for mm in messages:
                        if mm["role"] in ("user", "tool") and isinstance(mm.get("content"), str) \
                                and not mm["content"].startswith("<system-reminder>Idli check"):
                            allowed.update(numbers(mm["content"]))
                    for mm in messages:  # numbers in cards the model showed and in its own tool arguments
                        for tc in mm.get("tool_calls") or []:
                            allowed.update(numbers(tc["function"]["arguments"] or ""))
                    why = guard_reason(guards, turn["events"], content, allowed, nudged)
                    if why:
                        turn["events"].append({"type": "guard", "reason": why})
                        messages.append({"role": "user", "content": "<system-reminder>" + why + "</system-reminder>"})
                        continue
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
                elif name == "AskUserQuestion" and not valid_card(args):
                    # Claude Code checks the card against its schema and returns the error to the model
                    result = ("<tool_use_error>InputValidationError: AskUserQuestion needs questions: a list of "
                              "{question, header, multiSelect, options: [{label, description}]} (2-4 options)."
                              "</tool_use_error>")
                    turn["events"].append({"type": "tool", "name": name, "args": args, "error": "bad_card"})
                elif name == "AskUserQuestion" and guards.get("tool_cards_only") and not any(
                        e["type"] == "tool" and isinstance(e.get("result"), dict) and e["result"].get("card")
                        for e in turn["events"]):
                    # E6 fix: a card only when a tool handed one over; otherwise ask in plain text
                    result = ("<tool_use_error>Idli check: no tool gave you a card to show. Ask in one plain line "
                              "instead (the person types their answer).</tool_use_error>")
                    turn["events"].append({"type": "tool", "name": name, "args": args, "error": "own_card_blocked"})
                elif name == "AskUserQuestion":
                    while i < len(steps) and steps[i].get("optional") and not matched(args, steps[i]):
                        log["turns"].append({"step": i, "input": steps[i], "events": [], "deviations": [],
                                             "skipped": True})
                        i += 1
                    nxt = steps[i] if i < len(steps) else None
                    obvious = obvious_pick(args, conv) if nxt is not None and not nxt.get("pick") else None
                    if nxt is None:
                        result = "The user closed the card without answering."
                        turn["events"].append({"type": "card", "card": args, "answer": None})
                    elif obvious:  # a "which file?" card: the person clicks the file they mean, then types on
                        result = card_answer(args, {"pick": "^" + re.escape(obvious) + "$"})
                        turn["events"].append({"type": "card", "card": args, "answer": result, "obvious_click": True})
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
                        if hasattr(mcp, "on_card"):  # E7: a click runs the step itself (send to Claude, working copy)
                            did = mcp.on_card(args, result)
                            if did:
                                turn["events"].append({"type": "tool", "name": did["name"], "args": did["args"],
                                                       "result": did["result"], "error": False, "by_card": True})
                                result += ("\n\nIdli did this after the click: " + did["name"] + " -> " +
                                           json.dumps(did["result"], ensure_ascii=False, default=str)[:3000])
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
