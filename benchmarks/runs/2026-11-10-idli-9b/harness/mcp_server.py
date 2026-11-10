"""Idli's MCP server for the Claude Code runs: the real cowork_mcp, with idli.py's fake Drive patched in.

  python harness/mcp_server.py <idli home>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idli  # noqa: E402

mcp = idli.setup(sys.argv[1])
os.environ.setdefault("COWORK_LOG", os.path.join(sys.argv[1], "cowork.log"))
mcp.main()
