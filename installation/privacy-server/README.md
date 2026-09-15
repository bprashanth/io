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
3. **The token.** `IO_PRIVACY_TOKEN` on the server; io gets it inside the server address,
   `https://<token>@privacy.idli.cc`, and sends it as a bearer header (the address that
   is logged is the one without it). No token, no scan: 401. There is no second sign-in
   for the person; the app carries the credential. It is a shared secret, so anyone with
   it can use the scanner (never see anyone else's text - nothing is stored); rotate it by
   changing the env file and the address io is given.

Why not Cloudflare Access with a login: it would be a second sign-in in the browser, and
there is no exchange between OpenAI's identity (the ChatGPT login inside io) and
Cloudflare's. Access with a *service token* is the same idea as ours with two headers
instead of one; either is fine, ours has no dependency.

Where io looks by default: `DEFAULT_PRIVACY_SERVER` in `app/io/service.py`
(`IO_PRIVACY_SERVER` overrides; the settings gear per session). Switch it to
`https://<token>@privacy.idli.cc` once the tunnel answers `/health`, and keep the
tailnet address as the fallback for the office. A quick check from any laptop:

    curl -s https://privacy.idli.cc/health | head -c 200
    curl -s -X POST https://privacy.idli.cc/scan -H 'Authorization: Bearer <token>' \
      -H 'Content-Type: application/json' -d '{"text":"call 9876543210"}'
