"""Idli's model switcher: three modes behind one Anthropic-style endpoint, picked by the model id Paseo sends.

Idli is a Claude Code chat (Paseo provider t4gc-cowork) whose ANTHROPIC_BASE_URL is the DGX router
(dgx/muse_prefix_proxy.py, reached as silo.idli.cc). The person picks the model in Paseo's model menu:

  muse-glimmer-30b  "Idli 30B (Muse)": today's product. Muse runs the chat and fills the form's spec itself.
                    The router only fixes Claude Code's mid-chat system messages (cacheable prompt) and hides
                    file_ask's `question`, so Muse sees exactly today's tools.
  idli-9b           "Idli 9B": the E7 winner (9B chat + 9B split). The local 9B runs the chat on a lean prompt
                    (idli/CLAUDE-9b.md and only the 12 Idli tools, not Claude Code's ~10k-token preamble), file_ask
                    takes the person's words and a second 9B call sets the form's dials (the split, inside the MCP
                    server), and the guards of the eval loop send the 9B back once when it skips a tool's card or
                    writes numbers no tool gave. Measured: 86% on held3, same as Muse (E7).
  idli-steam        "Steam powered": code runs the chat. Cards come from the tools and their answers map to the
                    next tool in code; typed questions go to file_ask with the person's words, where one 9B call
                    sets the form's dials; answers are shown as the code rendered them, never reworded. Codex's
                    exp/clef-form F: 19/20 vs 20/20 for the 9B chat, a third of the model calls, ~5 s instead of ~25 s.

Everything here is stateless: each request carries the whole chat, and the state (which file, which card) is read
back from it. Real data passes through here as it does through Muse today (tool results are in the chat).
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NINE_URL = os.environ.get("IDLI_9B_URL", "http://127.0.0.1:8291")
NINE_MODEL = "qwen3.5-9b"
MODES = {"muse-glimmer-30b": "muse", "idli-9b": "nine", "idli-steam": "steam", "idli-9b-careful": "careful",
         "idli-9b-auto": "auto"}
TWELVE = ["start", "file_get", "gsheet_read", "file_open", "show_dashboard", "file_ask", "teach_file", "teach_send",
          "working_copy", "working_copy_ready", "chart_request", "chart_show"]


def mode_of(model):
    m = str(model or "")
    if m in MODES:
        return MODES[m]
    if m.startswith("idli-steam"):
        return "steam"
    if m.startswith("idli-9b-careful"):
        return "careful"
    if m.startswith("idli-9b-auto"):
        return "auto"
    if m.startswith("idli-9b") or m.startswith("qwen3.5-9b"):
        return "nine"
    return "muse"


# ---------------------------------------------------------------- shared helpers
def _short(name):
    return name.split("__")[-1]


def _tool_name(tools, short):
    """The full name Claude Code gave a tool (mcp__cowork__file_get), by its short name."""
    for t in tools or []:
        if _short(t.get("name", "")) == short:
            return t["name"]
    return None


def _blocks(content):
    return content if isinstance(content, list) else [{"type": "text", "text": content or ""}]


def _text_of(block_content):
    if isinstance(block_content, str):
        return block_content
    return "".join(b.get("text", "") for b in block_content or [] if isinstance(b, dict) and b.get("type") == "text")


def _strip_reminders(text):
    return re.sub(r"<system-reminder>.*?</system-reminder>", "", text or "", flags=re.S).strip()


def _json(text):
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else {"text": text}
    except (TypeError, ValueError):
        return {"text": text}


def message(model, content, usage_in=0):
    """An Anthropic Messages response."""
    stop = "tool_use" if any(b["type"] == "tool_use" for b in content) else "end_turn"
    return {"id": "msg_" + uuid.uuid4().hex[:24], "type": "message", "role": "assistant", "model": model,
            "content": content, "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": usage_in, "output_tokens": sum(len(json.dumps(b)) // 4 for b in content)}}


def sse(msg):
    """The same message as Claude Code's streaming events."""
    def ev(kind, data):
        return f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()
    head = dict(msg, content=[], stop_reason=None, usage={"input_tokens": msg["usage"]["input_tokens"],
                                                          "output_tokens": 1})
    out = [ev("message_start", {"type": "message_start", "message": head})]
    for i, b in enumerate(msg["content"]):
        if b["type"] == "text":
            out.append(ev("content_block_start", {"type": "content_block_start", "index": i,
                                                  "content_block": {"type": "text", "text": ""}}))
            out.append(ev("content_block_delta", {"type": "content_block_delta", "index": i,
                                                  "delta": {"type": "text_delta", "text": b["text"]}}))
        else:
            out.append(ev("content_block_start", {"type": "content_block_start", "index": i, "content_block":
                                                  {"type": "tool_use", "id": b["id"], "name": b["name"], "input": {}}}))
            out.append(ev("content_block_delta", {"type": "content_block_delta", "index": i, "delta":
                                                  {"type": "input_json_delta",
                                                   "partial_json": json.dumps(b["input"], ensure_ascii=False)}}))
        out.append(ev("content_block_stop", {"type": "content_block_stop", "index": i}))
    out.append(ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": msg["stop_reason"],
                                                                       "stop_sequence": None},
                                    "usage": {"output_tokens": msg["usage"]["output_tokens"]}}))
    out.append(ev("message_stop", {"type": "message_stop"}))
    return b"".join(out)


def _tool_use(name, inp):
    return {"type": "tool_use", "id": "toolu_" + uuid.uuid4().hex[:24], "name": name, "input": inp}


def _text(t):
    return {"type": "text", "text": t}


# ---------------------------------------------------------------- Muse: today's product
def muse_body(j):
    """Muse sees today's file_ask (spec, no question); mid-chat system messages become user text (cacheable)."""
    for t in j.get("tools") or []:
        if _short(t.get("name", "")) == "file_ask":
            sch = t.get("input_schema") or {}
            (sch.get("properties") or {}).pop("question", None)
            (sch.get("properties") or {}).pop("pipeline", None)
            sch["required"] = ["file", "spec"]
    msgs = j.get("messages")
    if isinstance(msgs, list) and any(isinstance(m, dict) and m.get("role") == "system" for m in msgs):
        out = []
        for m in msgs:
            role = "user" if m.get("role") == "system" else m.get("role")
            c = list(_blocks(m.get("content")))
            if out and out[-1]["role"] == role:
                out[-1]["content"] += c
            else:
                out.append({**m, "role": role, "content": c})
        j["messages"] = out
    return j


# ---------------------------------------------------------------- the 9B: the E7 winner, on a lean prompt
NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def _nums(text):
    out = set()
    for n in NUM.findall(text or ""):
        try:
            v = float(n.replace(",", ""))
            out.add(str(int(v)) if v.is_integer() else str(v))
        except ValueError:
            pass
    return out


def _lean_system():
    with open(os.path.join(os.path.dirname(HERE), "idli", "CLAUDE-9b.md")) as f:
        text = re.sub(r"<!--.*?-->\s*", "", f.read(), flags=re.S)
    return ("You are the assistant in Idli, a desktop app. The user sees your replies in a chat and clicks cards you "
            "show with AskUserQuestion. Today is " + time.strftime("%Y-%m-%d") + ".\n\nInstructions from the workspace "
            "(CLAUDE.md):\n\n" + text)


def _nine_tools(tools):
    keep = []
    for t in tools or []:
        short = _short(t.get("name", ""))
        if t.get("name") != "AskUserQuestion" and short not in TWELVE:
            continue
        sch = json.loads(json.dumps(t.get("input_schema") or {"type": "object", "properties": {}}))
        desc = t.get("description", "")
        if short == "file_ask":
            props = sch.get("properties") or {}
            sch["properties"] = {k: props[k] for k in ("file", "question", "chart") if k in props}
            sch["required"] = ["file", "question"]
            desc = ("Answer a question about an opened file. Pass `question`: the person's question in their words "
                    "(add what 'that', 'those' or 'there' refers to if it isn't in the question). The spec is built for "
                    "you and the numbers come from the data; the form tab shows the same answer. For a graph, also "
                    "chart=true.")
        keep.append({"type": "function", "function": {"name": t["name"], "description": desc[:1500],
                                                      "parameters": sch}})
    return keep


def _to_openai(messages):
    out = []
    for m in messages:
        if m.get("role") == "system":
            out.append({"role": "user", "content": _strip_reminders(_text_of(m.get("content")))})
            continue
        if m["role"] == "assistant":
            text, calls = [], []
            for b in _blocks(m.get("content")):
                if b.get("type") == "text":
                    text.append(b["text"])
                elif b.get("type") == "tool_use":
                    calls.append({"id": b["id"], "type": "function", "function": {
                        "name": b["name"], "arguments": json.dumps(b.get("input") or {}, ensure_ascii=False)}})
            am = {"role": "assistant", "content": "\n".join(text) or None}
            if calls:
                am["tool_calls"] = calls
            out.append(am)
            continue
        texts = []
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_result":
                out.append({"role": "tool", "tool_call_id": b["tool_use_id"],
                            "content": _strip_reminders(_text_of(b.get("content"))) or "(no output)"})
            elif b.get("type") == "text":
                t = _strip_reminders(b["text"])
                if t:
                    texts.append(t)
        if texts:
            out.append({"role": "user", "content": "\n".join(texts)})
    return out


def _nine_call(messages, tools):
    body = {"model": NINE_MODEL, "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 4096,
            "temperature": 0.6}
    req = urllib.request.Request(NINE_URL + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"the 9B said {e.code}: {e.read().decode(errors='replace')[:300]}") from None


def _card_guard(messages):
    """A tool in this turn handed over a card to show, and no AskUserQuestion came after it."""
    last, shown = None, False
    for m in messages:
        if m["role"] == "user":
            last, shown = None, False
        elif m["role"] == "tool":
            r = _json(m["content"])
            if isinstance(r.get("card"), dict) and "AskUserQuestion" in str(r.get("then", "")):
                last, shown = r, False
        elif m["role"] == "assistant" and any(c["function"]["name"] == "AskUserQuestion"
                                              for c in m.get("tool_calls") or []):
            shown = True
    return last if last is not None and not shown else None


def nine(j, variant=None, pre=None, check=None):
    """The 9B runs the chat the way the E7 eval loop ran it. variant (careful / auto, the grounded modes): file_ask
    gets pipeline=<variant>, and chart_request is not offered (no "ask Claude" in these chats). pre(msgs) may edit
    the chat before the 9B reads it; check(text, msgs) may send the 9B back once with a reason."""
    msgs = [{"role": "system", "content": _lean_system()}] + _to_openai(j.get("messages") or [])
    if pre:
        msgs = pre(msgs)
    tools = _nine_tools(j.get("tools"))
    if variant:
        drop = {"chart_request"} | ({"chart_show"} if variant == "auto" else set())
        tools = [t for t in tools if _short(t["function"]["name"]) not in drop]
    asked = set()  # file_ask questions already answered since the person last spoke
    for m in reversed(msgs):
        if m["role"] == "user":
            break
        for c in m.get("tool_calls") or []:
            if _short(c["function"]["name"]) == "file_ask":
                asked.add((_json(c["function"]["arguments"]).get("question") or "").strip().lower())
    if not tools:  # Claude Code's side requests (titles, summaries): no tools, answer plainly
        tools = None
    nudged = set()
    usage_in = 0
    for _ in range(3):
        resp = _nine_call(msgs, tools) if tools else _nine_call(msgs, [])
        usage_in = (resp.get("usage") or {}).get("prompt_tokens", 0)
        msg = resp["choices"][0]["message"]
        text = re.sub(r"<think>.*?</think>", "", msg.get("content") or "", flags=re.S).strip()
        calls = msg.get("tool_calls") or []
        again = [c for c in calls if variant and _short(c["function"]["name"]) == "file_ask" and
                 (_json(c["function"].get("arguments") or "{}").get("question") or "").strip().lower() in asked]
        if again and "again" not in nudged:
            nudged.add("again")
            msgs += [{"role": "assistant", "content": text or None},
                     {"role": "user", "content": "Idli check: you already asked file_ask that, and its answer is above. "
                                                 "Reply to the person now from that answer."}]
            continue
        if calls or not tools:
            break
        why = None
        card = _card_guard(msgs)
        if card is not None and "card" not in nudged:
            nudged.add("card")
            why = ("Idli check: a tool returned a card for the user, but you didn't show it. Call AskUserQuestion now "
                   "with exactly that `card` (its questions and options as they are). Don't write its options as text.")
        else:
            allowed = set()
            for m in msgs:
                if m["role"] in ("user", "tool") and isinstance(m.get("content"), str):
                    allowed |= _nums(m["content"])
                for c in m.get("tool_calls") or []:
                    allowed |= _nums(c["function"]["arguments"])
            bad = [n for n in _nums(text) - allowed if not re.fullmatch(r"[0-9]", n)]
            if bad and "numbers" not in nudged:
                nudged.add("numbers")
                why = ("Idli check: these numbers in your reply didn't come from a tool: " + ", ".join(sorted(bad)[:5])
                       + ". Idli never works out numbers itself. Write the reply again with only numbers from tool "
                       "answers (call file_ask if you need another one).")
        if not why and check and "check" not in nudged:
            why = check(text, msgs)
            if why:
                nudged.add("check")
        if not why:
            break
        msgs += [{"role": "assistant", "content": text or None}, {"role": "user", "content": why}]
    content = [_text(text)] if text else []
    for c in calls:
        try:
            args = json.loads(c["function"].get("arguments") or "{}")
        except ValueError:
            args = {}
        name = c["function"]["name"]
        if name == "AskUserQuestion" and not _tool_card_in_turn(j.get("messages") or []):
            # tool_cards_only (E6/E7): a card only when a tool handed one over; otherwise ask in plain text
            q = (args.get("questions") or [{}])[0] if isinstance(args.get("questions"), list) else {}
            content.append(_text(str(q.get("question") or "")))
            continue
        if _short(name) == "teach_send" and not _said_yes_to_send(j.get("messages") or []):
            # consent is code's: a copy goes to Claude only right after a yes on teach_file's card
            again = _last_teach_card(j.get("messages") or [])
            content = [b for b in content if b["type"] != "text"]
            content.append(_tool_use("AskUserQuestion", again) if again else
                           _text("Shall I send a copy with fake values to Claude? Say yes and I'll show the card."))
            break
        args = args if isinstance(args, dict) else {}
        if variant and _short(name) == "file_ask":
            args = {k: v for k, v in args.items() if k in ("file", "question", "chart", "tab")}
            args["pipeline"] = variant
        content.append({"type": "tool_use", "id": c.get("id") or "toolu_" + uuid.uuid4().hex[:24], "name": name,
                        "input": args})
    if not content:
        content = [_text("…")]
    return message(j.get("model", "idli-9b"), content, usage_in)


def _said_yes_to_send(messages):
    """Was the last thing the person did a "Yes, send and switch" on a card?"""
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_result" and '="Yes, send and switch"' in _text_of(b.get("content")):
                return True
        if any(b.get("type") == "text" and _strip_reminders(b.get("text")) for b in _blocks(m.get("content"))):
            return False
    return False


def _last_teach_card(messages):
    for m in reversed(messages):
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_result":
                r = _json(_strip_reminders(_text_of(b.get("content"))))
                if r.get("request_id") and isinstance(r.get("card"), dict):
                    return r["card"]
    return None


def _tool_card_in_turn(messages):
    """Did a tool in this turn (since the person last typed) hand over a card?"""
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        bl = _blocks(m.get("content"))
        if any(b.get("type") == "text" and _strip_reminders(b.get("text")) for b in bl) and \
                not any(b.get("type") == "tool_result" for b in bl):
            return False
        for b in bl:
            if b.get("type") == "tool_result":
                r = _json(_text_of(b.get("content")))
                if isinstance(r.get("card"), dict) or isinstance(r.get("start_card"), dict):
                    return True
    return False


# ---------------------------------------------------------------- Steam: code runs the chat
LINK = re.compile(r"https?://(?:docs|drive)\.google\.com/\S+")
READY = re.compile(r"(?i)\b(ready|done|fixed|finished)\b")
CHART_WORDS = re.compile(r"(?i)\b(chart|graph|plot|picture|visuali[sz]e|show me)\b")
GREETING = re.compile(r"(?i)^\s*(hi|hello|hey|start|namaste|good (morning|afternoon|evening))\b[\s!.]*$")
ASK_LINK = "Paste the file's link: open it in Google Drive or Sheets and copy the address from the top of the tab."


def _card_answers(card, text):
    """Claude Code's AskUserQuestion result → [answer per question], using the questions we sent."""
    qs = [q.get("question", "") for q in (card or {}).get("questions") or []]
    starts = [text.find('"' + q + '"="') for q in qs]
    out = []
    for i, q in enumerate(qs):
        s = starts[i]
        if s < 0:
            out.append(None)
            continue
        s += len(q) + 4
        ends = [x for x in starts[i + 1:] if x > s]
        e = (ends[0] - 2) if ends else text.find(". You can now continue", s)
        if e < 0:  # newer Claude Code: '"q"="answer". Read the answers carefully ...'
            m = re.search(r'"(\.\s|,\s*"|\s*$)', text[s:])
            e = s + m.start() if m else -1
        out.append(text[s:e].rstrip('"').strip() if e > 0 else text[s:].strip())
    return out


def _events(messages):
    """The chat as a list of ("said", text) and ("tool", short name, input, result) in order."""
    uses, ev = {}, []
    for m in messages:
        if m.get("role") == "assistant":
            for b in _blocks(m.get("content")):
                if b.get("type") == "tool_use":
                    uses[b["id"]] = (b["name"], b.get("input") or {})
        elif m.get("role") in ("user", "system"):
            for b in _blocks(m.get("content")):
                if b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                    name, inp = uses[b["tool_use_id"]]
                    raw = _text_of(b.get("content"))
                    res = {"text": raw} if name == "AskUserQuestion" else _json(_strip_reminders(raw))
                    ev.append(("tool", _short(name), inp, res))
                elif b.get("type") == "text":
                    t = _strip_reminders(b.get("text"))
                    if t and m.get("role") == "user":
                        ev.append(("said", t))
    return ev


QUESTION = re.compile(r"(?i)\?|\b(how|what|which|who|where|when|why|average|mean|total|sum|count|share|percent|"
                      r"compare|list|show|chart|graph|plot|trend|per|by)\b")


def _question_in(t):
    """A question typed with the link ("how many trees per plot? <link>"), without the link and "open <file> at"."""
    rest = LINK.sub("", t)
    rest = re.sub(r"(?i)^\s*(please\s+)?(open|load|use|check|clean|analy[sz]e)\b[^?]*?\b(at|from|here)\s*[:,-]?\s*$", "",
                  rest.strip())
    rest = rest.strip(" .,:;-")
    return rest if len(rest.split()) >= 3 and QUESTION.search(rest) else None


def _is_copy(f):
    return "Idli working copy" in str(f or "")


class _State:
    def __init__(self, ev):
        self.original = self.active = None
        self.goal = "analyse"
        self.pending_q = None      # a question typed with the link, answered once the file is open
        self.last_q = None         # the last question asked of the form
        self.waiting = False       # "Not yet" / "Stay here": fixing the copy in Drive
        self.origin = None         # the tool result whose card is showing
        self.charts = []
        for e in ev:
            if e[0] == "said":
                t = e[1]
                if LINK.search(t):
                    self.pending_q = _question_in(t)
                    if re.search(r"(?i)\b(clean|mistake|check|fix)", t):
                        self.goal = "clean"
                continue
            _, name, inp, res = e
            if name in ("file_get", "file_open") and res.get("file"):
                f = res["file"]
                if _is_copy(f):
                    self.active = f
                else:
                    self.original = self.active = f
                if inp.get("goal"):
                    self.goal = inp["goal"]
            elif name == "working_copy_ready" and res.get("file"):
                self.active = res["file"]
                self.waiting = False
            elif name == "file_ask":
                self.last_q = inp.get("question") or self.last_q
                if res.get("answer"):
                    self.pending_q = None
            elif name == "AskUserQuestion":
                ans = (_card_answers(inp, res.get("text", "")) or [None])[0] or ""
                if ans in ("Clean up a file",):
                    self.goal = "clean"
                elif ans in ("Analyse a file",):
                    self.goal = "analyse"
                elif ans in ("No, analyse the original", "Use the original"):
                    self.active = self.original
                elif ans in ("Not yet", "Stay here"):
                    self.waiting = True
                elif ans in ("Continue with analysis", "Use the checked copy (Recommended)", "Analyse it now"):
                    self.waiting = False
            if isinstance(res, dict) and (isinstance(res.get("card"), dict) or isinstance(res.get("start_card"), dict)):
                self.origin = res
            if isinstance(res, dict) and res.get("charts") and isinstance(res["charts"], list):
                self.charts = [c["id"] for c in res["charts"] if isinstance(c, dict) and c.get("id")]


def _after_say(say, key):
    """The part of a tool's say_to_user that is for the person, after `key` ("Then say: ...")."""
    i = (say or "").find(key)
    return say[i + len(key):].strip() if i >= 0 else ""


def steam(j):
    tools = j.get("tools") or []
    model = j.get("model", "idli-steam")
    T = lambda short: _tool_name(tools, short)  # noqa: E731
    if not T("file_get"):  # Claude Code's side requests (titles, summaries): nothing to run
        return message(model, [_text("Idli")])
    ev = _events(j.get("messages") or [])
    st = _State(ev)

    def call(short, **inp):
        return message(model, [_tool_use(T(short), inp)])

    def say(text):
        return message(model, [_text(text)])

    def card(c):
        return message(model, [_tool_use("AskUserQuestion", c)])

    def ask(question, file=None):
        file = file or st.active
        chart = bool(CHART_WORDS.search(question))
        return call("file_ask", file=file, question=question, **({"chart": True} if chart else {}))

    def start_or_question(res):
        """The file is open on the start card: answer the question they typed with the link, if any."""
        if st.pending_q and res.get("file"):
            return ask(st.pending_q, res["file"])
        return card(res["start_card"]) if res.get("start_card") else say("What would you like to know?")

    if not ev:
        return call("start") if T("start") else say(ASK_LINK)
    last = ev[-1]

    # ---- the person typed something
    if last[0] == "said":
        t = last[1]
        if t.startswith("Teaching finished"):
            f = st.original or st.active
            return call("file_open", file=f, goal=st.goal) if f else say(ASK_LINK)
        if t.startswith("Claude finished"):
            m = re.search(r"charts=(\[[^\]]*\])", t)
            ids = json.loads(m.group(1)) if m else []
            return call("chart_show", file=st.active, charts=ids) if st.active and ids else say(t)
        link = LINK.search(t)
        if link:
            goal = "clean" if re.search(r"(?i)\b(clean|mistake|check|fix)", t) else st.goal
            return call("file_get", link=link.group(0).rstrip(").,"), goal=goal)
        if not st.active:
            if GREETING.match(t) and T("start"):
                return call("start")
            return say(ASK_LINK)
        if st.waiting and READY.search(t) and st.original:
            return call("working_copy", file=st.original)
        if re.search(r"(?i)\bask claude\b", t) and st.last_q:
            return call("chart_request", file=st.active, question=st.last_q)
        if re.search(r"(?i)^\s*suggest analyses\s*$", t):
            return call("chart_request", file=st.active, question="")
        return ask(t)

    _, name, inp, res = last
    err = res.get("error") if isinstance(res, dict) else None

    # ---- a card was answered
    if name == "AskUserQuestion":
        answers = _card_answers(inp, res.get("text", ""))
        a = (answers or [None])[0]
        o = st.origin or {}
        f = st.active
        if a is None:  # dismissed, or not an answer
            return say("OK. Tell me what you'd like to do next.")
        if a in ("Clean up a file", "Analyse a file"):
            return say(ASK_LINK)
        if a == "Yes, upload a checked copy (Recommended)":
            return call("working_copy", file=st.original, **({"fresh": True} if "fresh=true" in str(o.get("then"))
                                                            else {}))
        if a in ("No, analyse the original", "Use the original", "Analyse it now"):
            return start_or_question(o)
        if a in ("Continue with analysis", "Use the checked copy (Recommended)"):
            return call("working_copy_ready", file=st.original)
        if a in ("Not yet", "Stay here"):
            return say("Fine. Fix what matters in the copy, and say \"ready\" when you want to carry on.")
        if a == "Open my working copy":
            return call("working_copy", file=st.original)
        if a == "Make a fresh copy":
            return call("working_copy", file=st.original, fresh=True)
        if a == "I have a question":
            return say("What would you like to know?")
        if a == "Suggest analyses":
            return call("chart_request", file=f, question="")
        if a == "Show the saved charts":
            return call("chart_show", file=f, charts=st.charts)
        if a == "Yes, send and switch" and o.get("request_id"):
            labels = [x.strip() for x in (answers[1] if len(answers) > 1 and answers[1] else "").split(",")
                      if x.strip() and not x.strip().lower().startswith("none")]
            return call("teach_send", request_id=o["request_id"], share_labels=labels)
        if a == "Yes, teach the new layout":
            return call("teach_file", file=st.original or f, question=st.pending_q or "Learn the new layout")
        if a == "Not now":
            return say("Nothing was sent. Ask again any time." if o.get("request_id") else "OK, nothing changes.")
        # typed into the card's "Other" box: treat it as a message
        ev.append(("said", a))
        return steam({**j, "messages": (j.get("messages") or []) + [{"role": "user", "content": a}]})

    # ---- a tool came back
    if err:
        then = res.get("then") or ""
        if name == "file_ask":
            return say(f"I couldn't answer that from the form ({err}). Try asking it another way.")
        return say(str(err) + ((" " + then) if then and "Ask the user" in then else ""))
    if name == "start":
        return card(res["card"])
    if name in ("file_get", "file_open", "working_copy_ready"):
        if res.get("downloaded") is False:
            return say(res.get("say_to_user") or "I couldn't download the file.")
        if res.get("known") is False:
            return call("teach_file", file=res["file"], question=st.pending_q or "Help me understand this file")
        if res.get("layout") == "changed":
            return card({"questions": [{"header": "Teach", "multiSelect": False, "question": res.get("say_to_user"),
                                        "options": [{"label": "Yes, teach the new layout",
                                                     "description": "Claude learns it from a copy with fake values"},
                                                    {"label": "Not now", "description": "Nothing is sent"}]}]})
        c = res.get("card")
        if c:
            labels = [o.get("label") for q in c.get("questions") or [] for o in q.get("options") or []]
            if "I have a question" in labels and st.pending_q:
                return ask(st.pending_q, res["file"])
            return card(c)
        return say(res.get("say_to_user") or "The file is open.")
    if name == "working_copy":
        if res.get("card"):
            return card(res["card"])
        return say(res.get("say_to_user") or "")
    if name in ("teach_file", "chart_request"):
        return card(res["card"]) if res.get("card") else say(res.get("say_to_user") or "")
    if name == "teach_send":
        if not res.get("started"):
            return say("Couldn't start Claude.")
        return say("Sent a copy with fake values to Claude" + (
            ", and switched there to answer its questions." if res.get("switched") else
            f"; open the Claude workspace (chat '{res.get('teach_chat', '')}') to answer its questions.")
            + " This chat carries on when teaching is done.")
    if name == "file_ask":
        if res.get("cannot"):
            q = inp.get("question") or st.last_q or ""
            if res.get("route") == "chart_request" or "chart_request" in str(res.get("then")):
                return call("chart_request", file=inp.get("file") or st.active, question=q)
            return call("teach_file", file=inp.get("file") or st.active, question=q, missing=res["cannot"])
        s = res.get("say_to_user") or ""
        parts = []
        if res.get("chart_markdown"):
            parts.append(res["chart_markdown"])
        parts.append(res.get("answer") or "")
        tail = ["The form tab shows it too." if res.get("form_updated") else f"Form: {res.get('form_link', '')}"]
        if "Rows that failed checks are included." in s:
            tail.append("Rows that failed checks are included.")
        for key in ("Mention: ", " Say: "):
            if key in s:
                tail.append(_after_say(s, key).split(" Mention: ")[0])
        if res.get("chart_markdown"):
            tail.append("For a fuller chart, say 'ask Claude' and I'll send Claude a copy with fake values to design it.")
        parts.append(" ".join(x for x in tail if x))
        return say("\n\n".join(p for p in parts if p))
    if name == "chart_show":
        parts = [res.get("chart_markdown") or ""]
        if res.get("errors"):
            parts.append("Some charts didn't draw: " + "; ".join(res["errors"]))
        note = _after_say(res.get("say_to_user"), "Then say: ")
        parts.append(((note + " ") if note else "") + "They're also on the dashboard tab.")
        return say("\n\n".join(p for p in parts if p))
    if name == "show_dashboard":
        return say("" if res.get("shown") else res.get("say_to_user", ""))
    return say(res.get("say_to_user") or "Done.")


def respond(j):
    """Steam, 9B, or a grounded 9B mode: the Anthropic Messages response for one Claude Code request."""
    pre = privacy_route(j)
    if pre:
        return pre
    mode = mode_of(j.get("model"))
    if mode == "steam":
        return steam(j)
    if mode == "careful":
        return careful_chat(j)
    if mode == "auto":
        return auto_chat(j)
    return nine(j)


# ---------------------------------------------------------------- the grounded 9B modes (2026-11-13)
# benchmarks/runs/2026-11-13-grounded-9b: two proposals for the Yerawada failure, built independently.
def _lib(name):
    import sys
    root = os.path.dirname(HERE)
    if root not in sys.path:
        sys.path.insert(0, root)
    import importlib
    return importlib.import_module("lib." + name)


def _file_ask_results(messages):
    """[(input, result)] for every file_ask in the chat, oldest first."""
    uses, out = {}, []
    for m in messages:
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_use":
                uses[b["id"]] = (b["name"], b.get("input") or {})
            elif b.get("type") == "tool_result" and _short(uses.get(b.get("tool_use_id"), ("",))[0]) == "file_ask":
                out.append((uses[b["tool_use_id"]][1], _json(_strip_reminders(_text_of(b.get("content"))))))
    return out


def _last_typed(messages):
    """The person's last typed message, if it is the latest thing in the chat."""
    if not messages or messages[-1].get("role") != "user":
        return None
    bl = _blocks(messages[-1].get("content"))
    if any(b.get("type") == "tool_result" for b in bl):
        return None
    t = " ".join(_strip_reminders(b.get("text", "")) for b in bl if b.get("type") == "text").strip()
    return t or None


def _last_assistant_text(messages):
    for m in reversed(messages[:-1]):
        if m.get("role") == "assistant":
            t = " ".join(b.get("text", "") for b in _blocks(m.get("content")) if b.get("type") == "text").strip()
            if t:
                return t
    return ""


def _latest_tool(messages):
    """(short name, input, result) when the chat's latest message is a tool result."""
    if not messages or messages[-1].get("role") != "user":
        return None
    res = [b for b in _blocks(messages[-1].get("content")) if b.get("type") == "tool_result"]
    if not res:
        return None
    uses = {}
    for m in messages:
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_use":
                uses[b["id"]] = (b["name"], b.get("input") or {})
    name, inp = uses.get(res[-1].get("tool_use_id"), ("", {}))
    raw = _strip_reminders(_text_of(res[-1].get("content")))
    return _short(name), inp, ({"text": raw} if name == "AskUserQuestion" else _json(raw))


TABLE = re.compile(r"(?i)\b(as a table|in a table|table instead|show (me )?(a |the )?table|put it in a table)\b")
PREVIOUS = re.compile(r"(?i)\b(previous|last|earlier|before|first) (chart|graph|one)\b|\bon the previous\b")


def careful_chat(j):
    """Careful: code answers what it can from the manifests in the chat; the 9B parses everything else."""
    C, R = _lib("careful"), _lib("receipt")
    msgs = j.get("messages") or []
    model = j.get("model", "idli-9b-careful")
    tools = j.get("tools") or []
    asks = [(i, r) for i, r in _file_ask_results(msgs) if isinstance(r.get("manifest"), dict)]
    mans = [r["manifest"] for _, r in asks]
    latest = _latest_tool(msgs)
    if latest and latest[0] == "file_ask" and (latest[1] or {}).get("pipeline") == "careful":
        res = latest[2]
        if isinstance(res.get("card"), dict):
            return message(model, [_tool_use("AskUserQuestion", res["card"])])
        if res.get("reply"):
            return message(model, [_text(res["reply"])])
        if res.get("error"):
            return message(model, [_text(f"I couldn't answer that from the form ({res['error']}). Try asking it "
                                         "another way.")])
    head = (latest[1].get("questions") or [{}])[0].get("header") if latest and latest[0] == "AskUserQuestion" else None
    if head in ("Which figure", "Which view"):
        ans = (_card_answers(latest[1], latest[2].get("text", "")) or [None])[0]
        last_in = next((i for i, r in reversed(_file_ask_results(msgs)) if r.get("card")), {})
        if ans and last_in.get("file") and _tool_name(tools, "file_ask"):
            word = "figure: " if head == "Which figure" else "view: "
            return message(model, [_tool_use(_tool_name(tools, "file_ask"),
                                             {"file": last_in["file"], "question": word + ans,
                                              "pipeline": "careful", "send": "no"})])  # its own card: stays local
    said = _last_typed(msgs)
    if said and mans:
        if R.PUSHBACK.search(said):
            return message(model, [_text(C.verify_chart(mans[-1], said, _last_assistant_text(msgs)))])
        if R.READ_CHART.search(said):
            prev = PREVIOUS.search(said) and len(mans) > 1
            return message(model, [_text(C.read_chart(mans[-2] if prev else mans[-1],
                                                      "previous" if prev else "active"))])
        if TABLE.search(said):
            return message(model, [_text(C.as_table(mans[-1]))])
    # a question about the open file goes to the form in the person's own words (the 9B parses it there); the chat
    # 9B only handles the rest (links, greetings, cards it was handed)
    f = _open_file(msgs)
    if said and f and not LINK.search(said) and QUESTION.search(said) and _tool_name(tools, "file_ask"):
        return message(model, [_tool_use(_tool_name(tools, "file_ask"),
                                         {"file": f, "question": said, "pipeline": "careful"})])
    return nine(j, variant="careful")


def _open_file(messages):
    """The file this chat is working on: the last one file_get / file_open / working_copy_ready / file_ask used."""
    uses, f = {}, None
    for m in messages:
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_use":
                uses[b["id"]] = (_short(b["name"]), b.get("input") or {})
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                name, inp = uses[b["tool_use_id"]]
                r = _json(_strip_reminders(_text_of(b.get("content"))))
                if name in ("file_get", "file_open", "working_copy_ready") and r.get("file") and r.get("known") is not False:
                    f = r["file"]
                elif name == "file_ask" and inp.get("file"):
                    f = inp["file"]
    return f


AUDIT = ("SYSTEM AUDIT: the person reports a difference between your explanation and the chart on screen. Do NOT "
         "defend your previous answer. Read render_receipt below: say exactly what is on screen (total_bars_on_screen, "
         "the axes, categories_shown) and anything in omitted_from_chart. If the person's description is wrong and "
         "the receipt shows more, say what the receipt shows. Never mention or offer other AI models.")
FLAG = "[PREVIOUS EXPLANATION FLAGGED FOR VISUAL DISCREPANCY — DO NOT REPEAT]"


def auto_chat(j):
    """Auto: the 9B talks, with the render receipt as its only source about the chart."""
    R = _lib("receipt")
    msgs = j.get("messages") or []
    asks = [r for _, r in _file_ask_results(msgs) if isinstance(r.get("render_receipt"), dict)]
    rc = asks[-1]["render_receipt"] if asks else None
    said = _last_typed(msgs)
    push = bool(said and rc and R.PUSHBACK.search(said))
    read = bool(said and rc and R.READ_CHART.search(said))

    def pre(om):
        if not rc or not (push or read):
            return om
        out = list(om)
        if push:  # mask what was said about the chart since the last answer: it may be wrong
            last_tool = max((i for i, m in enumerate(out) if m["role"] == "tool"), default=-1)
            for i in range(last_tool + 1, len(out)):
                if out[i]["role"] == "assistant" and out[i].get("content"):
                    out[i] = {**out[i], "content": FLAG}
        note = (AUDIT if push else "Answer about the chart using only this render_receipt (what is actually on "
                "screen):") + "\nrender_receipt: " + json.dumps(rc, ensure_ascii=False) + "\nIn words: " + R.describe(rc)
        out.append({"role": "user", "content": note})
        return out

    def check(text, m):
        if R.mentions_escalation(text):
            return "Idli check: don't mention or offer other AI models. Write the reply again without that."
        if rc:
            bad = R.check_reply(text, rc)
            if bad:
                return ("Idli check: your reply contradicts the render receipt (" + "; ".join(bad) + "). Write it again "
                        "using only render_receipt: " + R.describe(rc))
        return None

    msg = nine(j, variant="auto", pre=pre, check=check)
    for b in msg["content"]:
        if b["type"] == "text":
            b["text"] = R.scrub_escalation(b["text"]) if R.mentions_escalation(b["text"]) else b["text"]
    return msg


# ---------------------------------------------------------------- privacy, per file (2026-11-14), every model
# When a file opens, ask once how Claude may see it (fake copy, or masked with or without a check on each question).
# In mask mode a typed question goes to file_ask in the person's words; file_ask shows the masked question on a card
# ("Send to Claude") when review is "ask", has Claude plan it, and works the numbers out on this computer.
PRIV_HEAD, SEND_HEAD = "Claude & file", "Send to Claude"
PRIV_OPTS = [
    ("Fake copy (most private)", "Claude only ever sees made-up values. Your questions stay with the private model."),
    ("Masked, I check each question", "Claude sees your real columns with names, places and any column you pick "
     "(even income) turned into codes, e.g. Yerawada Ward -> PLACE_001. You approve each question before it goes."),
    ("Masked, automatic", "The same, without the check each time. The fastest and best answers."),
]


def _privacy_of(messages, f):
    """The latest privacy setting a tool result reported for file f."""
    pv = None
    for i, r in _file_results(messages):
        if (r.get("file") == f or i.get("file") == f) and isinstance(r.get("privacy"), dict):
            pv = r["privacy"]
        elif i.get("file") == f and isinstance(r.get("saved"), dict) and r["saved"].get("mode"):  # file_privacy
            pv = r["saved"]
    return pv


def _file_results(messages):
    uses, out = {}, []
    for m in messages:
        for b in _blocks(m.get("content")):
            if b.get("type") == "tool_use":
                uses[b["id"]] = (b.get("input") or {})
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                r = _json(_strip_reminders(_text_of(b.get("content"))))
                if isinstance(r, dict):
                    out.append((uses[b["tool_use_id"]], r))
    return out


def _asked(messages, head):
    return any(b.get("type") == "tool_use" and _short(b.get("name", "")) == "AskUserQuestion"
               and ((b.get("input") or {}).get("questions") or [{}])[0].get("header") == head
               for m in messages for b in _blocks(m.get("content")))


def privacy_route(j):
    msgs, tools, model = j.get("messages") or [], j.get("tools") or [], j.get("model", "")
    fa = _tool_name(tools, "file_ask")
    if not fa:
        return None
    latest = _latest_tool(msgs)
    if latest:
        name, inp, res = latest
        if name in ("file_get", "file_open", "working_copy_ready") and res.get("file") and _tool_name(tools, "file_privacy") \
                and (res.get("privacy") or {"mode": 1}).get("mode") is None and not _asked(msgs, PRIV_HEAD):
            return message(model, [_tool_use("AskUserQuestion", {"questions": [{
                "header": PRIV_HEAD, "multiSelect": False,
                "question": "Before we start: how may Claude (the smart model online) see this file?",
                "options": [{"label": a, "description": b} for a, b in PRIV_OPTS]}]})])
        if name == "AskUserQuestion" and (inp.get("questions") or [{}])[0].get("header") == PRIV_HEAD:
            ans = (_card_answers(inp, res.get("text", "")) or [""])[0] or ""
            f = _open_file(msgs)
            mode = "mask" if re.search(r"(?i)mask", ans) else "fake"
            review = "auto" if re.search(r"(?i)automatic|auto\b", ans) else "ask"
            if f:
                return message(model, [_tool_use(_tool_name(tools, "file_privacy"),
                                                 {"file": f, "mode": mode, "review": review})])
        if name == "file_privacy" and res.get("say_to_user"):
            return message(model, [_text(res["say_to_user"] + "\n\nWhat would you like to know about it?")])
        if name == "file_ask" and inp.get("question") and (isinstance(res.get("card"), dict) and
                                                          (res["card"].get("questions") or [{}])[0].get("header") == SEND_HEAD):
            return message(model, [_tool_use("AskUserQuestion", res["card"])])
        if name == "file_ask" and inp.get("question") and (res.get("privacy") or {}).get("mode") == "mask" \
                and res.get("reply") and inp.get("send") != "no":
            return message(model, [_text(res["reply"])])
        if name == "AskUserQuestion" and (inp.get("questions") or [{}])[0].get("header") == SEND_HEAD and fa:
            ans = (_card_answers(inp, res.get("text", "")) or [""])[0] or ""
            last = next((i for i, r in reversed(_file_ask_results(msgs)) if r.get("card")), {})
            yes = ans.lower().startswith("send")
            mode = mode_of(model)
            args = {"file": last.get("file"), "question": last.get("question"), "chart": True,
                    "send": "yes" if yes else "no"}
            if not yes and mode in ("careful", "auto"):
                args["pipeline"] = mode
            if yes or mode in ("careful", "auto") or mode == "nine":
                return message(model, [_tool_use(fa, args)])
            return None  # Muse answers it itself, on this computer
        return None
    said = _last_typed(msgs)
    f = _open_file(msgs)
    # "how is X worked out" is answered from the form's own definition: nothing to plan, nothing to send
    if said and f and fa and not LINK.search(said) and (_privacy_of(msgs, f) or {}).get("mode") == "mask" \
            and QUESTION.search(said) and not _lib("careful").DEFINE_WORDS.search(said):
        return message(model, [_tool_use(fa, {"file": f, "question": said, "chart": bool(CHART_WORDS.search(said))})])
    return None
