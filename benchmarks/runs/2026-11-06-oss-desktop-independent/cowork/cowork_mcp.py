#!/usr/bin/env python3
"""Co-work MCP server: the site plugins built in DIY mode, offered to the private model.

Loads only the sites enabled for this workspace (a `cowork.sites` file in the workspace folder,
one site per line, or COWORK_SITES=google,sheets; default: every site). Adds `report_gap`, so
the model reports a missing capability in a fixed form the user can paste into DIY mode,
instead of improvising. Dependency-free stdio MCP; site plugins may import their own libraries.

Dev: cowork_mcp.py --call <tool> '<json>'
"""
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.browser import NotSignedIn, log  # noqa: E402

SITES_DIR = os.path.join(HERE, "sites")


def site_meta(name):
    try:
        with open(os.path.join(SITES_DIR, name, "site.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"name": name}


def enabled_sites():
    names = os.environ.get("COWORK_SITES")
    if not names:
        try:
            with open(os.path.join(os.environ.get("COWORK_DATA_DIR") or os.getcwd(), "cowork.sites")) as f:
                names = ",".join(l.split("#")[0].strip() for l in f)
        except OSError:
            names = ""
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    present = sorted(d for d in os.listdir(SITES_DIR) if os.path.isfile(os.path.join(SITES_DIR, d, "tools.py")))
    return [n for n in (wanted or present) if n in present]


TOOLS, OWNER, LOAD_ERRORS = {}, {}, {}
for site in enabled_sites():
    try:
        mod = importlib.import_module(f"sites.{site}.tools")
    except Exception as e:  # a broken plugin must not take down the others
        LOAD_ERRORS[site] = f"{type(e).__name__}: {e}"
        log("LOAD", site, LOAD_ERRORS[site])
        continue
    for name, spec in mod.TOOLS.items():
        TOOLS[name] = spec
        OWNER[name] = site


def site_lines():
    out = []
    for s in enabled_sites():
        m = site_meta(s)
        t = m.get("last_test") or {}
        status = f"last test {t.get('result', 'never run')}" + (f" on {t['when']}" if t.get("when") else "")
        if s in LOAD_ERRORS:
            status = "failed to load"
        out.append(f"{s} ({m.get('covers', '')}; {status})")
    return out


def t_report_gap(wanted, tried="", site=""):
    tools = sorted(n for n in TOOLS if n != "report_gap")
    block = "\n".join([
        "=== CO-WORK GAP REPORT ===",
        f"wanted: {wanted}",
        f"site: {site or 'unknown'}",
        f"tried: {tried or 'nothing suitable'}",
        f"sites enabled: {'; '.join(site_lines()) or 'none'}",
        f"tools available: {', '.join(tools)}",
        "=== END ===",
    ])
    return {"gap_report": block,
            "tell_the_user": "Say plainly that you don't have a tool for this yet. Show the gap report exactly as "
                             "written, inside a code block, and tell the user: to add it, remove any personal "
                             "details from the report, then paste it into a DIY-mode chat."}


TOOLS["report_gap"] = (t_report_gap,
                       "Call this when the user asks for something none of your tools can do (or a tool says it "
                       "cannot). Not for a spreadsheet that has a form (file_open said known): use teach_file with "
                       "`missing` instead, so Claude can extend its form. Do not improvise or guess an answer instead. Describe what is needed in general "
                       "terms (the kind of action and data), not the user's personal data.",
                       {"wanted": {"type": "string", "description": "The missing capability, e.g. 'read the "
                                                                    "cells of a Google Sheet'"},
                        "tried": {"type": "string", "description": "Tools you tried and what they said"},
                        "site": {"type": "string"}}, ["wanted"])


def enabled_tools():
    """Optional allow-list for this workspace: a `cowork.tools` file (one tool per line) next to `cowork.sites`.
    A small model chooses better from fewer tools, so each chat gets only what its job needs."""
    try:
        with open(os.path.join(os.environ.get("COWORK_DATA_DIR") or os.getcwd(), "cowork.tools")) as f:
            return {l.split("#")[0].strip() for l in f} - {""}
    except OSError:
        return None


_ALLOWED = enabled_tools()
if _ALLOWED is not None:
    for _n in [n for n in TOOLS if n not in _ALLOWED]:
        del TOOLS[_n]


def call(name, args):
    try:
        return TOOLS[name][0](**args), False
    except NotSignedIn as e:
        return {"error": str(e), "tell_the_user": "Ask the user to sign in to this site in the workspace browser, "
                                                   "then try again."}, True
    except Exception as e:
        log("ERROR", name, repr(e))
        return {"error": f"{type(e).__name__}: {e}"[:400],
                "hint": "If no other tool can do this, call report_gap."}, True


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        if mid is None:
            continue
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}}, "serverInfo": {"name": "cowork", "version": "0.2"},
                "instructions": "Co-work tools for the sites this workspace uses: " + "; ".join(site_lines())
                                + ". Never send email or edit documents; draft and suggest only. When no tool "
                                  "fits, call report_gap."}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [
                {"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
                for n, (_, d, p, r) in TOOLS.items()]}})
        elif method == "tools/call":
            name, args = msg["params"]["name"], msg["params"].get("arguments") or {}
            t0 = time.time()
            out, err = call(name, args) if name in TOOLS else ({"error": f"unknown tool {name}"}, True)
            log("CALL", name, json.dumps(args)[:200], f"{time.time() - t0:.1f}s", "error" if err else "ok")
            res = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1, default=str)}]}
            if err:
                res["isError"] = True
            send({"jsonrpc": "2.0", "id": mid, "result": res})
        else:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--call":
        out, _ = call(sys.argv[2], json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}"))
        print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "--list":
        print("\n".join(f"{OWNER.get(n, 'core')}: {n}" for n in TOOLS), "\nload errors:", LOAD_ERRORS or "none")
    else:
        main()
