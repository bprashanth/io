#!/bin/sh
# Laptop side: make this laptop's Paseo drivable from the DGX.
#   1. Paseo desktop must be running with a DevTools port (9333). If it isn't, this script says how.
#   2. Opens ONE ssh connection to the DGX that carries:
#        -L 8181  laptop -> DGX 8185: Muse (the T4GC model) via the prefix proxy, unless something already listens on 8181
#        -R 46767 DGX -> laptop Paseo daemon (127.0.0.1:6767)
#        -R 49333 DGX -> laptop Paseo DevTools (127.0.0.1:9333)
#      All forwards bind to 127.0.0.1 on both ends.
# Usage: laptop-up.sh [start|stop|status]   (DGX=user@host overrides the default)
DGX=${DGX:-beeps@gx10-0a47.tail5ef239.ts.net}
PIDFILE=${XDG_RUNTIME_DIR:-/tmp}/paseo-dgx-tunnel.pid
listening() { ss -ltn 2>/dev/null | grep -q "127.0.0.1:$1 "; }

status() {
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then echo "tunnel: up (pid $(cat "$PIDFILE"))"; else echo "tunnel: down"; fi
  listening 6767 && echo "paseo daemon: listening on 6767" || echo "paseo daemon: NOT listening (start the Paseo app)"
  listening 9333 && echo "devtools: listening on 9333" || echo "devtools: NOT listening (restart Paseo with the port, see docs/driving-desktop.md)"
  listening 8181 && echo "muse: 8181 reachable locally" || echo "muse: 8181 not forwarded"
}

case "${1:-start}" in
  status) status ;;
  stop)
    [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; rm -f "$PIDFILE"; echo "tunnel stopped" ;;
  start)
    if ! listening 9333; then
      echo "Paseo has no DevTools port. Quit Paseo (no agents running), then start it with:"
      echo "  setsid /opt/Paseo/Paseo --remote-debugging-port=9333 >/dev/null 2>&1 &"
      exit 1
    fi
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then status; exit 0; fi
    L=""; listening 8181 || L="-L 127.0.0.1:8181:127.0.0.1:8185"   # DGX 8185 = Muse via dgx/muse_prefix_proxy.py
    # shellcheck disable=SC2086
    setsid ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 $L \
      -R 127.0.0.1:46767:127.0.0.1:6767 -R 127.0.0.1:49333:127.0.0.1:9333 "$DGX" </dev/null >/dev/null 2>&1 &
    echo $! > "$PIDFILE"; sleep 4
    kill -0 "$(cat "$PIDFILE")" 2>/dev/null || { echo "ssh exited: run 'ssh $DGX true' to see why (Tailscale may want a sign-in)"; rm -f "$PIDFILE"; exit 1; }
    status ;;
esac
