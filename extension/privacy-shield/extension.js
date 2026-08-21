// Privacy Shield for Antigravity: starts/stops the local redacting proxy and
// points Antigravity's language server at it through CLOUD_CODE_URL.
//
// The language server reads CLOUD_CODE_URL when it starts, so enabling or
// disabling the shield needs one Antigravity restart. The extension sets the
// variable for the user's login session (launchctl on macOS, setx on Windows,
// ~/.config/environment.d on Linux) and tells the user to restart.
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

// ---- CLOUD_CODE_URL for the login session -----------------------------------
function setSessionEnv(value) {
  const plat = os.platform();
  try {
    if (plat === "darwin") {
      cp.execFileSync("launchctl", value ? ["setenv", "CLOUD_CODE_URL", value] : ["unsetenv", "CLOUD_CODE_URL"]);
      return "launchctl (applies to apps started from the Dock after this)";
    }
    if (plat === "win32") {
      cp.execFileSync("setx", ["CLOUD_CODE_URL", value || ""]);
      return "setx (applies to apps started after this)";
    }
    const dir = path.join(os.homedir(), ".config", "environment.d");
    fs.mkdirSync(dir, { recursive: true });
    const file = path.join(dir, "privacy-shield.conf");
    if (value) fs.writeFileSync(file, `CLOUD_CODE_URL=${value}\n`); else if (fs.existsSync(file)) fs.unlinkSync(file);
    return "~/.config/environment.d/privacy-shield.conf (systemd user sessions; or launch with CLOUD_CODE_URL=... antigravity)";
  } catch (e) {
    return `could not set automatically (${e.message}); set CLOUD_CODE_URL=${value || ""} yourself before launching Antigravity`;
  }
}

function languageServerUsesProxy() {
  return process.env.CLOUD_CODE_URL === proxyUrl();
}

// ---- daemon ------------------------------------------------------------------
async function startDaemon() {
  if (daemon) return true;
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
  const out = vscode.window.createOutputChannel("Privacy Shield");
  daemon = cp.spawn(py, args, { cwd: stateDir(), env });
  daemon.stdout.on("data", (d) => out.append(d.toString()));
  daemon.stderr.on("data", (d) => out.append(d.toString()));
  daemon.on("exit", (code) => { out.appendLine(`daemon exited (${code})`); daemon = null; refresh(); });
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    if (await getJson(`${proxyUrl()}/shield/status.json`)) return true;
    if (!daemon) return false;
  }
  vscode.window.showErrorMessage("Privacy Shield: daemon did not start; see the 'Privacy Shield' output channel.");
  return false;
}

function stopDaemon() {
  if (daemon) { daemon.kill(); daemon = null; }
}

// ---- commands -----------------------------------------------------------------
async function enable() {
  if (!(await startDaemon())) return;
  await ctx.globalState.update("enabled", true);
  const how = setSessionEnv(proxyUrl());
  refresh();
  if (!languageServerUsesProxy()) {
    const pick = await vscode.window.showWarningMessage(
      `Privacy Shield daemon is running. Antigravity must be restarted once so its model traffic goes through it (set via ${how}).`,
      "Restart now", "Later");
    if (pick === "Restart now") vscode.commands.executeCommand("workbench.action.reloadWindow");
  } else {
    vscode.window.showInformationMessage("🛡️ Privacy Shield is active: personal data is replaced before anything leaves this laptop.");
  }
}

async function disable() {
  stopDaemon();
  await ctx.globalState.update("enabled", false);
  const how = setSessionEnv("");
  refresh();
  const pick = await vscode.window.showWarningMessage(
    `Privacy Shield stopped. Restart Antigravity so it talks to Google directly again (cleared via ${how}).`,
    "Restart now", "Later");
  if (pick === "Restart now") vscode.commands.executeCommand("workbench.action.reloadWindow");
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
  if (ctx.globalState.get("enabled")) await startDaemon();
  vscode.window.showInformationMessage("Privacy Shield: vault and decisions forgotten.");
  refresh();
}

// ---- status bar -------------------------------------------------------------------
async function refresh() {
  const enabled = ctx.globalState.get("enabled");
  const s = daemon ? await getJson(`${proxyUrl()}/shield/status.json`) : null;
  if (!enabled) {
    statusBar.text = "$(shield) Shield off";
    statusBar.tooltip = "Privacy Shield is off. Click to enable.";
    statusBar.backgroundColor = undefined;
  } else if (!s) {
    statusBar.text = "$(shield) Shield starting…";
    statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
  } else if (!languageServerUsesProxy()) {
    statusBar.text = "$(shield) Shield ready – restart Antigravity";
    statusBar.tooltip = "Daemon is running but this Antigravity was started without CLOUD_CODE_URL. Restart it.";
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
    { dispose: stopDaemon });
  if (ctx.globalState.get("enabled")) startDaemon().then(refresh);
  poller = setInterval(refresh, 2000);
  context.subscriptions.push({ dispose: () => clearInterval(poller) });
  refresh();
}

function deactivate() { stopDaemon(); }

module.exports = { activate, deactivate };
