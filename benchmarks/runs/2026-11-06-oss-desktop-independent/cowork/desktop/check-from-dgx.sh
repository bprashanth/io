#!/bin/bash
# DGX side: verify this machine can drive the laptop's Paseo over the tunnel. Read-only except that
# it opens (and closes) one terminal in the laptop's DIY workspace and takes a screenshot.
# Run from the cowork/ folder of this repo on the DGX:  desktop/check-from-dgx.sh
set -u
cd "$(dirname "$0")/.."
P=desktop/paseo-remote.sh
ok() { echo "PASS  $*"; }; bad() { echo "FAIL  $*"; FAILED=1; }; FAILED=0

curl -s -m 5 -o /dev/null http://127.0.0.1:46767/ && ok "laptop daemon reachable on 127.0.0.1:46767" \
  || { bad "laptop daemon not reachable: on the laptop run desktop/laptop-up.sh"; exit 1; }
curl -s -m 5 http://127.0.0.1:49333/json/version | grep -q Paseo && ok "laptop DevTools reachable on 127.0.0.1:49333" \
  || bad "DevTools not reachable: Paseo must run with --remote-debugging-port=9333 (laptop-up.sh says how)"

PROVIDERS=$($P provider ls 2>&1)
for p in t4gc-cowork diy-claude; do
  echo "$PROVIDERS" | grep -q "^$p .*available" && ok "provider $p available" || bad "provider $p missing or unavailable"
done

WS=$($P workspace ls --json | python3 -c '
import json,sys
ws=json.load(sys.stdin)
diy=[w for w in ws if w["cwd"].endswith("/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork")]
cw=[w for w in ws if w["cwd"].endswith("/cowork-real")]
print((diy[0]["workspaceId"] if diy else "-"), (cw[0]["workspaceId"] if cw else "-"), (diy[0]["cwd"] if diy else "-"))')
read -r DIY_WS COWORK_WS LAPTOP_COWORK <<<"$WS"
[ "$DIY_WS" != "-" ] && ok "DIY workspace $DIY_WS ($LAPTOP_COWORK)" || bad "no DIY workspace for the cowork/ folder on the laptop"
[ "$COWORK_WS" != "-" ] && ok "co-work workspace $COWORK_WS (~/idli-insights/cowork-real)" || bad "no co-work workspace for ~/cowork-real"

if [ "$DIY_WS" != "-" ]; then
  T=$($P terminal create --workspace "$DIY_WS" --name dgx-check --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
  sleep 2; $P terminal send-keys "$T" "echo dgx-check-\$(git rev-parse --short HEAD)" Enter >/dev/null; sleep 3
  LAPTOP_HEAD=$($P terminal capture "$T" | grep -o 'dgx-check-[0-9a-f]\{7,\}' | tail -1 | sed 's/dgx-check-//')
  $P terminal kill "$T" >/dev/null
  [ -n "$LAPTOP_HEAD" ] && ok "laptop terminal works; laptop checkout at $LAPTOP_HEAD (DGX at $(git rev-parse --short HEAD))" \
    || bad "could not run a command in a laptop terminal"
fi

SHOTS=${SHOTS:-$HOME/io-oss-state/desktop-shots} python3 desktop/drive.py shot dgx-check >/tmp/dgx-check.txt 2>&1 \
  && ok "screenshot of the laptop app: $(head -1 /tmp/dgx-check.txt | cut -d'|' -f1 | sed 's/saved //')" \
  || bad "screenshot failed: $(tail -1 /tmp/dgx-check.txt)"

# The site plugins on THIS machine, driving the laptop's browser tabs through the tunnel.
AGENT=$($P ls --json | python3 -c '
import json,sys
a=[x for x in json.load(sys.stdin) if x["cwd"].endswith("/2026-11-06-oss-desktop-independent/cowork")]
print(a[0]["id"] if a else "")')
if [ -z "$AGENT" ]; then
  bad "no agent in the DIY workspace yet; start any DIY chat on the laptop, then rerun"
elif ! python3 -c 'import sys; sys.path.insert(0, "."); from lib.accounts import load_accounts; sys.exit(0 if load_accounts() else 1)'; then
  bad "no test-account file: copy the laptop's ~/idli-insights/config/accounts.json to the same path here (see docs/driving-desktop.md)"
else
  [ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip -q install duckdb pandas openpyxl; }
  # Browser tools need a LIVE caller agent (idle agents get closed) and new tabs only open in the
  # workspace the app is showing. Wake the agent (no model call) and show its workspace first.
  $P agent reload "$AGENT" >/dev/null 2>&1
  python3 desktop/drive.py goto "$DIY_WS" >/dev/null 2>&1 || bad "could not show the DIY workspace in the app"
  PASEO_MCP_URL=http://127.0.0.1:46767/mcp/agents .venv/bin/python run_tests.py --agent "$AGENT" | tee /tmp/dgx-tests.txt | grep '^\['
  grep -q FAILED /tmp/dgx-tests.txt && bad "site tests (details in /tmp/dgx-tests.txt)" || ok "site tests pass from the DGX through the tunnel"
fi
[ "$FAILED" = 0 ] && echo "ALL CHECKS PASSED" || { echo "SOME CHECKS FAILED"; exit 1; }
