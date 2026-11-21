"""Which account a site plugin should use, and where the test-account file lives.

The file (never committed) is, in order of preference:
  $COWORK_ACCOUNTS, else $IDLI_HOME/config/accounts.json (IDLI_HOME defaults to ~/idli-insights),
  else the legacy cowork/accounts.local.json.
Shape: {"google": {"test": "someone.test@gmail.com", "fixtures": {"pbv_sheet": "<id>", ...}}}

COWORK_MODE=test (set by run_tests.py) uses the site's test account, so tests never touch the
user's real data. Otherwise (co-work) the plugin uses the account signed in to the workspace browser
(`real`, default: the first signed-in account).
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDLI_HOME = os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights")


def accounts_path():
    for p in (os.environ.get("COWORK_ACCOUNTS"), os.path.join(IDLI_HOME, "config", "accounts.json"),
              os.path.join(HERE, "accounts.local.json")):
        if p and os.path.isfile(p):
            return p
    return os.path.join(IDLI_HOME, "config", "accounts.json")


def load_accounts():
    try:
        with open(accounts_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def account(site, default=""):
    accts = load_accounts().get(site, {})
    if os.environ.get("COWORK_MODE", "cowork") == "test":
        if not accts.get("test"):
            raise RuntimeError(f"No test account for '{site}' in {accounts_path()}")
        return accts["test"]
    return accts.get("real", default)
