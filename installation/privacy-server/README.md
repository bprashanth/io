# The privacy server on the DGX, reachable as privacy.idli.cc

What runs: `app/io/privacy_server.py` on port 8899, GLiNER on the GPU, one process, stores
nothing. What it sees: the text io asks it to scan, unredacted. So it needs three things
before it is on a public name: TLS, a way in that opens no port on the box, and a token.

1. **Cloudflare Tunnel**, not a DNS record. 100.82.28.38 is a tailnet address; a public
   name pointing at it reaches nobody. `cloudflared` on the DGX connects outbound and
   forwards `privacy.idli.cc` to `http://localhost:8899`; Cloudflare terminates TLS.
   Nothing on the DGX listens to the internet.
2. **The service** (`io-privacy-server.service`, instructions inside): a systemd user unit
   so it survives reboots and restarts on failure, with the token in a 600-mode env file.
3. **The token - none for the limited preview.** The app is public on GitHub, so a
   token in the app would be no token; and the decision for now is that anyone with the
   app may use the scanner (it stores nothing, so the exposure is GPU time; put a
   Cloudflare rate limit on the hostname). The machinery is there for later:
   `IO_PRIVACY_TOKEN` in `~/.config/io-privacy-server/env` makes the server refuse
   without it (401), and io sends it when it is given the address as
   `https://<token>@privacy.idli.cc`. No second sign-in either way.

Why not Cloudflare Access with a login: it would be a second sign-in in the browser, and
there is no exchange between OpenAI's identity (the ChatGPT login inside io) and
Cloudflare's. Access with a *service token* is the same idea as ours with two headers
instead of one; either is fine, ours has no dependency.

Where io looks, baked in (`DEFAULT_PRIVACY_SERVERS` in `app/io/service.py`, in order;
`IO_PRIVACY_SERVER=a,b` overrides; the settings gear per session): `https://privacy.idli.cc`
first, then `http://100.82.28.38:8899` on the tailnet for the office. Each gets a 4-second
warm-up; the first that answers is used, otherwise the on-device scanner. A quick check
from any laptop:

    curl -s https://privacy.idli.cc/health | head -c 200
    curl -s -X POST https://privacy.idli.cc/scan \
      -H 'Content-Type: application/json' -d '{"text":"call 9876543210"}'
