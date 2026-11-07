import type { PluginServerContext } from "@getpaseo/plugin/server";
import { open, stop } from "./server/open";
import { openDashboard } from "./shared/open";

export default function contribute(server: PluginServerContext) {
  server.handle(openDashboard, open);
  return () => stop();
}
