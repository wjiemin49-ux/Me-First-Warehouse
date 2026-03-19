import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useLiveEvents(): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    const offScripts = window.scriptConsole.onEvent("scripts-updated", () => {
      void queryClient.invalidateQueries({ queryKey: ["scripts"] });
      void queryClient.invalidateQueries({ queryKey: ["overview"] });
    });
    const offRuntime = window.scriptConsole.onEvent("script-runtime-updated", () => {
      void queryClient.invalidateQueries({ queryKey: ["scripts"] });
      void queryClient.invalidateQueries({ queryKey: ["script-detail"] });
      void queryClient.invalidateQueries({ queryKey: ["overview"] });
    });
    const offLogs = window.scriptConsole.onEvent("logs-updated", () => {
      void queryClient.invalidateQueries({ queryKey: ["logs"] });
      void queryClient.invalidateQueries({ queryKey: ["script-detail"] });
    });
    const offSettings = window.scriptConsole.onEvent("settings-updated", () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    });
    const offHealth = window.scriptConsole.onEvent("health-updated", () => {
      void queryClient.invalidateQueries({ queryKey: ["scripts"] });
      void queryClient.invalidateQueries({ queryKey: ["script-detail"] });
      void queryClient.invalidateQueries({ queryKey: ["overview"] });
    });

    return () => {
      offScripts();
      offRuntime();
      offLogs();
      offSettings();
      offHealth();
    };
  }, [queryClient]);
}
