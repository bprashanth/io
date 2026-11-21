#!/usr/bin/env bash
# Stop the remote test servers (state in ~/io-oss-state is kept). Leaves Muse and IO untouched.
docker stop -t 5 io-oss-paseo-a io-oss-paseo-b io-oss-aion-a io-oss-aion-b >/dev/null 2>&1
[ "${1:-}" = "--with-t3" ] && docker stop -t 5 io-t3-bench >/dev/null 2>&1
A="172.31.77.1:8183 172.31.78.1:8183"; [ "${1:-}" = "--with-t3" ] && A="$A 172.26.0.1:8182 127.0.0.1:8791"
for a in $A; do
  pid=$(ss -ltnp | grep " $a " | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2); [ -n "$pid" ] && kill "$pid"
done; true
