import path from "node:path";
import { BrowserWindow, app, ipcMain, nativeTheme } from "electron";
import { APP_EVENT_CHANNEL, IPC_CHANNELS } from "@shared/constants";
import { appSettingsSchema, logSearchSchema, manifestSchema, scriptIdSchema } from "@shared/schema";
import { AppSettings, LogSearchFilters, ScriptFilters, ScriptManifest, WizardTemplateInput } from "@shared/types";
import { ensureDir } from "@main/utils/path-utils";
import { AuditService } from "./audit-service";
import { DatabaseService } from "./database-service";
import { EventBus } from "./event-bus";
import { HealthMonitor } from "./health-monitor";
import { IndexService } from "./index-service";
import { LogService } from "./log-service";
import { ProcessSupervisor } from "./process-supervisor";
import { ResourceSampler } from "./resource-sampler";
import { SettingsService } from "./settings-service";
import { StartupService } from "./startup-service";
import { TrayService } from "./tray-service";
import { WizardService } from "./wizard-service";
import { WorkspaceWatcher } from "./workspace-watcher";
import { SampleProjectService } from "./sample-project-service";
import { PluginRegistry } from "./plugin-registry";

export class AppKernel {
  readonly events = new EventBus();
  readonly db: DatabaseService;
  readonly audit: AuditService;
  readonly settings: SettingsService;
  readonly indexService: IndexService;
  readonly logService: LogService;
  readonly resourceSampler: ResourceSampler;
  readonly startupService: StartupService;
  readonly wizardService: WizardService;
  readonly processSupervisor: ProcessSupervisor;
  readonly healthMonitor: HealthMonitor;
  readonly trayService: TrayService;
  readonly workspaceWatcher: WorkspaceWatcher;
  readonly sampleProjectService: SampleProjectService;
  readonly pluginRegistry: PluginRegistry;
  private readonly windows = new Set<BrowserWindow>();

  constructor() {
    const dataRoot = ensureDir(path.join(app.getPath("appData"), "ScriptConsole"));
    const dbPath = path.join(dataRoot, "data", "script-console.db");
    this.db = new DatabaseService(dbPath);
    this.audit = new AuditService(this.db);
    this.settings = new SettingsService(this.db);
    this.settings.load();
    this.logService = new LogService(this.db, this.events, () => this.settings.get());
    this.indexService = new IndexService(this.db, this.audit, this.events);
    this.resourceSampler = new ResourceSampler();
    this.startupService = new StartupService();
    this.wizardService = new WizardService();
    this.sampleProjectService = new SampleProjectService();
    this.pluginRegistry = new PluginRegistry();
    this.processSupervisor = new ProcessSupervisor(
      this.indexService,
      this.audit,
      this.events,
      this.logService,
      this.resourceSampler,
      () => this.settings.get(),
    );
    this.healthMonitor = new HealthMonitor(
      this.indexService,
      this.events,
      this.resourceSampler,
      this.processSupervisor,
      this.logService,
      () => this.settings.get(),
    );
    this.trayService = new TrayService();
    this.workspaceWatcher = new WorkspaceWatcher(() => this.settings.get(), (rootDir) => {
      this.scanWorkspace(rootDir);
    });
  }

  private broadcast(event: string, payload: unknown): void {
    for (const window of this.windows) {
      if (!window.isDestroyed()) {
        window.webContents.send(APP_EVENT_CHANNEL, { event, payload });
      }
    }
  }

  private async autoStartEligibleScripts(): Promise<void> {
    const scripts = this.indexService.listScripts();
    for (const script of scripts) {
      if (!script.record.manifest.policy.allowAutoStart) {
        continue;
      }
      if (script.runtime.lifecycleState === "running" || script.runtime.lifecycleState === "starting") {
        continue;
      }
      if (script.runtime.circuitState === "open") {
        continue;
      }
      await this.processSupervisor.startScript(script.record.id, "auto-start");
    }
  }

  bindWindow(window: BrowserWindow): void {
    this.windows.add(window);
    window.on("closed", () => {
      this.windows.delete(window);
    });

    this.events.on("scripts-updated", (payload) => this.broadcast("scripts-updated", payload));
    this.events.on("overview-updated", (payload) => this.broadcast("overview-updated", payload));
    this.events.on("script-runtime-updated", (payload) => this.broadcast("script-runtime-updated", payload));
    this.events.on("logs-updated", (payload) => this.broadcast("logs-updated", payload));
    this.events.on("settings-updated", (payload) => this.broadcast("settings-updated", payload));
    this.events.on("scan-completed", (payload) => this.broadcast("scan-completed", payload));
    this.events.on("health-updated", (payload) => this.broadcast("health-updated", payload));
  }

  initialize(): void {
    const settings = this.settings.get();
    this.applyTheme(settings.theme);
    this.startupService.setEnabled(settings.openAtLogin);
    this.sampleProjectService.ensure(settings.scriptRoot);
    this.scanWorkspace();
    void this.autoStartEligibleScripts();
    this.workspaceWatcher.start();
    this.healthMonitor.start();
  }

  shutdown(): void {
    this.workspaceWatcher.stop();
    this.healthMonitor.stop();
    this.trayService.destroy();
    this.events.removeAllListeners();
    this.db.close();
  }

  applyTheme(theme: AppSettings["theme"]): void {
    nativeTheme.themeSource = theme;
  }

  scanWorkspace(rootDir = this.settings.get().scriptRoot) {
    const scanned = this.indexService.scanWorkspace(rootDir);
    scanned.forEach((summary) => {
      void this.processSupervisor.syncExternalProcess(summary);
      if (summary.record.manifest.logging.filePath) {
        this.logService.watchExternalLogFile(summary.record.id, summary.record.manifest.logging.filePath);
      }
    });
    return scanned;
  }

  registerIpc(window: BrowserWindow): void {
    this.bindWindow(window);

    ipcMain.handle(IPC_CHANNELS.getOverview, () => this.indexService.getOverview());
    ipcMain.handle(IPC_CHANNELS.listScripts, (_event, filters?: ScriptFilters) => this.indexService.listScripts(filters));
    ipcMain.handle(IPC_CHANNELS.getScriptDetail, (_event, scriptId: string) =>
      this.indexService.getScriptDetail(scriptIdSchema.parse(scriptId)),
    );
    ipcMain.handle(IPC_CHANNELS.startScript, (_event, scriptId: string) =>
      this.processSupervisor.startScript(scriptIdSchema.parse(scriptId)),
    );
    ipcMain.handle(IPC_CHANNELS.stopScript, (_event, scriptId: string) =>
      this.processSupervisor.stopScript(scriptIdSchema.parse(scriptId), false),
    );
    ipcMain.handle(IPC_CHANNELS.restartScript, (_event, scriptId: string) =>
      this.processSupervisor.restartScript(scriptIdSchema.parse(scriptId)),
    );
    ipcMain.handle(IPC_CHANNELS.forceKillScript, (_event, scriptId: string) =>
      this.processSupervisor.forceKillScript(scriptIdSchema.parse(scriptId)),
    );
    ipcMain.handle(IPC_CHANNELS.rescanScripts, () => this.scanWorkspace());
    ipcMain.handle(IPC_CHANNELS.openFolder, (_event, scriptId: string) =>
      this.indexService.openScriptFolder(scriptIdSchema.parse(scriptId)),
    );
    ipcMain.handle(IPC_CHANNELS.getLogs, (_event, scriptId?: string, limit?: number) =>
      this.logService.getTail(scriptId, limit),
    );
    ipcMain.handle(IPC_CHANNELS.searchLogs, (_event, filters: LogSearchFilters) =>
      this.logService.search(logSearchSchema.parse(filters)),
    );
    ipcMain.handle(IPC_CHANNELS.exportLogs, (_event, filters: LogSearchFilters) =>
      this.logService.export(logSearchSchema.parse(filters)),
    );
    ipcMain.handle(IPC_CHANNELS.clearLogIndex, (_event, scriptId?: string) => this.logService.clearIndex(scriptId));
    ipcMain.handle(IPC_CHANNELS.getSettings, () => this.settings.get());
    ipcMain.handle(IPC_CHANNELS.saveSettings, (_event, nextSettings: Partial<AppSettings>) => {
      const merged = appSettingsSchema.partial().parse(nextSettings);
      const saved = this.settings.save(merged);
      this.applyTheme(saved.theme);
      this.startupService.setEnabled(saved.openAtLogin);
      this.workspaceWatcher.start();
      this.healthMonitor.start();
      this.events.emit("settings-updated", { changedKeys: Object.keys(merged) });
      return saved;
    });
    ipcMain.handle(IPC_CHANNELS.wizardDetect, (_event, rootDir: string) => this.wizardService.detect(rootDir));
    ipcMain.handle(IPC_CHANNELS.wizardValidateManifest, (_event, content: string, rootDir: string) =>
      this.wizardService.validateManifest(content, rootDir),
    );
    ipcMain.handle(IPC_CHANNELS.wizardTestLaunch, (_event, manifest: ScriptManifest, rootDir: string) =>
      this.wizardService.testLaunch(manifestSchema.parse(manifest), rootDir),
    );
    ipcMain.handle(IPC_CHANNELS.wizardTestHealth, (_event, manifest: ScriptManifest, rootDir: string) =>
      this.wizardService.testHealth(manifestSchema.parse(manifest), rootDir),
    );
    ipcMain.handle(IPC_CHANNELS.wizardGenerateTemplate, (_event, input: WizardTemplateInput) =>
      this.wizardService.generateTemplate(input),
    );
    ipcMain.handle(IPC_CHANNELS.wizardImportExisting, (_event, sourceDir: string, workspaceRoot: string) =>
      this.wizardService.importExisting(sourceDir, workspaceRoot),
    );
    ipcMain.handle(IPC_CHANNELS.pluginsList, () => this.pluginRegistry.list(this.settings.get().scriptRoot));
    ipcMain.handle(IPC_CHANNELS.manifestSchema, () => this.wizardService.getManifestSchema());
  }
}
