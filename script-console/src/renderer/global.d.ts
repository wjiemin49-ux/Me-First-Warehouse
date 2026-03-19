import {
  AppEventPayloadMap,
  AppSettings,
  LogSearchFilters,
  PluginDescriptor,
  ScriptFilters,
  ScriptManifest,
  WizardTemplateInput,
} from "@shared/types";

declare global {
  interface Window {
    scriptConsole: {
      getOverview: () => Promise<unknown>;
      listScripts: (filters?: ScriptFilters) => Promise<unknown>;
      getScriptDetail: (scriptId: string) => Promise<unknown>;
      startScript: (scriptId: string) => Promise<unknown>;
      stopScript: (scriptId: string) => Promise<unknown>;
      restartScript: (scriptId: string) => Promise<unknown>;
      forceKillScript: (scriptId: string) => Promise<unknown>;
      rescanScripts: () => Promise<unknown>;
      openFolder: (scriptId: string) => Promise<void>;
      tailLogs: (scriptId?: string, limit?: number) => Promise<unknown>;
      searchLogs: (filters: LogSearchFilters) => Promise<unknown>;
      exportLogs: (filters: LogSearchFilters) => Promise<string>;
      clearLogIndex: (scriptId?: string) => Promise<void>;
      getSettings: () => Promise<AppSettings>;
      saveSettings: (settings: Partial<AppSettings>) => Promise<AppSettings>;
      wizardDetect: (rootDir: string) => Promise<unknown>;
      wizardValidateManifest: (content: string, rootDir: string) => Promise<unknown>;
      wizardTestLaunch: (manifest: ScriptManifest, rootDir: string) => Promise<unknown>;
      wizardTestHealth: (manifest: ScriptManifest, rootDir: string) => Promise<unknown>;
      wizardGenerateTemplate: (input: WizardTemplateInput) => Promise<string>;
      wizardImportExisting: (sourceDir: string, workspaceRoot: string) => Promise<string>;
      listPlugins: () => Promise<PluginDescriptor[]>;
      getManifestSchema: () => Promise<unknown>;
      onEvent: <K extends keyof AppEventPayloadMap>(
        event: K,
        listener: (payload: AppEventPayloadMap[K]) => void,
      ) => () => void;
    };
  }
}

export {};
