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

if [ "$WANT_BOARD" = "0" ] && [ "$WANT_SCANNER" = "0" ] && [ "$STOP" = "0" ]; then
  echo "--board-only and --scanner-only together leave nothing to start" >&2; exit 2
fi

APP="app/io"
[ -f "$APP/room_server.py" ] || { echo "run this from the root of the repo" >&2; exit 1; }

RUN="${TMPDIR:-/tmp}/io-event"
mkdir -p "$RUN"

script_for() { [ "$1" = "board" ] && echo room_server.py || echo privacy_server.py; }

# A pid file outlives a crash, and by then the number may belong to something else
# entirely. Killing that on --stop would be a very unpleasant surprise on the machine
# running the projector, so check the pid is really the server before touching it.
ours() {
  local pid="$1" want="$2"
  [ -n "${pid:-}" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  ps -p "$pid" -o args= 2>/dev/null | grep -q -- "$want"
}

# "started" should mean "answering", not "the process has not exited yet".
wait_ready() {
  local port="$1" pid="$2" limit="$3" i=0
  while [ "$i" -lt "$limit" ]; do
    kill -0 "$pid" 2>/dev/null || return 2          # died while we waited
    (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null && { exec 3<&- 2>/dev/null; return 0; }
    sleep 1; i=$((i+1))
  done
  return 1
}

stop_all() {
  local stopped=0
  for name in board scanner; do
    local pf="$RUN/$name.pid"
    [ -f "$pf" ] || continue
    local pid; pid=$(cat "$pf" 2>/dev/null || true)
    if ours "${pid:-}" "$(script_for "$name")"; then
      kill "$pid" 2>/dev/null && stopped=$((stopped+1))
      echo "  stopped $name (pid $pid)"
    elif [ -n "${pid:-}" ]; then
      echo "  $name was not running (pid $pid belongs to something else now)"
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
  local name="$1" script="$2" port="$3" py="$4" ready="${5:-10}"
  local log="$RUN/$name.log" pf="$RUN/$name.pid"
  if [ -f "$pf" ]; then
    if ours "$(cat "$pf" 2>/dev/null)" "$(basename "$script")"; then
      echo "  $name already running (pid $(cat "$pf"))"; return 0
    fi
    rm -f "$pf"    # stale, from a crash or a reboot
  fi
  if command -v ss >/dev/null && ss -ltn 2>/dev/null | grep -q ":$port "; then
    echo "  $name NOT started: something is already listening on port $port."
    echo "      set a different one, e.g. ${name^^}_PORT=$((port+10)) $0"
    return 1
  fi
  ( cd "$APP" && exec "$py" "$(basename "$script")" "$port" ) > "$log" 2>&1 &
  echo $! > "$pf"
  local pid; pid=$(cat "$pf")
  wait_ready "$port" "$pid" "$ready"
  case $? in
    0) echo "  $name started (pid $pid), log: $log" ;;
    2) echo "  $name FAILED to start, last lines of $log:"
       tail -5 "$log" | sed 's/^/      /'; rm -f "$pf"; return 1 ;;
    *) echo "  $name is running (pid $pid) but has not answered on port $port after ${ready}s."
       echo "      it may still be loading. Watch $log; if it never answers, stop and retry."
       tail -3 "$log" | sed 's/^/      /' ;;
  esac
}

trap 'echo; echo "stopping"; stop_all; exit 0' INT TERM
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
    start_one scanner "$APP/privacy_server.py" "$SCANNER_PORT" "$PY_FULL" 120 || WANT_SCANNER=0
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

# Wait here, so Ctrl-C stops both and the operator can see it is alive.
echo
echo "running. Ctrl-C to stop."
while :; do
  sleep 5
  left=0
  for name in board scanner; do
    pf="$RUN/$name.pid"
    [ -f "$pf" ] || continue
    if ours "$(cat "$pf" 2>/dev/null)" "$(script_for "$name")"; then
      left=$((left+1))
    else
      echo "  WARNING: $name stopped, see $RUN/$name.log"; rm -f "$pf"
    fi
  done
  # Nothing left to watch. This happens when --stop was run from another window, or
  # when both servers died; either way sitting here saying "running" would be a lie.
  [ "$left" = "0" ] && { echo; echo "nothing is running any more."; exit 0; }
done
