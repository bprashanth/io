"""E7 variants from the product as merged (oss-desktop-eval 94570b4: Idli gets 12 tools via cowork.tools).
  e7-product: exactly the product: its CLAUDE.md, its 12 tools, the model builds the form spec itself, no guards.
  e7-p12:     the same 12 tools with the 9B benchmark's split (file_ask takes the question) and guards.
Rerun after the product's CLAUDE.md or tool list changes."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COWORK = os.path.join(os.path.dirname(os.path.dirname(HERE)), "2026-11-06-oss-desktop-independent", "cowork")
sys.path.insert(0, os.path.join(COWORK, "desktop"))
src = open(os.path.join(COWORK, "desktop", "idli-bootstrap.py")).read()
tools = re.search(r'"Idli": (\[[^\]]*\])', src, re.S).group(1)
tools = json.loads(tools)
claude = open(os.path.join(COWORK, "idli", "CLAUDE.md")).read()

os.makedirs(os.path.join(HERE, "e7-product"), exist_ok=True)
json.dump(tools, open(os.path.join(HERE, "e7-product", "tools.json"), "w"))
open(os.path.join(HERE, "e7-product", "CLAUDE.md"), "w").write(claude)
open(os.path.join(HERE, "e7-product", "hook.py"), "w").write(
    '"""E7 product: the shipped tool list (tools.json) and CLAUDE.md, nothing else."""\n\n\ndef apply(mcp, tools):\n    pass\n')

split = open(os.path.join(HERE, "e7-today", "CLAUDE.md")).read()
ask_split = split[split.index("- Questions about an opened file:"):split.index("- If file_ask says the form can't answer:")]
p12 = claude[:claude.index("- Questions about an opened file:")] + ask_split + \
    claude[claude.index("- If the form can't give what they asked"):]
os.makedirs(os.path.join(HERE, "e7-p12"), exist_ok=True)
json.dump(tools, open(os.path.join(HERE, "e7-p12", "tools.json"), "w"))
open(os.path.join(HERE, "e7-p12", "CLAUDE.md"), "w").write(p12)
open(os.path.join(HERE, "e7-p12", "guards.json"), "w").write('{"card": true, "numbers": true}\n')
open(os.path.join(HERE, "e7-p12", "hook.py"), "w").write(
    '"""E7 p12: the product\'s 12 tools with the split (see ../e7_common.py, mode today = split only)."""\n'
    'import os, sys\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n'
    'import e7_common  # noqa: E402\n\n\ndef apply(mcp, tools):\n    e7_common.apply(mcp, "today")\n')
print(len(tools), tools)
