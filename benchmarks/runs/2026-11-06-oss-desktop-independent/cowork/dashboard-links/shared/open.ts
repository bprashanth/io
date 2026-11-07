import { defineRpc } from "@getpaseo/plugin";
import { z } from "zod";

/** Serve an HTML file from the agent's folder and open it in that agent's workspace browser. */
export const openDashboard = defineRpc({
  name: "dashboard.open",
  input: z.object({ agentId: z.string(), cwd: z.string(), path: z.string() }),
  output: z.object({ ok: z.boolean(), url: z.string(), message: z.string() }),
});

/** Paths ending in .html/.htm mentioned in a message, excluding http(s) URLs. */
export function findHtmlPaths(text: string): string[] {
  const found = new Set<string>();
  const re = /(?:^|[\s`'"(\[])((?:~|\.{1,2})?\/?[\w@%+.,~-]+(?:\/[\w@%+.,~ -]*[\w@%+.,~-])*\.html?)(?=$|[\s`'")\].,:;!?])/g;
  for (const m of text.matchAll(re)) {
    const start = (m.index ?? 0) + m[0].length - m[1].length;
    if (/[a-z]+:\/\/\S*$/i.test(text.slice(Math.max(0, start - 200), start))) continue;
    found.add(m[1]);
  }
  return [...found];
}
