import { createServer, type Server } from "node:http";
import { createReadStream, realpathSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { randomBytes } from "node:crypto";
import type { RpcInput } from "@getpaseo/plugin";
import type { openDashboard } from "../shared/open";

// One local static server. Each served folder gets an unguessable prefix; nothing else is served.
const roots = new Map<string, string>(); // token -> folder
let server: Server | undefined;
let port = 0;

const TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".js": "text/javascript",
  ".css": "text/css", ".json": "application/json", ".csv": "text/csv; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml",
  ".gif": "image/gif", ".webp": "image/webp", ".txt": "text/plain; charset=utf-8",
};

async function ensureServer(): Promise<number> {
  if (server) return port;
  server = createServer((req, res) => {
    const url = new URL(req.url ?? "/", "http://x");
    const [, token, ...rest] = url.pathname.split("/");
    const root = roots.get(token);
    const file = root && resolve(root, decodeURIComponent(rest.join("/")));
    if (!root || !file || (file !== root && !file.startsWith(root + sep))) {
      res.writeHead(404).end("not found");
      return;
    }
    try {
      if (!statSync(file).isFile()) throw new Error("not a file");
      res.writeHead(200, { "content-type": TYPES[extname(file).toLowerCase()] ?? "application/octet-stream",
                           "cache-control": "no-store" });
      createReadStream(file).pipe(res);
    } catch {
      res.writeHead(404).end("not found");
    }
  });
  await new Promise<void>((ok) => server!.listen(0, "127.0.0.1", ok));
  const addr = server.address();
  port = typeof addr === "object" && addr ? addr.port : 0;
  return port;
}

function tokenFor(folder: string): string {
  for (const [t, f] of roots) if (f === folder) return t;
  const t = randomBytes(9).toString("hex");
  roots.set(t, folder);
  return t;
}

/** Ask the daemon to open a tab in the agent's workspace browser (same tool agents use). */
async function newTab(agentId: string, url: string): Promise<string | null> {
  const daemon = process.env.PASEO_DAEMON_URL ?? "http://127.0.0.1:6767";
  const body = JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call",
    params: { name: "browser_new_tab", arguments: { url } } });
  try {
    const r = await fetch(`${daemon}/mcp/agents?callerAgentId=${encodeURIComponent(agentId)}`, {
      method: "POST", body,
      headers: { "content-type": "application/json", accept: "application/json, text/event-stream" },
    });
    const raw = await r.text();
    const data = raw.split("\n").find((l) => l.startsWith("data:"));
    const msg = JSON.parse(data ? data.slice(5) : raw);
    if (msg.error) return String(msg.error.message ?? "browser tab failed");
    if (msg.result?.isError) return String(msg.result.content?.[0]?.text ?? "browser tab failed");
    return null;
  } catch (e) {
    return e instanceof Error ? e.message : String(e);
  }
}

export async function open({ agentId, cwd, path }: RpcInput<typeof openDashboard>) {
  const expanded = path.startsWith("~/") ? join(homedir(), path.slice(2)) : path;
  let file: string;
  try {
    file = realpathSync(isAbsolute(expanded) ? expanded : resolve(cwd, expanded));
  } catch {
    return { ok: false, url: "", message: `File not found: ${path}` };
  }
  // Serve the file's own folder (so relative assets like data.csv still load).
  const folder = resolve(file, "..");
  const p = await ensureServer();
  const rel = relative(folder, file).split(sep).map(encodeURIComponent).join("/");
  const url = `http://127.0.0.1:${p}/${tokenFor(folder)}/${rel}`;
  const err = await newTab(agentId, url);
  return err ? { ok: false, url, message: `Could not open the workspace browser: ${err}` }
             : { ok: true, url, message: "Opened in the workspace browser" };
}

export function stop() {
  server?.close();
  server = undefined;
  roots.clear();
}
