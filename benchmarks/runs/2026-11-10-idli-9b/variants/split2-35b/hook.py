"""The split with or-qwen35-35b-a3b building the specs (see ../split_common.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import split_common  # noqa: E402


def apply(mcp, tools):
    split_common.apply(mcp, "or-qwen35-35b-a3b", prompt=split_common.PROMPT2)
