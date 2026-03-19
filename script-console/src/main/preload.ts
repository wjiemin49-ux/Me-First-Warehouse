import { contextBridge, ipcRenderer } from "electron";
import { APP_EVENT_CHANNEL, IPC_CHANNELS } from "@shared/constants";
import { appSettingsSchema, logSearchSchema, manifestSchema, scriptIdSchema, wizardTemplateSchema } from "@shared/schema";
import { AppEventPayloadMap, AppSettings, LogSearchFilters, ScriptFilters, ScriptManifest, WizardTemplateInput } from "@shared/types";

const api = {
  getOverview: () => ipcRenderer.invoke(IPC_CHANNELS.getOverview),
  listScripts: (filters?: ScriptFilters) => ipcRenderer.invoke(IPC_CHANNELS.listScripts, filters),
  getScriptDetail: (scriptId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.getScriptDetail, scriptIdSchema.parse(scriptId)),
  startScript: (scriptId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.startScript, scriptIdSchema.parse(scriptId)),
  stopScript: (scriptId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.stopScript, scriptIdSchema.parse(scriptId)),
  restartScript: (scriptId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.restartScript, scriptIdSchema.parse(scriptId)),
  forceKillScript: (scriptId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.forceKillScript, scriptIdSchema.parse(scriptId)),
  rescanScripts: () => ipcRenderer.invoke(IPC_CHANNELS.rescanScripts),
  openFolder: (scriptId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.openFolder, scriptIdSchema.parse(scriptId)),
  tailLogs: (scriptId?: string, limit?: number) => ipcRenderer.invoke(IPC_CHANNELS.getLogs, scriptId, limit),
  searchLogs: (filters: LogSearchFilters) =>
    ipcRenderer.invoke(IPC_CHANNELS.searchLogs, logSearchSchema.parse(filters)),
  exportLogs: (filters: LogSearchFilters) =>
    ipcRenderer.invoke(IPC_CHANNELS.exportLogs, logSearchSchema.parse(filters)),
  clearLogIndex: (scriptId?: string) => ipcRenderer.invoke(IPC_CHANNELS.clearLogIndex, scriptId),
  getSettings: () => ipcRenderer.invoke(IPC_CHANNELS.getSettings),
  saveSettings: (settings: Partial<AppSettings>) =>
    ipcRenderer.invoke(IPC_CHANNELS.saveSettings, appSettingsSchema.partial().parse(settings)),
  wizardDetect: (rootDir: string) => ipcRenderer.invoke(IPC_CHANNELS.wizardDetect, rootDir),
  wizardValidateManifest: (content: string, rootDir: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.wizardValidateManifest, content, rootDir),
  wizardTestLaunch: (manifest: ScriptManifest, rootDir: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.wizardTestLaunch, manifestSchema.parse(manifest), rootDir),
  wizardTestHealth: (manifest: ScriptManifest, rootDir: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.wizardTestHealth, manifestSchema.parse(manifest), rootDir),
  wizardGenerateTemplate: (input: WizardTemplateInput) =>
    ipcRenderer.invoke(IPC_CHANNELS.wizardGenerateTemplate, wizardTemplateSchema.parse(input)),
  wizardImportExisting: (sourceDir: string, workspaceRoot: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.wizardImportExisting, sourceDir, workspaceRoot),
  listPlugins: () => ipcRenderer.invoke(IPC_CHANNELS.pluginsList),
  getManifestSchema: () => ipcRenderer.invoke(IPC_CHANNELS.manifestSchema),
  onEvent: <K extends keyof AppEventPayloadMap>(event: K, listener: (payload: AppEventPayloadMap[K]) => void) => {
    const handler = (_: unknown, message: { event: string; payload: AppEventPayloadMap[K] }) => {
      if (message.event === event) {
        listener(message.payload);
      }
    };
    ipcRenderer.on(APP_EVENT_CHANNEL, handler);
    return () => ipcRenderer.removeListener(APP_EVENT_CHANNEL, handler);
  },
};

contextBridge.exposeInMainWorld("scriptConsole", api);
