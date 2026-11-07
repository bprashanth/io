"""Which account a site plugin should use.

COWORK_MODE=test (set by run_tests.py) uses the site's test account from accounts.local.json,
so tests never touch the user's real data. Otherwise (co-work) the plugin uses the account the
user is signed into in the workspace browser (`real`, default: the first signed-in account).

accounts.local.json is never committed:  {"google": {"test": "someone.test@gmail.com"}}
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def account(site, default=""):
    mode = os.environ.get("COWORK_MODE", "cowork")
    try:
        with open(os.path.join(HERE, "accounts.local.json")) as f:
            accts = json.load(f).get(site, {})
    except (OSError, ValueError):
        accts = {}
    if mode == "test":
        if not accts.get("test"):
            raise RuntimeError(f"No test account for '{site}' in accounts.local.json")
        return accts["test"]
    return accts.get("real", default)
