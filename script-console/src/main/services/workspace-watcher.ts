import chokidar, { FSWatcher } from "chokidar";
import path from "node:path";
import { AppSettings } from "@shared/types";

export class WorkspaceWatcher {
  private watcher?: FSWatcher;
  private debounceTimer?: NodeJS.Timeout;
  private periodicTimer?: NodeJS.Timeout;

  constructor(
    private readonly getSettings: () => AppSettings,
    private readonly onRescanRequested: (rootDir: string) => void,
  ) {}

  start(): void {
    const settings = this.getSettings();
    this.stop();
    if (!settings.autoScan) {
      return;
    }
    this.watcher = chokidar.watch(settings.scriptRoot, {
      ignoreInitial: true,
      depth: 2,
      awaitWriteFinish: {
        stabilityThreshold: 500,
        pollInterval: 100,
      },
      ignored: (candidatePath) => {
        const folderName = path.basename(candidatePath);
        return folderName === ".github" || folderName === ".vscode" || folderName === "__pycache__";
      },
    });

    const scheduleRescan = () => {
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer);
      }
      this.debounceTimer = setTimeout(() => this.onRescanRequested(settings.scriptRoot), 800);
    };

    this.watcher
      .on("addDir", scheduleRescan)
      .on("unlinkDir", scheduleRescan)
      .on("add", scheduleRescan)
      .on("unlink", scheduleRescan)
      .on("change", scheduleRescan);

    this.periodicTimer = setInterval(() => {
      this.onRescanRequested(settings.scriptRoot);
    }, settings.scanIntervalSeconds * 1000);
  }

  stop(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = undefined;
    }
    if (this.periodicTimer) {
      clearInterval(this.periodicTimer);
      this.periodicTimer = undefined;
    }
    this.watcher?.close();
    this.watcher = undefined;
  }
}
