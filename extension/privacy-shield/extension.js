// Privacy Shield for Antigravity: starts/stops the local redacting proxy and
// points Antigravity's language server at it through CLOUD_CODE_URL.
//
// Antigravity resolves its backend from the user setting `jetski.cloudCodeUrl`
// and restarts its language server when that setting changes, so enabling or
// disabling the shield is a settings write: no environment variables, no
// manual restart.
const vscode = require("vscode");
const cp = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");

let daemon = null;
let statusBar = null;
let poller = null;
let ctx = null;
let baselineCalls = null;   // daemon call-count when this window attached; routing is
let verified = false;       // "verified" once a model call arrives after that.

const cfg = () => vscode.workspace.getConfiguration("privacyShield");
const net = require("net");
let chosenPort = null;
const port = () => chosenPort || (ctx && ctx.globalState.get("port")) || cfg().get("port") || 8765;

function portFree(p) {
  return new Promise((resolve) => {
    const srv = net.createServer();
    srv.once("error", () => resolve(false));
    srv.once("listening", () => srv.close(() => resolve(true)));
    srv.listen(p, "127.0.0.1");
  });
}

// Our daemon answers /shield/status.json; anything else on the port is a stranger.
// Pick the first free port from the configured one upwards and remember it.
async function choosePort() {
  const base = cfg().get("port") || 8765;
  for (let p = base; p < base + 20; p++) {
    chosenPort = p;
    const st = await getJson(`http://127.0.0.1:${p}/shield/status.json`);
    if (st && (!st.server || path.resolve(st.server) === path.resolve(serverDir()))) return p;   // our daemon, adopt
    if (st) continue;                                            // a foreign shield daemon: leave it alone
    if (await portFree(p)) return p;
  }
  chosenPort = null;
  return null;
}
const proxyUrl = () => `http://127.0.0.1:${port()}`;

function serverDir() {
  return path.join(ctx.extensionPath, "server");
}

function envDir() {
  // The Python env lives in globalStorage, NOT in the versioned extension folder:
  // the IDE deletes the old extension folder on every update, which used to take
  // the 1.7 GB venv and model cache with it (measured 2026-08-25).
  return path.join(stateDir(), "env");
}

function pythonPath() {
  const custom = cfg().get("pythonPath");
  if (custom) return custom;
  const cand = os.platform() === "win32"
    ? [path.join(envDir(), ".venv", "Scripts", "python.exe"), path.join(serverDir(), ".venv", "Scripts", "python.exe")]
    : [path.join(envDir(), ".venv", "bin", "python"), path.join(serverDir(), ".venv", "bin", "python")];
  for (const c of cand) if (fs.existsSync(c)) return c;   // legacy in-extension venv still honoured
  return null;
}

function stateDir() {
  const dir = ctx.globalStorageUri.fsPath;
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function getJson(url) {
  return new Promise((resolve) => {
    const req = http.get(url, { headers: { Accept: "application/json" } }, (res) => {
      let body = "";
      res.on("data", (d) => (body += d));
      res.on("end", () => { try { resolve(JSON.parse(body)); } catch { resolve(null); } });
    });
    req.on("error", () => resolve(null));
    req.setTimeout(1500, () => { req.destroy(); resolve(null); });
  });
}

// ---- connecting Antigravity to the shield -----------------------------------
// Antigravity's agent traffic is sent by a language server that honours the
// CLOUD_CODE_URL environment variable (and nothing else we can set), read when
// the app starts. The daemon must already be listening at that moment or the
// window never finishes loading. So: the daemon runs detached (it survives a
// quit), and enabling/disabling relaunches Antigravity with/without the
// variable through a small detached helper.
function languageServerUsesProxy() {
  return process.env.CLOUD_CODE_URL === proxyUrl();
}

// Antigravity also reads `jetski.cloudCodeUrl` (core setting, not registered, so
// written straight into settings.json). Measured: the agent routes through the
// shield only when the daemon is already listening, CLOUD_CODE_URL is in the
// app's environment, and this setting is applied right after launch. The setting
// must not survive a session (a dead port at startup stalls the window).
function userSettingsPath() {
  return path.join(path.dirname(path.dirname(ctx.globalStorageUri.fsPath)), "settings.json");
}

function readUserSettings() {
  const file = userSettingsPath();
  if (!fs.existsSync(file)) return {};
  const raw = fs.readFileSync(file, "utf8");
  try { return JSON.parse(raw); } catch { /* comments or trailing commas */ }
  try { return JSON.parse(raw.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "").replace(/,\s*([}\]])/g, "$1")); } catch { return null; }
}

function setCloudCodeUrlSetting(value) {
  const settings = readUserSettings();
  if (settings === null) return null;
  if ((settings["jetski.cloudCodeUrl"] || null) === (value || null)) return "same";
  if (value) settings["jetski.cloudCodeUrl"] = value; else delete settings["jetski.cloudCodeUrl"];
  const file = userSettingsPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(settings, null, 2) + "\n");
  return "written";
}

// Antigravity resolves its backend as: jetski.cloudCodeUrl setting if set, else the
// default host. Two language servers exist: the app-level one that serves the agent
// (owned by the main process) and the extension-host one. The app-level server
// learns the URL only (a) as a launch flag or (b) via a push that fires when the
// app's own loadCodeAssist completes — a few seconds after launch, BEFORE our
// activation (onStartupFinished) can write the setting. A value written later is
// never delivered and the agent keeps talking to Google directly while the status
// bar says the shield is on. Measured on Antigravity 1.107.0, 2026-08-22.
// antigravity.handleAuthRefresh re-runs the auth/user-status flow, whose
// loadCodeAssist completion re-pushes the (new) URL to the app-level server;
// antigravity.restartLanguageServer re-reads it for the extension-host server.
function pushCloudCodeUrlToLanguageServers() {
  const run = (cmd) => vscode.commands.executeCommand(cmd).then(() => true, () => false);
  return Promise.all([run("antigravity.handleAuthRefresh"), run("antigravity.restartLanguageServer")]);
}

function relaunch(withShield) {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
    ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
  const extra = (cfg().get("relaunchArgs") || []).join(" ");
  const exe = process.execPath;
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.CLOUD_CODE_URL;
  const cmd = withShield ? daemonCommand() : null;
  const q = (v) => `"${String(v).replace(/"/g, '\\"')}"`;
  if (os.platform() === "win32") {
    const setLine = withShield ? `set "CLOUD_CODE_URL=${proxyUrl()}" && ` : `set "CLOUD_CODE_URL=" && `;
    const daemonLine = cmd ? `(curl -s -m 2 ${proxyUrl()}/shield/status.json >nul 2>&1 || start "" /b ${q(cmd.py)} ${cmd.args.map(q).join(" ")} >> ${q(cmd.log)} 2>&1) && ` +
      `for /l %i in (1,1,90) do @(curl -s -m 2 ${proxyUrl()}/shield/status.json >nul 2>&1 && goto up || timeout /t 1 /nobreak >nul)\n:up\n` : `curl -s -m 2 ${proxyUrl()}/shield/quit >nul 2>&1 & `;
    cp.spawn("cmd.exe", ["/c", `timeout /t 4 /nobreak >nul && ${daemonLine}${setLine}start "" "${exe}" ${extra} "${folder}"`],
      { detached: true, stdio: "ignore", windowsHide: true, env: cmd ? cmd.env : env }).unref();
  } else {
    const daemonLine = cmd
      ? `curl -s -m 2 ${proxyUrl()}/shield/status.json >/dev/null 2>&1 || ${os.platform() === "linux" ? "setsid " : ""}nohup ${q(cmd.py)} ${cmd.args.map(q).join(" ")} >> ${q(cmd.log)} 2>&1 & ` +
        `for i in $(seq 1 90); do curl -s -m 2 ${proxyUrl()}/shield/status.json >/dev/null 2>&1 && break; sleep 1; done; `
      : `curl -s -m 2 ${proxyUrl()}/shield/quit >/dev/null 2>&1; `;
    const line = `sleep 4; ${daemonLine}${withShield ? `CLOUD_CODE_URL="${proxyUrl()}"` : ""} "${exe}" ${extra} "${folder}" >/dev/null 2>&1 &`;
    cp.spawn("/bin/sh", ["-c", line], { cwd: stateDir(), detached: true, stdio: "ignore", env: cmd ? cmd.env : env }).unref();
  }
  setTimeout(() => vscode.commands.executeCommand("workbench.action.quit"), 500);
}

// ---- daemon ------------------------------------------------------------------
async function daemonAlive() {
  const s = await getJson(`${proxyUrl()}/shield/status.json`);
  if (!s) return false;
  if (s.server && path.resolve(s.server) !== path.resolve(serverDir())) return false;  // someone else's daemon (another profile/version): do not adopt
  return true;
}

function daemonCommand() {
  const py = pythonPath();
  if (!py) return null;
  const args = [path.join(serverDir(), "shield_proxy.py"), "--port", String(port()),
    "--vault", path.join(stateDir(), "shield-vault-local-only.json"),
    "--review", cfg().get("review") || "off",
    "--discovery", cfg().get("discovery") || "files"];
  // Discovery-at-rest: the daemon scans the workspace folder's files once (and on
  // change); the request path is then deterministic. Queries are held while the
  // scan runs, so nothing can leave with a partially built vault.
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
    ? vscode.workspace.workspaceFolders[0].uri.fsPath : null;
  if (folder) args.push("--scan", folder);
  const numbers = cfg().get("numbers");
  if (numbers) args.push("--numbers", String(numbers));
  if (cfg().get("annotate")) args.push("--annotate");
  const hf = fs.existsSync(path.join(envDir(), "hf-cache")) ? path.join(envDir(), "hf-cache") : path.join(serverDir(), "hf-cache");
  const env = { ...process.env, PII_THREADS: String(cfg().get("threads") || 4),
    HF_HOME: hf, PYTHONUNBUFFERED: "1" };
  delete env.CLOUD_CODE_URL; // the daemon itself must talk to Google directly
  delete env.ELECTRON_RUN_AS_NODE;
  return { py, args, env, log: path.join(stateDir(), "daemon.out") };
}

// Spawn the daemon OUTSIDE the extension host's process tree. VS Code kills its
// children on quit, which left the proxy dead for the seconds the relaunched app
// needs it most (measured: the login check hit ECONNREFUSED and the IDE showed
// "Log in" for the rest of the session). setsid/start make it a free process.
function spawnDetachedDaemon(cmd) {
  const q = (v) => `"${String(v).replace(/"/g, '\\"')}"`;
  if (os.platform() === "win32") {
    const line = `start "" /b ${q(cmd.py)} ${cmd.args.map(q).join(" ")} >> ${q(cmd.log)} 2>&1`;
    cp.spawn("cmd.exe", ["/c", line], { cwd: stateDir(), env: cmd.env, detached: true, stdio: "ignore", windowsHide: true }).unref();
  } else {
    const line = `${os.platform() === "linux" ? "setsid " : ""}nohup ${q(cmd.py)} ${cmd.args.map(q).join(" ")} >> ${q(cmd.log)} 2>&1 &`;
    cp.spawn("/bin/sh", ["-c", line], { cwd: stateDir(), env: cmd.env, detached: true, stdio: "ignore" }).unref();
  }
}

async function startDaemon() {
  if (await daemonAlive()) return true;   // adopt a daemon left running from a previous session
  const p = await choosePort();
  if (p === null) {
    vscode.window.showErrorMessage("Privacy Shield: no free local port between 8765 and 8784.");
    return false;
  }
  await ctx.globalState.update("port", p);
  if (await daemonAlive()) return true;
  const py = pythonPath();
  if (!py) {
    const pick = await vscode.window.showErrorMessage(
      "Privacy Shield: Python environment not found. Run the one-time install (needs internet, about a 500 MB download, 1.7 GB on disk).",
      "Install now");
    if (pick === "Install now") await install();
    return false;
  }
  spawnDetachedDaemon(daemonCommand());
  daemon = true;
  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    if (await getJson(`${proxyUrl()}/shield/status.json`)) return true;
  }
  daemon = null;
  vscode.window.showErrorMessage("Privacy Shield: daemon did not start; see the 'Privacy Shield' output channel.");
  return false;
}

function stopDaemon() {
  getJson(`${proxyUrl()}/shield/quit`);
  daemon = null;
}

// ---- commands -----------------------------------------------------------------
async function enable() {
  if (!(await startDaemon())) return;
  await ctx.globalState.update("enabled", true);
  refresh();
  if (languageServerUsesProxy()) {
    if (setCloudCodeUrlSetting(proxyUrl()) === "written") await pushCloudCodeUrlToLanguageServers();
    vscode.window.showInformationMessage("🛡️ Privacy Shield is active: personal data is replaced before anything leaves this laptop.");
    return;
  }
  const pick = await vscode.window.showWarningMessage(
    "Privacy Shield is running. Antigravity has to be relaunched once so its model traffic goes through it. Relaunch now?",
    { modal: true }, "Relaunch now");
  if (pick === "Relaunch now") {
    // The app-level language server reads jetski.cloudCodeUrl only at app launch
    // (or from a push that races our activation), so the setting must already be
    // in settings.json when the relaunched app starts. The daemon is confirmed
    // listening, so pointing the launch at it is safe; deactivate() keeps the
    // setting for every quit while the shield is enabled.
    setCloudCodeUrlSetting(proxyUrl());
    relaunch(true);
  } else if (setCloudCodeUrlSetting(proxyUrl()) === "written") {
    // No relaunch: the running language server only learns the URL from the next
    // loadCodeAssist push, typically within a minute. Nudge it.
    await pushCloudCodeUrlToLanguageServers();
  }
}

async function disable() {
  const changed = setCloudCodeUrlSetting(null) === "written";
  await ctx.globalState.update("enabled", false);
  refresh();
  if (!process.env.CLOUD_CODE_URL && !changed) {
    // never routed through the shield in this session: just stop quietly
    stopDaemon();
    vscode.window.showInformationMessage("Privacy Shield is off.");
    return;
  }
  const pick = await vscode.window.showWarningMessage(
    "Privacy Shield stopped. Relaunch Antigravity so it talks to Google directly again?", { modal: true }, "Relaunch now");
  if (pick === "Relaunch now") {
    // stop the daemon only after the relaunch has started; the running app still
    // points at it until it quits, and a dead port mid-session shows login errors
    setTimeout(stopDaemon, 3000);
    relaunch(false);
  } else {
    stopDaemon();
    await pushCloudCodeUrlToLanguageServers();
  }
}

async function install() {
  const script = os.platform() === "win32" ? "install.ps1" : "install.sh";
  // The env must land in globalStorage: the IDE deletes the versioned extension
  // folder on every update, and an env installed there dies with it.
  const target = envDir();
  const term = vscode.window.createTerminal({ name: "Privacy Shield install", cwd: serverDir() });
  term.show();
  term.sendText(os.platform() === "win32"
    ? `powershell -ExecutionPolicy Bypass -File .\\${script} "${target}"`
    : `bash ./${script} "${target}"`);
  vscode.window.showInformationMessage("Privacy Shield: installing in the terminal. When it prints 'ready', run 'Privacy Shield: Enable'.");
}

function openUrl(suffix) {
  vscode.env.openExternal(vscode.Uri.parse(`${proxyUrl()}${suffix}`));
}

async function peek() {
  const s = await getJson(`${proxyUrl()}/shield/status.json`);
  const on = s && s.peek ? "0" : "1";
  await getJson(`${proxyUrl()}/shield/peek?on=${on}`);
  vscode.window.showInformationMessage(on === "1"
    ? "Peek mode ON: answers now show the tokens the model actually saw (no rehydration)."
    : "Peek mode OFF: answers show real values again.");
}

async function reset() {
  stopDaemon();
  for (const f of ["shield-vault-local-only.json", "shield-decisions-local-only.json", "shield.log"]) {
    const p = path.join(stateDir(), f);
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
  await new Promise((r) => setTimeout(r, 1500));
  if (ctx.globalState.get("enabled")) await startDaemon();
  vscode.window.showInformationMessage("Privacy Shield: vault and decisions forgotten.");
  refresh();
}

// ---- status bar menu --------------------------------------------------------------
// Clicking the shield opens a picker instead of toggling: turning the shield off
// mid-session should be a deliberate choice, not a misclick.
async function menu() {
  const enabled = ctx.globalState.get("enabled");
  const items = enabled ? [
    { label: "$(dashboard) Show shield status", action: "status" },
    { label: "$(search) Show last request that left the laptop", action: "wire" },
    { label: "$(key) Show vault (what is being hidden)", action: "vault" },
    { label: "$(circle-slash) Disable Privacy Shield…", action: "disable",
      description: "agent traffic goes directly to Google again" },
  ] : [
    { label: "$(shield) Enable Privacy Shield", action: "enable" },
    { label: "$(dashboard) Show shield status", action: "status" },
  ];
  const pick = await vscode.window.showQuickPick(items, {
    placeHolder: enabled ? "Privacy Shield is ON — personal data is replaced before it leaves this laptop"
                         : "Privacy Shield is OFF — agent traffic goes directly to Google",
  });
  if (!pick) return;
  if (pick.action === "enable") return enable();
  if (pick.action === "disable") return disable();
  if (pick.action === "status") return openUrl("/shield/status");
  if (pick.action === "wire") return openUrl("/shield/last-request");
  if (pick.action === "vault") return openUrl("/shield/vault");
}

// ---- status bar -------------------------------------------------------------------
async function refresh() {
  const enabled = ctx.globalState.get("enabled");
  const s = enabled ? await getJson(`${proxyUrl()}/shield/status.json`) : null;
  if (s) {
    if (baselineCalls === null) baselineCalls = s.calls;
    if (s.calls > baselineCalls) verified = true;
  }
  if (!enabled) {
    statusBar.text = "$(shield) Shield off";
    statusBar.tooltip = "Privacy Shield is off. Click to enable.";
    statusBar.backgroundColor = undefined;
  } else if (!s) {
    statusBar.text = "$(shield) Shield starting…";
    statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
  } else if (s.scan_active) {
    statusBar.text = `$(shield) Scanning your files\u2026 ${s.scan_done}/${s.scan_total}` +
      (s.scan_current ? ` \u00b7 ${s.scan_current}` : "");
    statusBar.tooltip = "Privacy Shield is reading the files in this folder to learn what must be hidden. " +
      "Questions asked now are held until the scan finishes; nothing leaves early.";
    statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
  } else if (!verified) {
    // The daemon is up but no model call has passed through it in this session yet,
    // so routing is unproven. This clears on the first shielded agent message; if it
    // never clears while the agent answers, traffic is bypassing the shield.
    statusBar.text = "$(shield) Shield on - awaiting first call";
    statusBar.tooltip = `Privacy Shield is running on ${proxyUrl()} and Antigravity is pointed at it, ` +
      "but no model call has arrived yet. The first agent message verifies routing." +
      (languageServerUsesProxy() ? "" : "\nIf this persists after a chat message, run 'Privacy Shield: Enable' and choose Relaunch.");
    statusBar.backgroundColor = undefined;
  } else {
    const peek = s.peek ? " - PEEK" : "";
    const blocked = s.blocked ? ` - ${s.blocked} blocked` : "";
    statusBar.text = `$(shield) ${s.calls} calls - ${Math.round(s.redact_ms_last)} ms - vault ${s.vault_entries}${blocked}${peek}`;
    statusBar.tooltip = `Privacy Shield active on ${proxyUrl()}\n` +
      `redaction total ${Math.round(s.redact_ms_total)} ms, upstream ${Math.round(s.upstream_ms_total)} ms, ` +
      `${s.bytes_out} bytes sent, ${s.spans_total} values hidden, cache ${s.cache_hits}/${s.cache_hits + s.cache_misses}` +
      (s.pending_review ? "\nWaiting for your reply in the chat (ok / also hide / don't hide)" : "");
    statusBar.backgroundColor = s.pending_review ? new vscode.ThemeColor("statusBarItem.warningBackground") : undefined;
  }
  statusBar.show();
}

function activate(context) {
  ctx = context;
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 1000);
  statusBar.command = "privacyShield.menu";
  context.subscriptions.push(statusBar,
    vscode.commands.registerCommand("privacyShield.enable", enable),
    vscode.commands.registerCommand("privacyShield.disable", disable),
    vscode.commands.registerCommand("privacyShield.toggle", () => (ctx.globalState.get("enabled") ? disable() : enable())),
    vscode.commands.registerCommand("privacyShield.menu", menu),
    vscode.commands.registerCommand("privacyShield.status", () => openUrl("/shield/status")),
    vscode.commands.registerCommand("privacyShield.vault", () => openUrl("/shield/vault")),
    vscode.commands.registerCommand("privacyShield.wire", () => openUrl("/shield/last-request")),
    vscode.commands.registerCommand("privacyShield.peek", peek),
    vscode.commands.registerCommand("privacyShield.reset", reset),
    vscode.commands.registerCommand("privacyShield.install", install),
    vscode.commands.registerCommand("privacyShield.openServerFolder", () => vscode.env.openExternal(vscode.Uri.file(serverDir()))),
    vscode.commands.registerCommand("privacyShield.showLog", () => vscode.commands.executeCommand("workbench.action.output.show.extension-output-insight-out.privacy-shield-#1-Privacy Shield").then(undefined, () => vscode.commands.executeCommand("workbench.action.output.toggleOutput"))),
    { dispose: stopDaemon });
  if (!ctx.globalState.get("enabled")) {
    if (setCloudCodeUrlSetting(null) === "written") {
      pushCloudCodeUrlToLanguageServers();  // never let a stale override survive a crash
    }
  } else {
    startDaemon().then(async (ok) => {
      if (ok) {
        if (setCloudCodeUrlSetting(proxyUrl()) === "written") {
          await pushCloudCodeUrlToLanguageServers();   // the launch-time push has already passed
        }
      } else if (setCloudCodeUrlSetting(null) === "written") {
        await pushCloudCodeUrlToLanguageServers();     // daemon gone: stop pointing at a dead port
      }
      refresh();
    });
  }
  poller = setInterval(refresh, 2000);
  context.subscriptions.push({ dispose: () => clearInterval(poller) });
  refresh();
}

function deactivate() {
  // The daemon stays up on purpose and survives quits, and the app-level language
  // server reads jetski.cloudCodeUrl only at launch — so while the shield is
  // enabled the setting must survive every quit, or a normal reopen starts the
  // agent talking to Google directly until the next endpoint push (measured on
  // 1.107.0). If the daemon is dead at the next launch the cost is a transient
  // login error that clears once activation restarts the daemon (also measured);
  // activation clears the setting itself when the daemon cannot be started.
  if (ctx && ctx.globalState.get("enabled")) return;
  try { setCloudCodeUrlSetting(null); } catch { /* shutting down */ }
}

module.exports = { activate, deactivate };
