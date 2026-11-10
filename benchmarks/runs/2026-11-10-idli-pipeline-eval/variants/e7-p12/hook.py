"""E7 p12: the product's 12 tools with the split (see ../e7_common.py, mode today = split only)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import e7_common  # noqa: E402


def apply(mcp, tools):
    e7_common.apply(mcp, "today")
