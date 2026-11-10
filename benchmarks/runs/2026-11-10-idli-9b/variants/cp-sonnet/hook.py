"""Claude (claude-sonnet-5-5) plans the spec from redacted text; the local model executes (see ../claude_plans_common.py). Shape-only backtrack: True."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import claude_plans_common  # noqa: E402


def apply(mcp, tools):
    claude_plans_common.apply(mcp, "claude-sonnet-5-5", backtrack=True)
