#!/usr/bin/env bash
# Bring up the per-user remote test servers on the DGX (architecture B):
#   Paseo  user A 172.31.77.2:6767   user B 172.31.78.2:6767
#   AionUi user A 172.31.77.3:25808  user B 172.31.78.3:25808
#   T3     (other agent's io-t3-bench container) via 127.0.0.1:8791
# Every container sits on an --internal per-user network and reaches only Muse through a
# logging proxy on that network's gateway (:8183 -> 127.0.0.1:8181). Nothing is published on a
# public interface; laptops reach these over `ssh -L`. Idempotent; state lives in $ST.
# Usage: up.sh [--no-t3]       Stop: down.sh
set -euo pipefail
R=$(cd "$(dirname "$0")/.." && pwd)            # benchmarks/runs/2026-11-06-oss-desktop-independent
REPO=$(cd "$R/../../.." && pwd)
ST=${IO_OSS_STATE:-$HOME/io-oss-state}
mkdir -p "$ST"; chmod 700 "$ST"
C=/opt/AionUi/resources/bundled-aioncore/linux-arm64/aioncore

net() { docker network inspect "$1" >/dev/null 2>&1 || docker network create --internal --subnet "$2" --gateway "${2%.0/24}.1" "$1" >/dev/null; }
net io-oss-private   172.31.77.0/24
net io-oss-private-b 172.31.78.0/24

proxy() {  # $1 = gateway ip
  if ! ss -ltn | grep -q "$1:8183"; then
    setsid nohup python3 "$R/paseo/model_proxy.py" "$1" 8183 "$ST/model-requests.jsonl" >"$ST/proxy-$1.log" 2>&1 < /dev/null &
  fi
}
proxy 172.31.77.1; proxy 172.31.78.1

images() {
  docker image inspect io-oss-paseo:0.15.2 >/dev/null 2>&1 || {
    [ -x "$REPO/app/io/codex-bin/linux-arm64/bin/codex" ] || (cd "$REPO" && node app/io/fetch-codex.js linux-arm64)
    b=$(mktemp -d); cp -r "$REPO/app/io/codex-bin/linux-arm64" "$b/codex"; cp "$R/paseo/Dockerfile" "$b/"
    docker build -q -t io-oss-paseo:0.15.2 "$b"; rm -rf "$b"; }
  docker image inspect io-oss-aionui:2.2.2 >/dev/null 2>&1 || {
    b=$(mktemp -d); cp -r "$REPO/app/io/codex-bin/linux-arm64" "$b/codex"; cp "$R/aionui/Dockerfile" "$b/"
    curl -fsSo "$b/AionUi-2.2.2-linux-arm64.deb" https://static.aionui.com/releases/2.2.2/AionUi-2.2.2-linux-arm64.deb
    echo "3e8e2f292371fcb1ed5ba9a3a28386e7f0610fcc765480b1e95762e1110515e2  $b/AionUi-2.2.2-linux-arm64.deb" | sha256sum -c -
    docker build -q -t io-oss-aionui:2.2.2 "$b"; rm -rf "$b"; }
}
images

renderer() {  # extract AionUi's renderer once
  [ -d "$ST/aion-renderer" ] && return
  t=$(mktemp -d); docker create --name io-oss-aion-x io-oss-aionui:2.2.2 >/dev/null
  docker cp io-oss-aion-x:/opt/AionUi/resources/app.asar "$t/app.asar"
  docker cp io-oss-aion-x:/opt/AionUi/resources/app.asar.unpacked "$t/app.asar.unpacked"; docker rm io-oss-aion-x >/dev/null
  (cd "$t" && npx --yes @electron/asar@3.2.17 extract app.asar x >/dev/null)
  mv "$t/x/out/renderer" "$ST/aion-renderer"; rm -rf "$t"
}
renderer

for u in a b; do
  if [ $u = a ]; then NET=io-oss-private; GW=172.31.77.1; P=172.31.77.2; A=172.31.77.3
  else NET=io-oss-private-b; GW=172.31.78.1; P=172.31.78.2; A=172.31.78.3; fi

  # ---- Paseo: only the T4GC providers exist on the server (no subscription logins on Idli)
  d=$ST/paseo-$u; mkdir -p "$d/home/.codex-t4gc" "$d/home/.claude-t4gc" "$d/home/.paseo" "$d/workspace"
  sed "s#172.31.77.1#$GW#" "$R/paseo/codex-config.toml" > "$d/home/.codex-t4gc/config.toml"
  sed "s#GATEWAY#$GW#" "$R/aionui/claude-settings.json" > "$d/home/.claude-t4gc/settings.json"
  sed "s#/HOME#/home/paseo#g" "$R/dgx/paseo-server-config.json" > "$d/home/.paseo/config.json"
  [ -s "$d/password" ] || { head -c 18 /dev/urandom | base64 | tr -d '/+=' > "$d/password"; chmod 600 "$d/password"; }
  if ! docker inspect io-oss-paseo-$u >/dev/null 2>&1; then
    docker run -d --name io-oss-paseo-$u --network $NET --ip $P --cap-drop ALL --cap-add CHOWN --cap-add SETUID \
      --cap-add SETGID --cap-add DAC_OVERRIDE --cap-add FOWNER --security-opt no-new-privileges \
      --memory 3g --pids-limit 512 -e PASEO_PASSWORD="$(cat "$d/password")" \
      -v "$d/home:/home/paseo" -v "$d/workspace:/workspace" io-oss-paseo:0.15.2 >/dev/null
    sleep 20; docker restart -t 5 io-oss-paseo-$u >/dev/null   # first boot races Codex's sqlite init
  else docker start io-oss-paseo-$u >/dev/null; fi

  # ---- AionUi open-source backend (aioncore --identity-mode webui) + webhost.mjs
  d=$ST/aion-$u; h=$d/home; mkdir -p "$h/.codex" "$h/.claude" "$h/work" "$h/aion-oss/data" "$h/aion-oss/logs"
  sed "s#172.31.77.1#$GW#" "$R/paseo/codex-config.toml" > "$h/.codex/config.toml"
  sed "s#GATEWAY#$GW#" "$R/aionui/claude-settings.json" > "$h/.claude/settings.json"
  [ -d "$h/aion-oss/renderer" ] || cp -r "$ST/aion-renderer" "$h/aion-oss/renderer"
  cp "$R/aionui/webhost.mjs" "$h/aion-oss/"
  [ -s "$d/password" ] || { head -c 18 /dev/urandom | base64 | tr -d '/+=' > "$d/password"; chmod 600 "$d/password"; }
  if ! docker inspect io-oss-aion-$u >/dev/null 2>&1; then
    docker run -d --name io-oss-aion-$u --network $NET --ip $A --cap-drop ALL --security-opt no-new-privileges \
      --memory 4g --pids-limit 1024 -v "$h:/home/node" --entrypoint sleep io-oss-aionui:2.2.2 infinity >/dev/null
  else docker start io-oss-aion-$u >/dev/null; fi
  docker exec -i io-oss-aion-$u $C --data-dir /home/node/aion-oss/data --identity-mode webui user set-password --password-stdin < "$d/password" >/dev/null
  docker exec io-oss-aion-$u sh -c 'pgrep -x aioncore >/dev/null' || docker exec -d io-oss-aion-$u sh -c \
    "cd /home/node/aion-oss && $C --host 127.0.0.1 --port 34031 --data-dir /home/node/aion-oss/data --work-dir /home/node/work --log-dir /home/node/aion-oss/logs --identity-mode webui --managed-resources-mode bundled --app-version 2.2.2 >aioncore.out 2>&1"
  docker exec io-oss-aion-$u sh -c 'pgrep -f "[w]ebhost.mjs" >/dev/null' || docker exec -d io-oss-aion-$u sh -c \
    'cd /home/node/aion-oss && node webhost.mjs /home/node/aion-oss/renderer 34031 25808 >webhost.out 2>&1'
done

# ---- T3: resume the other agent's single-user runtime exactly as its RESUME.md describes
if [ "${1:-}" != "--no-t3" ] && docker inspect io-t3-bench >/dev/null 2>&1; then
  docker start io-t3-bench >/dev/null
  ss -ltn | grep -q '172.26.0.1:8182' || { setsid nohup python3 /tmp/io-t3-benchmark/model_proxy.py >"$ST/t3-proxy.log" 2>&1 < /dev/null & }
  ss -ltn | grep -q '127.0.0.1:8791' || { cd /tmp/io-t3-browser && setsid nohup node gateway.cjs >"$ST/t3-gateway.log" 2>&1 < /dev/null & }
fi

sleep 3
echo "Passwords (keep private):"
for u in a b; do echo "  user $u  paseo: $ST/paseo-$u/password   aionui (login admin): $ST/aion-$u/password"; done
echo "T3 pairing link (single use, run when ready):"
echo "  docker exec io-t3-bench /opt/t3/t3-0.1.7-linux-arm64/t3 auth pairing create --base-dir /tmp/io-t3-benchmark/home --base-url http://127.0.0.1:8791"
