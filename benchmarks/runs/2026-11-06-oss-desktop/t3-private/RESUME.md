# Resume the experiment on this server

These commands depend on the retained /tmp downloads/state and Docker test container;
they are not a durable installer. This is a single-user test environment, not the IO gateway.

1. `docker start io-t3-bench`
2. In one terminal: `python3 /tmp/io-t3-benchmark/model_proxy.py`
3. In another: `node /tmp/io-t3-browser/gateway.cjs`
4. Generate a fresh single-use pairing link locally (do not commit/share it):
   ```sh
   docker exec io-t3-bench /opt/t3/t3-0.1.7-linux-arm64/t3 auth pairing create \
     --base-dir /tmp/io-t3-benchmark/home --base-url http://127.0.0.1:8791
   ```
5. Open the link in a local browser, or add it to T3 desktop. The desktop can disable
   Local environment and act solely as a remote client. A normal Linux keyring must
   work; the benchmark's isolated gnome-keyring/Xvfb setup is not a laptop requirement.
6. Start a NEW conversation. Type the CSV prompt, THEN attach a client-only synthetic
   CSV. Verify computation and table preview; don't count preview as download.

For a laptop using Tailscale, localhost8791 on the server is not the laptop's localhost.
An explicitly configured forwarding route would be needed for this temporary loopback
service. Do not change io.idli.cc to this unaudited single-user service: its existing
IO gateway has a different protocol and tenant/identity mapping. The next implementation
step is a compatible authenticated test route with deliberate per-user routing.

Stop: `docker stop io-t3-bench`; stop the two proxy terminals. The existing IO gateway
on8789 and Muse on8181 were never replaced. The benchmark stopped its own test services
at completion. Runtime/auth state is private in /tmp, outside the repository.
