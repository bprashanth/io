#!/bin/sh
# Dry-run matrix: how long the first-run chat takes to greet and to act on the person's reply.
cd "$(dirname "$0")"
run() { timeout 400 python3 oobe_test.py "$@" 2>&1 | tail -1; }
run --provider t4gc-cowork --thinking high --variant text --reply yes
run --provider t4gc-cowork --thinking high --variant text --reply "go for it"
run --provider t4gc-cowork --thinking high --variant text --reply start
run --provider t4gc-cowork --thinking high --variant text --reply "what does this do?"
run --provider t4gc-cowork --thinking low --variant text --reply yes
run --provider t4gc-cowork --thinking low --variant text --reply "go for it"
run --provider t4gc-cowork --thinking high --variant card --reply "card:Yes, index my Drive"
run --provider t4gc-cowork --thinking low --variant card --reply "card:Yes, index my Drive"
run --provider t4gc-cowork --thinking low --variant card --reply "go for it"
run --provider cowork-9b-or --thinking high --variant text --reply yes
run --provider cowork-9b-or --thinking high --variant text --reply "go for it"
run --provider cowork-9b-or --thinking high --variant text --reply start
run --provider cowork-9b-or --thinking high --variant card --reply "card:Yes, index my Drive"
echo MATRIX-DONE
