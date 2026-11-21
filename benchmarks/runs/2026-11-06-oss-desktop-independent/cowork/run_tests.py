#!/usr/bin/env python3
"""Run each site plugin's tests.json against its TEST account and record the result in site.json.

  run_tests.py [site ...] [--agent PASEO_AGENT_ID]

Tests run in the workspace of the given agent (Paseo agents already have PASEO_AGENT_ID), so the
test account must be signed in there. If it is not, the site fails with "not signed in" and the
user signs in later and reruns. Real accounts are never used: COWORK_MODE=test.
"""
import argparse
import datetime
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["COWORK_MODE"] = "test"
from lib.accounts import account, load_accounts  # noqa: E402
from lib.browser import NotSignedIn  # noqa: E402


def check(expect, out):
    text = json.dumps(out, ensure_ascii=False, default=str)
    if isinstance(out, dict) and out.get("error") and not expect.get("error_ok"):
        return f"tool error: {out['error']}"
    for key in expect.get("keys", []):
        if key not in out:
            return f"missing key '{key}'"
    for key in expect.get("nonempty", []):
        if not out.get(key):
            return f"'{key}' is empty"
    for s in expect.get("contains", []):
        if s.lower() not in text.lower():
            return f"output does not contain '{s}'"
    return None


def run_site(site):
    sdir = os.path.join(HERE, "sites", site)
    with open(os.path.join(sdir, "tests.json")) as f:
        raw = f.read()
    # {{name}} placeholders are test-account fixtures kept out of git (see lib/accounts.py)
    fixtures = load_accounts().get(site, {}).get("fixtures", {})
    for k, v in fixtures.items():
        raw = raw.replace("{{%s}}" % k, v)
    spec = json.loads(raw)
    if spec.get("data_dir"):
        os.environ["COWORK_DATA_DIR"] = os.path.join(sdir, spec["data_dir"])
    mod = importlib.import_module(f"sites.{site}.tools")
    results = []
    try:
        who = mod.whoami()
        want = account(site, "") if spec.get("needs_account") else ""
        if want and who.lower() != want.lower():
            raise NotSignedIn(f"signed in as {who}, but the test account is {want}")
    except NotSignedIn as e:
        return [{"test": "signed in", "ok": False,
                 "why": f"{e} Sign in to the test account in this workspace's browser, then rerun."}]
    except RuntimeError as e:
        return [{"test": "signed in", "ok": False, "why": str(e)}]
    for t in spec["tests"]:
        t0 = time.time()
        try:
            out = mod.TOOLS[t["tool"]][0](**t.get("args", {}))
            why = check(t.get("expect", {}), out)
        except Exception as e:
            why = f"{type(e).__name__}: {e}"
        results.append({"test": t["name"], "ok": why is None, "why": why, "secs": round(time.time() - t0, 1)})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", nargs="*")
    ap.add_argument("--agent", default=os.environ.get("PASEO_AGENT_ID"))
    a = ap.parse_args()
    if a.agent:
        os.environ["PASEO_AGENT_ID"] = a.agent
    sites = a.sites or sorted(d for d in os.listdir(os.path.join(HERE, "sites"))
                              if os.path.isfile(os.path.join(HERE, "sites", d, "tests.json")))
    failed = 0
    for site in sites:
        res = run_site(site)
        passed = sum(r["ok"] for r in res)
        summary = f"passed {passed}/{len(res)}" if passed == len(res) else \
            f"FAILED {len(res) - passed}/{len(res)}: " + "; ".join(f"{r['test']}: {r['why']}" for r in res if not r["ok"])
        failed += passed != len(res)
        print(f"[{site}] {summary}")
        for r in res:
            print(f"   {'ok  ' if r['ok'] else 'FAIL'} {r['test']}" + (f" ({r.get('secs')}s)" if r.get("secs") else "")
                  + ("" if r["ok"] else f" -- {r['why']}"))
        meta_path = os.path.join(HERE, "sites", site, "site.json")
        with open(meta_path) as f:
            meta = json.load(f)
        meta["last_test"] = {"when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                             "result": "passed" if passed == len(res) else "failed",
                             "detail": summary[:500]}
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
