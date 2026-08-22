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

const cfg = () => vscode.workspace.getConfiguration("privacyShield");
const port = () => cfg().get("port") || 8765;
const proxyUrl = () => `http://127.0.0.1:${port()}`;

function serverDir() {
  return path.join(ctx.extensionPath, "server");
}

function pythonPath() {
  const custom = cfg().get("pythonPath");
  if (custom) return custom;
  const venv = os.platform() === "win32"
    ? path.join(serverDir(), ".venv", "Scripts", "python.exe")
    : path.join(serverDir(), ".venv", "bin", "python");
  return fs.existsSync(venv) ? venv : null;
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
  if (settings === null) return false;
  if ((settings["jetski.cloudCodeUrl"] || null) === (value || null)) return true;
  if (value) settings["jetski.cloudCodeUrl"] = value; else delete settings["jetski.cloudCodeUrl"];
  const file = userSettingsPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(settings, null, 2) + "\n");
  return true;
}

function relaunch(withShield) {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
    ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
  const extra = (cfg().get("relaunchArgs") || []).join(" ");
  const exe = process.execPath;
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.CLOUD_CODE_URL;
  if (os.platform() === "win32") {
    const setLine = withShield ? `set "CLOUD_CODE_URL=${proxyUrl()}" && ` : `set "CLOUD_CODE_URL=" && `;
    cp.spawn("cmd.exe", ["/c", `timeout /t 4 /nobreak >nul && ${setLine}start "" "${exe}" ${extra} "${folder}"`],
      { detached: true, stdio: "ignore", windowsHide: true, env }).unref();
  } else {
    const line = `sleep 4; ${withShield ? `CLOUD_CODE_URL="${proxyUrl()}"` : ""} "${exe}" ${extra} "${folder}" >/dev/null 2>&1 &`;
    cp.spawn("/bin/sh", ["-c", line], { detached: true, stdio: "ignore", env }).unref();
  }
  setTimeout(() => vscode.commands.executeCommand("workbench.action.quit"), 500);
}

// ---- daemon ------------------------------------------------------------------
async function daemonAlive() {
  return !!(await getJson(`${proxyUrl()}/shield/status.json`));
}

async function startDaemon() {
  if (await daemonAlive()) return true;   // adopt a daemon left running from a previous session
  const py = pythonPath();
  if (!py) {
    const pick = await vscode.window.showErrorMessage(
      "Privacy Shield: Python environment not found. Run the one-time install (needs internet, ~200 MB).",
      "Install now");
    if (pick === "Install now") await install();
    return false;
  }
  const args = [path.join(serverDir(), "shield_proxy.py"), "--port", String(port()),
    "--vault", path.join(stateDir(), "shield-vault-local-only.json"),
    "--review", cfg().get("review") || "chat"];
  const numbers = cfg().get("numbers");
  if (numbers) args.push("--numbers", String(numbers));
  if (cfg().get("annotate")) args.push("--annotate");
  const env = { ...process.env, PII_THREADS: String(cfg().get("threads") || 4),
    HF_HOME: path.join(serverDir(), "hf-cache"), PYTHONUNBUFFERED: "1" };
  delete env.CLOUD_CODE_URL; // the daemon itself must talk to Google directly
  const logFile = path.join(stateDir(), "daemon.out");
  const fd = fs.openSync(logFile, "a");
  daemon = cp.spawn(py, args, { cwd: stateDir(), env, detached: true, stdio: ["ignore", fd, fd], windowsHide: true });
  daemon.unref();
  daemon.on("exit", (code) => { daemon = null; refresh(); });
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    if (await getJson(`${proxyUrl()}/shield/status.json`)) return true;
    if (!daemon) return false;
  }
  vscode.window.showErrorMessage("Privacy Shield: daemon did not start; see the 'Privacy Shield' output channel.");
  return false;
}

function stopDaemon() {
  getJson(`${proxyUrl()}/shield/quit`);
  if (daemon) { try { daemon.kill(); } catch { /* already gone */ } daemon = null; }
}

// ---- commands -----------------------------------------------------------------
async function enable() {
  if (!(await startDaemon())) return;
  await ctx.globalState.update("enabled", true);
  refresh();
  if (languageServerUsesProxy()) {
    setCloudCodeUrlSetting(proxyUrl());
    vscode.window.showInformationMessage("🛡️ Privacy Shield is active: personal data is replaced before anything leaves this laptop.");
    return;
  }
  const pick = await vscode.window.showWarningMessage(
    "Privacy Shield is running. Antigravity has to be relaunched once so its model traffic goes through it. Relaunch now?",
    { modal: true }, "Relaunch now");
  if (pick === "Relaunch now") relaunch(true);
}

async function disable() {
  setCloudCodeUrlSetting(null);
  stopDaemon();
  await ctx.globalState.update("enabled", false);
  refresh();
  if (!process.env.CLOUD_CODE_URL) {
    vscode.window.showInformationMessage("Privacy Shield is off.");
    return;
  }
  const pick = await vscode.window.showWarningMessage(
    "Privacy Shield stopped. Relaunch Antigravity so it talks to Google directly again?", { modal: true }, "Relaunch now");
  if (pick === "Relaunch now") relaunch(false);
}

async function install() {
  const script = os.platform() === "win32" ? "install.ps1" : "install.sh";
  const term = vscode.window.createTerminal({ name: "Privacy Shield install", cwd: serverDir() });
  term.show();
  term.sendText(os.platform() === "win32" ? `powershell -ExecutionPolicy Bypass -File .\\${script}` : `bash ./${script}`);
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

// ---- status bar -------------------------------------------------------------------
async function refresh() {
  const enabled = ctx.globalState.get("enabled");
  const s = enabled ? await getJson(`${proxyUrl()}/shield/status.json`) : null;
  if (!enabled) {
    statusBar.text = "$(shield) Shield off";
    statusBar.tooltip = "Privacy Shield is off. Click to enable.";
    statusBar.backgroundColor = undefined;
  } else if (!s) {
    statusBar.text = "$(shield) Shield starting…";
    statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
  } else if (!languageServerUsesProxy()) {
    statusBar.text = "$(shield) Shield ready – relaunch Antigravity";
    statusBar.tooltip = "The shield is running but this Antigravity was started without it. Run 'Privacy Shield: Enable' and choose Relaunch.";
    statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
  } else {
    const peek = s.peek ? " · PEEK" : "";
    const blocked = s.blocked ? ` · ${s.blocked} blocked` : "";
    statusBar.text = `$(shield) ${s.calls} calls · ${Math.round(s.redact_ms_last)} ms · vault ${s.vault_entries}${blocked}${peek}`;
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
  statusBar.command = "privacyShield.toggle";
  context.subscriptions.push(statusBar,
    vscode.commands.registerCommand("privacyShield.enable", enable),
    vscode.commands.registerCommand("privacyShield.disable", disable),
    vscode.commands.registerCommand("privacyShield.toggle", () => (ctx.globalState.get("enabled") ? disable() : enable())),
    vscode.commands.registerCommand("privacyShield.status", () => openUrl("/shield/status")),
    vscode.commands.registerCommand("privacyShield.vault", () => openUrl("/shield/vault")),
    vscode.commands.registerCommand("privacyShield.wire", () => openUrl("/shield/last-request")),
    vscode.commands.registerCommand("privacyShield.peek", peek),
    vscode.commands.registerCommand("privacyShield.reset", reset),
    vscode.commands.registerCommand("privacyShield.install", install),
    vscode.commands.registerCommand("privacyShield.openServerFolder", () => vscode.env.openExternal(vscode.Uri.file(serverDir()))),
    vscode.commands.registerCommand("privacyShield.showLog", () => vscode.commands.executeCommand("workbench.action.output.show.extension-output-insight-out.privacy-shield-#1-Privacy Shield").then(undefined, () => vscode.commands.executeCommand("workbench.action.output.toggleOutput"))),
    { dispose: stopDaemon });
  setCloudCodeUrlSetting(null);   // never let a stale override survive a crash
  if (ctx.globalState.get("enabled")) {
    startDaemon().then((ok) => { if (ok && languageServerUsesProxy()) setCloudCodeUrlSetting(proxyUrl()); refresh(); });
  }
  poller = setInterval(refresh, 2000);
  context.subscriptions.push({ dispose: () => clearInterval(poller) });
  refresh();
}

function deactivate() {
  // The daemon stays up on purpose (the relaunched Antigravity needs it listening);
  // the setting must not survive the session.
  try { setCloudCodeUrlSetting(null); } catch { /* shutting down */ }
}

module.exports = { activate, deactivate };
