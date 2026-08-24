// vscode:uninstall hook - runs on the next Antigravity start after the extension is
// removed. Two jobs: stop this extension's redaction daemon if it is still running,
// and stop pointing Antigravity at a proxy that no longer exists.
const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");

const here = path.resolve(__dirname, "server");

function getJson(url) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 1200 }, (res) => {
      let b = "";
      res.on("data", (c) => (b += c));
      res.on("end", () => { try { resolve(JSON.parse(b)); } catch { resolve(null); } });
    });
    req.on("error", () => resolve(null));
    req.on("timeout", () => { req.destroy(); resolve(null); });
  });
}

function settingsPaths() {
  const home = os.homedir();
  const names = ["Antigravity", "Antigravity - Insiders"];
  const roots = process.platform === "win32"
    ? [path.join(process.env.APPDATA || path.join(home, "AppData", "Roaming"))]
    : process.platform === "darwin"
      ? [path.join(home, "Library", "Application Support")]
      : [path.join(process.env.XDG_CONFIG_HOME || path.join(home, ".config"))];
  const out = [];
  for (const r of roots) for (const n of names) out.push(path.join(r, n, "User", "settings.json"));
  return out.filter((p) => fs.existsSync(p));
}

(async () => {
  const killed = [];
  for (let p = 8765; p < 8785; p++) {
    const s = await getJson(`http://127.0.0.1:${p}/shield/status.json`);
    if (s && (!s.server || path.resolve(s.server) === here)) {
      await getJson(`http://127.0.0.1:${p}/shield/quit`);
      killed.push(p);
    }
  }
  for (const sp of settingsPaths()) {
    try {
      const j = JSON.parse(fs.readFileSync(sp, "utf8"));
      const url = j["jetski.cloudCodeUrl"] || "";
      const m = /^http:\/\/127\.0\.0\.1:(\d+)$/.exec(url);
      if (m && +m[1] >= 8765 && +m[1] < 8785) {
        // only unroute if that port is ours (just killed) or dead
        const alive = await getJson(`${url}/shield/status.json`);
        if (killed.includes(+m[1]) || !alive) {
          delete j["jetski.cloudCodeUrl"];
          fs.writeFileSync(sp, JSON.stringify(j, null, 2));
          console.log("privacy-shield uninstall: removed jetski.cloudCodeUrl from", sp);
        }
      }
    } catch (e) { /* leave settings untouched on any doubt */ }
  }
  // remove the Python env (1.7 GB) from globalStorage; keep the vault (user data)
  for (const sp of settingsPaths()) {
    const d = path.join(path.dirname(sp), "globalStorage", "insight-out.privacy-shield", "env");
    try {
      if (fs.existsSync(d)) { fs.rmSync(d, { recursive: true, force: true }); console.log("privacy-shield uninstall: removed env", d); }
    } catch (e) { /* leave it */ }
  }
  console.log("privacy-shield uninstall: daemons stopped on ports", killed);
})();
