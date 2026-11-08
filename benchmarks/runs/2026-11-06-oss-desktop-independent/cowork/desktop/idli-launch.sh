#!/bin/sh
# Open "Idli": start Paseo, wait for its daemon, then run the first-run bootstrap (safe every time).
# Stand-in for what an installed package would do on launch. During development Paseo also gets its DevTools
# port so the DGX can drive it (never in a shipped build).
COWORK="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${IDLI_HOME:-$HOME/idli-insights}/config/idli-launch.log"
mkdir -p "$(dirname "$LOG")"
if ! pgrep -f '/opt/Paseo/Paseo.bin --remote-debugging-port' >/dev/null; then
  setsid /opt/Paseo/Paseo --remote-debugging-port=9333 >/dev/null 2>&1 &
fi
for i in $(seq 1 60); do
  paseo status >/dev/null 2>&1 && break
  sleep 1
done
sleep 3
python3 "$COWORK/desktop/idli-bootstrap.py" >>"$LOG" 2>&1
