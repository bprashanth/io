"""Idli's MCP server for the Claude Code runs: the real cowork_mcp, with idli.py's fake Drive patched in, and a
variant's tool changes (variants/<v>/hook.py) applied.

  python harness/mcp_server.py <idli home> [variant]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idli  # noqa: E402

mcp = idli.setup(sys.argv[1])
if len(sys.argv) > 2 and sys.argv[2] != "base":
    import convo  # noqa: E402
    convo.apply_variant(mcp, sys.argv[2])
os.environ.setdefault("COWORK_LOG", os.path.join(sys.argv[1], "cowork.log"))
mcp.main()
