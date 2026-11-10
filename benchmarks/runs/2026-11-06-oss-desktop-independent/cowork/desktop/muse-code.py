#!/usr/bin/env python3
"""Make the one-line "Idli code" a tester pastes into Idli's setup page, from a Cloudflare Access service token.

  python3 desktop/muse-code.py TOKEN.json [--check]

TOKEN.json: {"url": "https://silo.idli.cc", "client_id": "....access", "client_secret": "..."} (one token per
person: Zero Trust > Access > Service credentials, added to the Muse application's Service Auth policy).
Prints the code (it carries the secret: send it to that person only, e.g. over Signal). --check first asks Muse
for its models with the token. Revoke a person by deleting their token in Cloudflare.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "installer"))
import idli_app  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with open(os.path.expanduser(sys.argv[1])) as f:
        t = json.load(f)
    code = idli_app.encode_code((t.get("url") or "https://silo.idli.cc").rstrip("/"), t["client_id"],
                                t["client_secret"])
    if "--check" in sys.argv:
        print("Muse answers with:", ", ".join(idli_app.check_muse(idli_app.decode_code(code))), file=sys.stderr)
    print(code)
