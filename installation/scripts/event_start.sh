#!/usr/bin/env bash
# Start the two servers an organizer runs during the event, and print the addresses to
# read out to the room.
#
#   ./installation/scripts/event_start.sh              # start both
#   ./installation/scripts/event_start.sh --board-only # just the projector board
#   ./installation/scripts/event_start.sh --scanner-only
#   ./installation/scripts/event_start.sh --stop        # stop whatever is running
#
# Run it from the root of the repo. Ctrl-C stops both.
#
#   the room board    collects the blind-comparison votes, one line per laptop, and shows
#                     a live tally for the projector
#   the privacy server scans text for laptops that cannot run the model themselves, which
#                     today means Intel Macs and anything short of disk or memory
#
# Read this before starting the privacy server: text sent to it is NOT redacted. It cannot
# be, because finding the private values in it is the job. Only offer that address to
# people who need it, and only on the room's own wifi.
set -uo pipefail

BOARD_PORT="${BOARD_PORT:-8890}"
SCANNER_PORT="${SCANNER_PORT:-8899}"
WANT_BOARD=1
WANT_SCANNER=1
STOP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --board-only)   WANT_SCANNER=0; shift ;;
    --scanner-only) WANT_BOARD=0; shift ;;
    --stop)         STOP=1; shift ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

APP="app/io"
[ -f "$APP/room_server.py" ] || { echo "run this from the root of the repo" >&2; exit 1; }

RUN="${TMPDIR:-/tmp}/io-event"
mkdir -p "$RUN"

stop_all() {
  local stopped=0
  for name in board scanner; do
    local pf="$RUN/$name.pid"
    [ -f "$pf" ] || continue
    local pid; pid=$(cat "$pf" 2>/dev/null || true)
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null && stopped=$((stopped+1))
      echo "  stopped $name (pid $pid)"
    fi
    rm -f "$pf"
  done
  [ "$stopped" = "0" ] && echo "  nothing was running"
  return 0
}

if [ "$STOP" = "1" ]; then
  echo "stopping"; stop_all; exit 0
fi

# The bundled python if there is one, else whatever python3 is on the machine. Both servers
# are stdlib only, so either works; the scanner needs the full environment.
PY_PLAIN="python3"
PY_FULL=""
ROOT=$(pwd)
for c in "$ROOT/$APP/.venv/bin/python" "$HOME/.local/share/io/runtime/bin/python3"; do
  [ -x "$c" ] && { PY_FULL="$c"; break; }   # absolute: start_one cds into app/io
done

# the address to read out: the machine's address on the room's network, not localhost
lan_ip() {
  ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}' \
    || hostname -I 2>/dev/null | awk '{print $1}'
}
IP=$(lan_ip)
[ -n "${IP:-}" ] || IP="<this machine's address>"

start_one() {
  local name="$1" script="$2" port="$3" py="$4"
  local log="$RUN/$name.log" pf="$RUN/$name.pid"
  if [ -f "$pf" ] && kill -0 "$(cat "$pf" 2>/dev/null)" 2>/dev/null; then
    echo "  $name already running (pid $(cat "$pf"))"; return 0
  fi
  if command -v ss >/dev/null && ss -ltn 2>/dev/null | grep -q ":$port "; then
    echo "  $name NOT started: something is already listening on port $port."
    echo "      set a different one, e.g. ${name^^}_PORT=$((port+10)) $0"
    return 1
  fi
  ( cd "$APP" && exec "$py" "$(basename "$script")" "$port" ) > "$log" 2>&1 &
  echo $! > "$pf"
  sleep 1
  if kill -0 "$(cat "$pf")" 2>/dev/null; then
    echo "  $name started (pid $(cat "$pf")), log: $log"
  else
    echo "  $name FAILED to start, last lines of $log:"; tail -5 "$log" | sed 's/^/      /'
    rm -f "$pf"; return 1
  fi
}

echo "starting the event servers"
if [ "$WANT_BOARD" = "1" ]; then
  start_one board "$APP/room_server.py" "$BOARD_PORT" "$PY_PLAIN" || WANT_BOARD=0
fi
if [ "$WANT_SCANNER" = "1" ]; then
  if [ -z "$PY_FULL" ]; then
    echo "  privacy server SKIPPED: no io environment found."
    echo "    it needs the scanner installed. Run app/io/install.sh once, or start io"
    echo "    on this machine so it builds its environment, then run this again."
    WANT_SCANNER=0
  else
    echo "  privacy server is loading the scanner, this takes a few seconds"
    start_one scanner "$APP/privacy_server.py" "$SCANNER_PORT" "$PY_FULL" || WANT_SCANNER=0
  fi
fi

echo
if [ "$WANT_BOARD" = "0" ] && [ "$WANT_SCANNER" = "0" ]; then
  echo; echo "nothing is running. Fix the errors above and try again."; exit 1
fi
echo "=================================================================="
echo " read these out to the room"
echo "=================================================================="
[ "$WANT_BOARD" = "1" ]   && printf "  room server      http://%s:%s\n" "$IP" "$BOARD_PORT"
[ "$WANT_SCANNER" = "1" ] && printf "  privacy server   http://%s:%s\n" "$IP" "$SCANNER_PORT"
echo
[ "$WANT_BOARD" = "1" ] && echo "  put http://$IP:$BOARD_PORT on the projector, it refreshes itself"
[ "$WANT_SCANNER" = "1" ] && cat <<EOF
  give the privacy server address ONLY to people whose io says the scanner
  cannot run on their computer. Text sent there is not redacted.
EOF
echo
echo "  everyone must be on the same wifi as this machine"
echo "  votes are appended to $APP/room-votes.jsonl"
echo "  stop both with: ./installation/scripts/event_start.sh --stop"
echo "=================================================================="

# Wait, so Ctrl-C stops both, and so the operator can see it is alive.
trap 'echo; echo "stopping"; stop_all; exit 0' INT TERM
echo
echo "running. Ctrl-C to stop."
while :; do
  sleep 5
  for name in board scanner; do
    pf="$RUN/$name.pid"
    [ -f "$pf" ] || continue
    kill -0 "$(cat "$pf" 2>/dev/null)" 2>/dev/null || {
      echo "  WARNING: $name stopped unexpectedly, see $RUN/$name.log"; rm -f "$pf"; }
  done
done
