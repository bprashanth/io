# Privacy Shield Troubleshooting

Three places to check.
"Command palette" below refers to "Ctrl+Shift+P" in vscode. 

## 1. The status bar [loc: bottom right]

- `Shield off`: not enabled. Click it and choose Enable.
- `Shield starting...`: daemon is coming up (first start loads the scanner, up to 90 s).
- `Shield on - awaiting first call`: healthy, nothing sent yet.
- `N calls - X ms - vault M`: healthy and working. N requests intercepted, M values in the vault.
- No shield item at all: the extension did not activate. See section 4.

## 2. The status page [loc: Ctrl+Shift+P -> Privacy Shield -> Open status page]

Command palette: `Privacy Shield: Open status page`, or browse to
`http://127.0.0.1:<port>/shield/status` (port is 8765 unless changed in settings).

Things to audit:
- `calls`, `bytes_out`, `tokens_est_out`: how much has left the laptop.
- `spans_total`: how many values were replaced.
- `blocked`: requests refused because a private value was about to leave.
- `vault_entries`: how many real values are held locally.
- `server`: which install of the daemon is answering. It must point INSIDE this
  extension's folder; if it points somewhere else an old daemon from a previous
  install is still running - quit it from that page or reboot.
- Links: `vault`, `last request` shows the exact bytes that left the laptop.

## 3. The logs [loc: Ctrl+Shift+P -> Privacy Shield -> show daemon log]

- IDE side: command `Privacy Shield: Show daemon log`, or View -> Output -> "Privacy Shield".
- Daemon side: `server/shield.log` inside the extension folder
  (command `Privacy Shield: Open server folder` takes you there).
- Install log: the "Privacy Shield install - server" terminal. The install is done when it
  prints `privacy shield environment ready`. It downloads about 500 MB (torch + the scanner)
  and uses about 1.7 GB of disk.

## 4. Failure classes 

### Summary

| Symptom | Cause | Fix |
|---|---|---|
| No shield in the status bar | Workspace opened in Restricted Mode with an old build (< 0.2.4) | Trust the folder, or update: 0.2.4 activates in Restricted Mode |
| "Python environment not found" | Fresh laptop, one-time install not run | Click "Install now", wait for `ready` in the terminal |
| Install terminal fails at pip | No internet / proxy / low disk (needs 2 GB free) | Fix network or disk, run `Privacy Shield: Install Python environment` again |
| "daemon did not start" | Port taken or venv broken | Check `server/shield.log`; change `privacyShield.port` in settings; reinstall env |
| Status page `server` shows another folder | Stale daemon from an old install | Open that page's `/shield/quit`, then Enable again |
| Model answers but no redaction summary | Traffic is not routed through the proxy | `jetski.cloudCodeUrl` must be `http://127.0.0.1:<port>`; run Enable and accept the relaunch |
| Answers stall after uninstalling | Antigravity still pointed at the dead proxy | 0.2.4 cleans this up on the next start; manually delete `jetski.cloudCodeUrl` from settings.json otherwise |


## 5. What enable / disable / uninstall actually do

- Enable: starts the daemon (its process survives IDE restarts on purpose), points
  Antigravity's model traffic at it (one relaunch needed the first time).
- Disable: tells the daemon to quit and unroutes Antigravity.
- Uninstall: within the next start or two, a cleanup script stops any daemon belonging to
  this install, deletes the Python environment from globalStorage, and removes the routing
  setting. The vault file stays (it is your data); delete it by hand if you want it gone.
