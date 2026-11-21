# Manual tests: Paseo and AionUi with Idli Muse

For laptop testing of all three apps (T3, Paseo, AionUi) see
[docs/oss-desktop-laptop-testing.md](../../../docs/oss-desktop-laptop-testing.md); the DGX side is
[dgx/up.sh](dgx/up.sh) (per-user Paseo and AionUi with fixed IPs, plus the other agent's T3 runtime).

These reproduce the 2026-11-06 runs on the DGX (Linux arm64, Docker). They are an experiment,
not an installer. Don't route `io.idli.cc` to these servers: they are single-user and use plain HTTP.
Keep passwords and homes out of git. Use synthetic CSVs only.

Set once, from the worktree root:

```sh
R=benchmarks/runs/2026-11-06-oss-desktop-independent
ST=$HOME/io-oss-state                     # private runtime state, outside the repo
node app/io/fetch-codex.js linux-arm64    # IO's pinned Codex 0.154.0
```

## Shared: per-user networks and model proxy

```sh
docker network create --internal --subnet 172.31.77.0/24 --gateway 172.31.77.1 io-oss-private
docker network create --internal --subnet 172.31.78.0/24 --gateway 172.31.78.1 io-oss-private-b
python3 $R/paseo/model_proxy.py 172.31.77.1 8183 $ST/model-requests.jsonl &   # user A
python3 $R/paseo/model_proxy.py 172.31.78.1 8183 $ST/model-requests.jsonl &   # user B
```

The proxies forward only to Muse on `127.0.0.1:8181`. Stopping one is the "model down" test.

## Paseo

```sh
mkdir -p $ST/paseo-build && cp -r app/io/codex-bin/linux-arm64 $ST/paseo-build/codex && cp $R/paseo/Dockerfile $ST/paseo-build/
docker build -t io-oss-paseo:0.15.2 $ST/paseo-build
for u in a b; do
  net=$([ $u = a ] && echo io-oss-private || echo io-oss-private-b); gw=$([ $u = a ] && echo 172.31.77.1 || echo 172.31.78.1)
  d=$ST/paseo-$u; mkdir -p $d/home/.codex $d/home/.paseo $d/workspace
  sed "s#172.31.77.1#$gw#" $R/paseo/codex-config.toml > $d/home/.codex/config.toml
  sed "s#172.31.77.1#$gw#" $R/paseo/paseo-config.json > $d/home/.paseo/config.json
  head -c 18 /dev/urandom | base64 | tr -d '/+=' > $d/password; chmod 600 $d/password
  docker run -d --name io-oss-paseo-$u --network $net --cap-drop ALL --cap-add CHOWN --cap-add SETUID \
    --cap-add SETGID --cap-add DAC_OVERRIDE --cap-add FOWNER --security-opt no-new-privileges \
    --memory 3g --pids-limit 512 -e PASEO_PASSWORD="$(cat $d/password)" \
    -v $d/home:/home/paseo -v $d/workspace:/workspace io-oss-paseo:0.15.2
done
docker restart io-oss-paseo-a io-oss-paseo-b   # avoids the first-boot Codex sqlite race
```

In a browser on the DGX, open `http://<A's container IP>:6767`.
1. Choose **Direct connection**. Enter host `<A's container IP>`, port 6767 and A's password.
2. Skip setup. Choose **Add project**, then **Search for directory**, type `/workspace` and
   choose **Open this path**.
3. Pick **Codex · Idli Muse**, then **Muse Glimmer 30B (Idli)**, then **Full access**.
4. Type the CSV prompt. Attach a CSV from the client using **+**, then **Upload file**, and send.
5. Check: `result.csv` is correct. Open **Explorer**, then **Files**, right-click `result.csv`
   and choose **Download**.
6. Stop: ask for a 300-second script, press the red stop button, and check
   `docker exec io-oss-paseo-a ps aux | grep slow.py`. The process is expected to survive (known gap).
7. Model down: stop A's proxy and send "Reply PONG". Codex is expected to spin silently.
   Claude is expected to error after about 3 minutes.
8. Resume: run `docker restart io-oss-paseo-a`, reload the page, and send a follow-up that needs the
   first turn's context.
9. Repeat as B with **Claude Code · Idli Muse**. In the default Auto mode, Bash is denied. Switch to
   **Always ask** and accept the prompt.
10. Two users: B's password on A must give "Incorrect password". Also run
    `docker exec io-oss-paseo-a node -e "require('http').get('http://<B IP>:6767/api/health')"`,
    which must fail with `ENETUNREACH`.

## AionUi (open-source backend mode)

```sh
mkdir -p $ST/aion-build && curl -o $ST/aion-build/AionUi-2.2.2-linux-arm64.deb \
  https://static.aionui.com/releases/2.2.2/AionUi-2.2.2-linux-arm64.deb
sha256sum $ST/aion-build/*.deb   # 3e8e2f292371fcb1ed5ba9a3a28386e7f0610fcc765480b1e95762e1110515e2
cp -r app/io/codex-bin/linux-arm64 $ST/aion-build/codex && cp $R/aionui/Dockerfile $ST/aion-build/
docker build -t io-oss-aionui:2.2.2 $ST/aion-build
mkdir -p $ST/asar && (cd $ST && dpkg-deb -x aion-build/*.deb pkg && npx --yes @electron/asar@3.2.17 extract pkg/opt/AionUi/resources/app.asar asar)
for u in a b; do
  net=$([ $u = a ] && echo io-oss-private || echo io-oss-private-b); gw=$([ $u = a ] && echo 172.31.77.1 || echo 172.31.78.1)
  d=$ST/aion-$u/home; mkdir -p $d/.codex $d/.claude $d/work $d/aion-oss/data $d/aion-oss/logs
  sed "s#172.31.77.1#$gw#" $R/paseo/codex-config.toml > $d/.codex/config.toml
  sed "s#GATEWAY#$gw#" $R/aionui/claude-settings.json > $d/.claude/settings.json
  cp -r $ST/asar/out/renderer $d/aion-oss/; cp $R/aionui/webhost.mjs $d/aion-oss/
  head -c 18 /dev/urandom | base64 | tr -d '/+=' > $ST/aion-$u/password; chmod 600 $ST/aion-$u/password
  docker run -d --name io-oss-aion-$u --network $net --cap-drop ALL --security-opt no-new-privileges \
    --memory 4g --pids-limit 1024 -v $d:/home/node --entrypoint sleep io-oss-aionui:2.2.2 infinity
  C=/opt/AionUi/resources/bundled-aioncore/linux-arm64/aioncore
  docker exec -i io-oss-aion-$u $C --data-dir /home/node/aion-oss/data --identity-mode webui user set-password --password-stdin < $ST/aion-$u/password
  docker exec -d io-oss-aion-$u sh -c "cd /home/node/aion-oss && $C --host 127.0.0.1 --port 34031 --data-dir /home/node/aion-oss/data --work-dir /home/node/work --log-dir /home/node/aion-oss/logs --identity-mode webui --managed-resources-mode bundled --app-version 2.2.2"
  docker exec -d io-oss-aion-$u sh -c 'cd /home/node/aion-oss && node webhost.mjs /home/node/aion-oss/renderer 34031 25808'
done
```

Open `http://<A's container IP>:25808` and log in as `admin` with A's password.
1. Choose **New Chat**, then **Codex CLI**, then **Permission: Full Access**.
2. Type the prompt. Use **+**, then **Upload from device**, to attach the CSV, and send.
3. Open `result.csv` from the right-hand **Files** tree, then press **Download file** in the preview.
4. Run the stop, model-down, restart and two-user checks as for Paseo. After `docker restart`,
   rerun the two `docker exec -d` lines.
5. Watch for GA4: in the browser devtools Network tab, filter on `google-analytics`. It is expected
   to be present (known gap).

Official binary check (not for Private): run `/opt/AionUi/AionUi --no-sandbox` under Xvfb in a
container with internet. Expect "Sign in to AionUi" and connections to Sentry, GA,
`static.aionui.com` and `gvt1.com`.

## Egress check

```sh
pid=$(docker inspect io-oss-paseo-a -f '{{.State.Pid}}')
sudo nsenter -t $pid -n tcpdump -i any -nn -w $ST/a.pcap 'not tcp port 6767' &
# ...run the tests...
sudo python3 $R/egress_summary.py 172.31.77.2. $ST/a.pcap   # expect only 172.31.77.1:8183
python3 $R/dns_names.py $ST/a.pcap                          # expect no names
```

## Not covered here

These need a human on a real laptop:
- Windows and macOS desktop builds of Paseo, and of AionUi built from source
- fresh Open-mode `codex login` and `claude auth login`
- Cloudflare Access in front of a per-user router
