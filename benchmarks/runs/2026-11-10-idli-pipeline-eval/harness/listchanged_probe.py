"""E7 probe: does Claude Code pick up a changed MCP tool list in the middle of a chat (notifications/tools/list_changed)?

A minimal MCP stdio server: at first it lists only `phase_one`. Calling it switches the list to `phase_two` and sends
tools/list_changed. If Claude Code refreshes, the model can then call `phase_two` in the same chat.
  claude -p --mcp-config <json> "..."   (see listchanged_run.sh)
"""
import json
import sys

state = {"phase": 1}
LOG = sys.argv[1] if len(sys.argv) > 1 else None


def log(x):
    if LOG:
        with open(LOG, "a") as f:
            f.write(json.dumps(x) + "\n")


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def tools():
    name = "phase_one" if state["phase"] == 1 else "phase_two"
    return [{"name": name, "description": f"Step {state['phase']} of the probe. Call it.",
             "inputSchema": {"type": "object", "properties": {}}}]


for line in sys.stdin:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    log({"in": msg.get("method"), "id": msg.get("id")})
    mid, method = msg.get("id"), msg.get("method")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {"listChanged": True}}, "serverInfo": {"name": "probe", "version": "1"}}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": tools()}})
        log({"listed": [t["name"] for t in tools()]})
    elif method == "tools/call":
        name = msg["params"]["name"]
        if name == "phase_one":
            state["phase"] = 2
            send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text":
                  "Done. A new tool, phase_two, is now available: call it next."}]}})
            send({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})
        elif name == "phase_two":
            send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": "PHASE TWO REACHED"}]}})
        else:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool " + name}})
    elif mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
