#!/usr/bin/env python3
"""Connect this computer's Idli to Muse through Cloudflare, with the person's own Access service token.

  python3 desktop/muse-connect.py <token file>   a JSON file {"url", "client_id", "client_secret"} (e.g. from the
                                                 owner); it is copied to ~/idli-insights/config/muse-access.json
  python3 desktop/muse-connect.py                use the muse-access.json already there (rewrite settings)
  python3 desktop/muse-connect.py --off          back to the dev ssh tunnel (http://127.0.0.1:8181)

It checks the token against <url>/v1/models, then points the Idli 30B provider's Claude settings
(~/idli-insights/config/claude-t4gc/settings.json) at the URL with the two Access headers. Restart chats after.
Never prints the secret.
"""
import json
import os
import sys
import urllib.error
import urllib.request

COWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, COWORK)
from lib import muse  # noqa: E402

SETTINGS = os.path.join(muse.IDLI, "config", "claude-t4gc", "settings.json")


def write_private(path, data):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(path + ".tmp", path)


def check(a):
    req = urllib.request.Request(a["url"].rstrip("/") + "/v1/models",
                                 headers={"CF-Access-Client-Id": a["client_id"],
                                          "CF-Access-Client-Secret": a["client_secret"], "User-Agent": "idli"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            ids = [m.get("id") for m in json.load(r).get("data", [])]
    except urllib.error.HTTPError as e:
        sys.exit(f"{a['url']} refused the token (HTTP {e.code}): check the Client ID and secret, and that the "
                 "Access application has a Service Auth policy that includes this token.")
    except OSError as e:
        sys.exit(f"Can't reach {a['url']}: {e}")
    print(f"Muse reachable at {a['url']}: {', '.join(i for i in ids if i) or 'no models listed'}")


def main():
    with open(SETTINGS) as f:
        s = json.load(f)
    env = s.setdefault("env", {})
    if "--off" in sys.argv:
        env["ANTHROPIC_BASE_URL"] = muse.LOCAL
        env.pop("ANTHROPIC_CUSTOM_HEADERS", None)
        write_private(SETTINGS, s)
        print(f"Idli 30B uses {muse.LOCAL} (the ssh tunnel) again. Start new chats to pick it up.")
        return
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        with open(os.path.expanduser(args[0])) as f:
            src = json.load(f)
        a = {"url": src.get("url") or "https://silo.idli.cc", "client_id": src["client_id"],
             "client_secret": src["client_secret"]}
    else:
        a = muse.access()
        if not a:
            sys.exit(f"No token: pass the token file, or create {muse.ACCESS}.")
    check(a)
    if args:
        write_private(muse.ACCESS, a)
        print(f"saved {muse.ACCESS} (only you can read it)")
    env["ANTHROPIC_BASE_URL"] = a["url"].rstrip("/")
    env["ANTHROPIC_CUSTOM_HEADERS"] = (f"CF-Access-Client-Id: {a['client_id']}\n"
                                       f"CF-Access-Client-Secret: {a['client_secret']}")
    write_private(SETTINGS, s)
    print(f"Idli 30B now reaches Muse at {a['url']}. Start new chats to pick it up.")


if __name__ == "__main__":
    main()
