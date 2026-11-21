import { useAgent, useRpc, type PluginTimelineItemProps } from "@getpaseo/plugin/client";
import { Markdown } from "@getpaseo/plugin/client/ui";
import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { z } from "zod";
import { openDashboard } from "../shared/open";

export const messageSchema = z.object({ text: z.string(), paths: z.array(z.string()) });

function OpenButton({ agentId, path, theme }: { agentId: string; path: string } & Pick<PluginTimelineItemProps, "theme">) {
  const cwd = useAgent(agentId, (a) => a.cwd);
  const open = useRpc(openDashboard);
  const [status, setStatus] = useState<string>("");
  const name = path.split("/").pop() ?? path;
  const styles = useMemo(() => ({
    row: { flexDirection: "row" as const, alignItems: "center" as const, gap: 10, flexWrap: "wrap" as const },
    button: { paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8, backgroundColor: theme.colors.accent },
    label: { color: theme.colors.accentForeground, fontSize: 13 },
    status: { color: theme.colors.foregroundMuted, fontSize: 12 },
  }), [theme]);
  return (
    <View style={styles.row}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Open ${name} in the workspace browser`}
        style={styles.button}
        onPress={async () => {
          setStatus("Opening…");
          try {
            const r = await open({ agentId, cwd: cwd ?? "", path });
            setStatus(r.ok ? "" : r.message);
          } catch (e) {
            setStatus(e instanceof Error ? e.message : String(e));
          }
        }}
      >
        <Text style={styles.label}>Open {name}</Text>
      </Pressable>
      {status ? <Text style={styles.status}>{status}</Text> : null}
    </View>
  );
}

export function MessageWithDashboards({ agentId, item, theme }: PluginTimelineItemProps<z.output<typeof messageSchema>>) {
  return (
    <View style={{ gap: 10 }}>
      <Markdown>{item.data.text}</Markdown>
      {item.data.paths.map((p) => <OpenButton key={p} agentId={agentId} path={p} theme={theme} />)}
    </View>
  );
}

