"""E7 hard (see ../e7_common.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import e7_common  # noqa: E402


def apply(mcp, tools):
    e7_common.apply(mcp, "hard")
