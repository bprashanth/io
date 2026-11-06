"""Probe Muse (llama.cpp) on the three wire protocols agent CLIs speak: Chat Completions,
Responses (Codex) and Anthropic Messages (Claude Code). Each request streams, offers one tool and
asks a question that needs it. Records status, event types, tool-call validity and timings.
Small max_tokens; the server is shared."""
import json, sys, time, urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8181"
MODEL = "muse-glimmer-30b"
Q = "What is the sum of the visits column in /data/visits.csv? Use the tool to run a command; do not guess."
TOOL_DESC = "Run a shell command and return its output"
SCHEMA = {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}

def stream(path, body, headers):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    t0 = time.time(); first = None; events = []; raw = []
    try:
        r = urllib.request.urlopen(req, timeout=180)
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()[:300]}
    ctype = r.headers.get("content-type")
    for line in r:
        line = line.decode("utf8", "replace").rstrip("\n")
        if not line:
            continue
        if first is None: first = time.time() - t0
        raw.append(line)
        if line.startswith("event:"): events.append(line[6:].strip())
        elif line.startswith("data:"):
            d = line[5:].strip()
            if d == "[DONE]": events.append("[DONE]"); continue
            try: j = json.loads(d)
            except Exception: continue
            if "type" in j and not any(line.startswith("event:") for line in raw[-2:-1]): events.append(j["type"])
    return {"status": r.status, "content_type": ctype, "first_byte_s": round(first or 0, 2),
            "total_s": round(time.time() - t0, 2), "events": sorted(set(events)), "raw": raw}

def chat():
    out = stream("/v1/chat/completions", {"model": MODEL, "stream": True, "max_tokens": 400,
        "messages": [{"role": "user", "content": Q}],
        "tools": [{"type": "function", "function": {"name": "shell", "description": TOOL_DESC, "parameters": SCHEMA}}]}, {})
    args = ""; name = None
    for l in out.get("raw", []):
        if not l.startswith("data:") or l.endswith("[DONE]"): continue
        try: j = json.loads(l[5:])
        except Exception: continue
        for c in j.get("choices", []):
            for tc in (c.get("delta") or {}).get("tool_calls") or []:
                f = tc.get("function") or {}
                name = f.get("name") or name; args += f.get("arguments") or ""
    return out, name, args

def responses():
    out = stream("/v1/responses", {"model": MODEL, "stream": True, "max_output_tokens": 400, "input": Q,
        "tools": [{"type": "function", "name": "shell", "description": TOOL_DESC, "parameters": SCHEMA}]}, {})
    name = None; args = ""
    for l in out.get("raw", []):
        if not l.startswith("data:"): continue
        try: j = json.loads(l[5:])
        except Exception: continue
        it = j.get("item") or {}
        if j.get("type") == "response.output_item.done" and it.get("type") == "function_call":
            name = it.get("name"); args = it.get("arguments", "")
    return out, name, args

def messages():
    out = stream("/v1/messages", {"model": MODEL, "stream": True, "max_tokens": 400,
        "messages": [{"role": "user", "content": Q}],
        "tools": [{"name": "shell", "description": TOOL_DESC, "input_schema": SCHEMA}]},
        {"x-api-key": "unused", "anthropic-version": "2023-06-01"})
    name = None; args = ""
    for l in out.get("raw", []):
        if not l.startswith("data:"): continue
        try: j = json.loads(l[5:])
        except Exception: continue
        if j.get("type") == "content_block_start" and (j.get("content_block") or {}).get("type") == "tool_use":
            name = j["content_block"].get("name")
        if j.get("type") == "content_block_delta" and (j.get("delta") or {}).get("type") == "input_json_delta":
            args += j["delta"].get("partial_json", "")
    return out, name, args

result = {"base": BASE, "model": MODEL, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
for label, fn in (("chat_completions", chat), ("responses", responses), ("anthropic_messages", messages)):
    out, name, args = fn()
    try: parsed = json.loads(args) if args else None
    except Exception: parsed = "INVALID_JSON"
    raw = out.pop("raw", [])
    open(f"{label}.sse.txt", "w").write("\n".join(raw))
    result[label] = {**out, "tool_name": name, "tool_args": parsed}
    print(label, json.dumps(result[label])[:300])
json.dump(result, open("probe-results.json", "w"), indent=1)
