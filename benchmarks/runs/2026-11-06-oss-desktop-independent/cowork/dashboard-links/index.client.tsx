import type { PluginClientContext } from "@getpaseo/plugin/client";
import { MessageWithDashboards, messageSchema } from "./client/message";
import { findHtmlPaths } from "./shared/open";

export default function contribute(client: PluginClientContext) {
  client.addTimelineTransformer({
    id: "html-links",
    query: { itemType: "assistant_message" },
    transform({ item, phase }) {
      if (phase !== "complete") return undefined;
      const paths = findHtmlPaths(item.text);
      if (paths.length === 0) return undefined;
      return { items: [{ type: "plugin", kind: "message-with-dashboards", version: 1, data: { text: item.text, paths } }] };
    },
  });
  client.addTimelineRenderer({ kind: "message-with-dashboards", version: 1, schema: messageSchema, Component: MessageWithDashboards });
  return () => {};
}
