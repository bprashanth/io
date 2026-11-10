"""E7 soft12 (see ../e7_common.py apply12)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import e7_common  # noqa: E402


def apply(mcp, tools):
    e7_common.apply(mcp, "soft12")
