"""The same scripted conversation, but through the real Claude Code CLI (the Agent SDK, as Paseo runs it):
Claude Code's own system prompt and tool set, Idli's CLAUDE.md loaded from the workspace folder, Idli's MCP
server (harness/mcp_server.py: the real tools on the fake Drive), the production disallowed-tools list, and
cards answered through the SDK's permission callback the way Paseo answers them. The transcript has the
same shape as convo.py's, so score.py scores both.

Needs the SDK venv (/tmp/claude-1000/b9/sdkvenv) and a model behind an Anthropic-style /v1/messages:
Muse through the prefix proxy (8185), a local llama.cpp server, or OpenRouter.

  sdkvenv/bin/python harness/cc_convo.py --model <id> --scenario <file> --conv <id> --out <file> [--variant base]
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import convo  # noqa: E402  (card_answer, matched, system_prompt paths)

COWORK = os.path.join(os.path.dirname(os.path.dirname(BENCH)), "runs", "2026-11-06-oss-desktop-independent", "cowork")
DISALLOWED = ["Bash", "BashOutput", "KillShell", "Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "Glob", "Grep",
              "WebSearch", "WebFetch", "Task", "Agent", "TodoWrite", "Skill", "mcp__paseo", "Workflow", "SendMessage",
              "ScheduleWakeup", "CronCreate", "CronDelete", "CronList", "EnterPlanMode", "ExitPlanMode",
              "EnterWorktree", "ExitWorktree", "ReportFindings", "ListAgents", "mcp__cowork__gmail_draft_reply",
              "mcp__cowork__sheet_query", "mcp__cowork__sheet_profile"]  # = desktop/setup-laptop.py COWORK_PROVIDER


def endpoint(spec):
    """(ANTHROPIC_BASE_URL, token, model) for Claude Code."""
    cc = spec.get("cc") or {}
    if cc.get("base"):
        tok = convo.api_key(spec) if spec.get("key_file") else cc.get("token", "none")
        return cc["base"], tok, cc.get("model", spec["model"])
    base = spec["base"].rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base, convo.api_key(spec) if spec.get("key_file") else "none", spec["model"]


async def run(model_id, scenario_file, conv_id, out_path, variant="base"):
    from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
                                  ResultMessage, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage)
    spec = convo.load_models()[model_id]
    with open(scenario_file) as f:
        sc = json.load(f)
    conv = next(c for c in sc["conversations"] if c["id"] == conv_id)
    home = tempfile.mkdtemp(prefix=f"idli9b-cc-{model_id}-{conv_id}-", dir=os.environ.get("IDLI9B_TMP") or None)
    data = os.path.join(home, "cowork-real")
    os.makedirs(data, exist_ok=True)
    src = os.path.join(BENCH, "variants", variant, "CLAUDE.md") if variant != "base" else os.path.join(COWORK, "idli", "CLAUDE.md")
    shutil.copy(src, os.path.join(data, "CLAUDE.md"))
    cfg = os.path.join(home, "claude-config")
    os.makedirs(cfg, exist_ok=True)
    base, token, model = endpoint(spec)
    env = {"ANTHROPIC_BASE_URL": base, "ANTHROPIC_AUTH_TOKEN": token, "ANTHROPIC_MODEL": model,
           "ANTHROPIC_DEFAULT_HAIKU_MODEL": model, "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
           "ANTHROPIC_DEFAULT_OPUS_MODEL": model, "CLAUDE_CODE_SUBAGENT_MODEL": model,
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
           "ENABLE_TOOL_SEARCH": "false", "CLAUDE_CONFIG_DIR": cfg, "DISABLE_AUTOUPDATER": "1"}
    with open(os.path.join(cfg, "settings.json"), "w") as f:
        json.dump({"env": env, "permissions": {"deny": ["WebSearch", "WebFetch"]}, "autoMemoryEnabled": False}, f)
    py = sys.executable
    steps = list(conv["steps"])
    log = {"model": model_id, "variant": variant, "harness": "claude-code", "scenario": os.path.basename(scenario_file),
           "conv": conv_id, "segments": conv.get("segments", []), "turns": []}
    state = {"i": 0, "turn": None, "t_last": time.time()}

    def new_turn(idx, step, **kw):
        t = {"step": idx, "input": step, "events": [], "deviations": [], **kw}
        log["turns"].append(t)
        state["turn"] = t
        return t

    async def can_use_tool(name, inp, ctx):
        if name != "AskUserQuestion":
            return PermissionResultAllow(updated_input=inp)
        i = state["i"]
        while i < len(steps) and steps[i].get("optional") and not convo.matched(inp, steps[i]):
            log["turns"].append({"step": i, "input": steps[i], "events": [], "deviations": [], "skipped": True})
            i += 1
        nxt = steps[i] if i < len(steps) else None
        answers = {}
        if nxt is None:
            state["turn"]["events"].append({"type": "card", "card": inp, "answer": None})
            state["i"] = i
            return PermissionResultAllow(updated_input={**inp, "answers": {}})
        obvious = convo.obvious_pick(inp, conv) if not nxt.get("pick") else None
        if obvious:  # a "which file?" card: the person clicks the file they mean, then types on
            q = inp["questions"][0]
            state["turn"]["events"].append({"type": "card", "card": inp, "obvious_click": True,
                                            "answer": convo.card_answer(inp, {"pick": "^" + re.escape(obvious) + "$"})})
            state["i"] = i
            return PermissionResultAllow(updated_input={**inp, "answers": {q.get("question", ""): obvious}})
        if nxt.get("pick") and not convo.matched(inp, nxt):
            state["turn"]["deviations"].append("card_without_expected_option")
        if not nxt.get("pick"):
            state["turn"]["deviations"].append("card_where_user_types")
        text = convo.card_answer(inp, nxt)
        for q in inp.get("questions") or []:
            m = re.search(re.escape('"' + q.get("question", "") + '"="') + r'(.*?)"(?:, "|\. You can)', text)
            answers[q.get("question", "")] = m.group(1) if m else (nxt.get("user") or nxt.get("pick"))
        state["turn"]["events"].append({"type": "card", "card": inp, "answer": text, "answered_step": i})
        state["i"] = i + 1
        new_turn(i, nxt, via_card=True)
        state["t_last"] = time.time()
        return PermissionResultAllow(updated_input={**inp, "answers": answers})

    gpath = os.path.join(BENCH, "variants", variant, "guards.json")
    guards = json.load(open(gpath)) if variant != "base" and os.path.exists(gpath) else {}
    nudged = set()

    async def stop_hook(inp, tool_use_id, ctx):
        """Claude Code Stop hook: send the model back once when a card wasn't shown or a number was made up."""
        evs = state["turn"]["events"] if state["turn"] else []
        text = next((e["text"] for e in reversed(evs) if e["type"] == "model" and e.get("text")), "")
        from score import numbers
        allowed = set()
        for t in log["turns"]:
            allowed.update(numbers((t.get("input") or {}).get("user", "")))
            for e in t["events"]:
                if e["type"] in ("tool", "card"):
                    allowed.update(numbers(json.dumps(e, ensure_ascii=False, default=str)))
        why = convo.guard_reason(guards, evs, text, allowed, nudged)
        if why:
            state["turn"]["events"].append({"type": "guard", "reason": why})
            return {"decision": "block", "reason": why}
        return {}

    from claude_agent_sdk import HookMatcher
    opts = ClaudeAgentOptions(
        cwd=data, model=model, permission_mode="default", can_use_tool=can_use_tool, setting_sources=["project"],
        disallowed_tools=DISALLOWED, env=env, max_turns=24,
        mcp_servers={"cowork": {"type": "stdio", "command": py,
                                "args": ["-I", os.path.join(HERE, "mcp_server.py"), home, variant]}},
        allowed_tools=["mcp__cowork__*"],
        hooks={"Stop": [HookMatcher(hooks=[stop_hook])]} if guards else None)
    t_conv = time.time()
    pending = {}
    async with ClaudeSDKClient(options=opts) as client:
        while state["i"] < len(steps):
            i = state["i"]
            step = steps[i]
            state["i"] = i + 1
            if step.get("optional"):
                log["turns"].append({"step": i, "input": step, "events": [], "deviations": [], "skipped": True})
                continue
            turn = new_turn(i, step)
            if step.get("pick"):
                turn["deviations"].append("no_card_shown")
                msg = step.get("say") or re.sub(r"[\\^$().|?*+\[\]]", "", step["pick"]).split("|")[0]
            else:
                msg = step["user"]
            t0 = state["t_last"] = time.time()
            await client.query(msg)
            try:
                async for m in _with_timeout(client.receive_response(), convo.TURN_SECONDS):
                    now = time.time()
                    if isinstance(m, AssistantMessage):
                        texts = [b.text for b in m.content if isinstance(b, TextBlock)]
                        uses = [b for b in m.content if isinstance(b, ToolUseBlock)]
                        think = sum(len(b.thinking) for b in m.content if isinstance(b, ThinkingBlock))
                        state["turn"]["events"].append({"type": "model", "secs": round(now - state["t_last"], 1),
                                                        "finish": None, "text": "\n".join(texts).strip(),
                                                        "tool_calls": [{"name": u.name, "args": u.input} for u in uses],
                                                        "reasoning_chars": think})
                        for u in uses:
                            pending[u.id] = (u.name, u.input)
                        state["t_last"] = now
                    elif isinstance(m, UserMessage) and isinstance(m.content, list):
                        for b in m.content:
                            if isinstance(b, ToolResultBlock) and b.tool_use_id in pending:
                                name, args = pending.pop(b.tool_use_id)
                                if name == "AskUserQuestion":
                                    continue
                                content = b.content
                                if isinstance(content, list):
                                    content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
                                try:
                                    result = json.loads(content)
                                except (TypeError, ValueError):
                                    result = content
                                state["turn"]["events"].append({"type": "tool", "name": re.sub(r"^mcp__cowork__", "", name),
                                                                "args": args, "result": result, "error": bool(b.is_error)})
                        state["t_last"] = now
                    elif isinstance(m, ResultMessage):
                        state["turn"]["result"] = {"subtype": m.subtype, "turns": m.num_turns,
                                                   "cost": getattr(m, "total_cost_usd", None)}
            except asyncio.TimeoutError:
                state["turn"]["deviations"].append("turn_timeout")
                await client.interrupt()
            names = [e["name"] for t in log["turns"] if t["step"] >= i for e in t["events"] if e["type"] == "tool"]
            if any(names.count(n) >= convo.SAME_CALL_LOOP for n in set(names)) and len(names) >= 6:
                state["turn"]["deviations"].append("loop_same_call")
            state["turn"]["secs"] = round(time.time() - t0, 1)
    log["secs"] = round(time.time() - t_conv, 1)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(log, f, indent=1, default=str)


async def _with_timeout(agen, secs):
    deadline = time.time() + secs
    while True:
        try:
            m = await asyncio.wait_for(agen.__anext__(), max(1, deadline - time.time()))
        except StopAsyncIteration:
            return
        yield m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--conv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", default="base")
    a = ap.parse_args()
    asyncio.run(run(a.model, a.scenario, a.conv, a.out, a.variant))
