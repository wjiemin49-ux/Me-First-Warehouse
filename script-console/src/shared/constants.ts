export const APP_NAME = "Script Console";
export const APP_PRODUCT_NAME = "本地离线脚本中控台";
export const APP_PROTOCOL_VERSION = 1;
export const DEFAULT_SCRIPT_ROOT = "D:\\me\\脚本";
export const DEFAULT_SCAN_INTERVAL_SECONDS = 30;
export const DEFAULT_HEALTH_INTERVAL_SECONDS = 10;
export const DEFAULT_HEARTBEAT_STALE_SECONDS = 45;
export const DEFAULT_UNRESPONSIVE_TIMEOUT_SECONDS = 30;
export const DEFAULT_LOG_STALE_SECONDS = 120;
export const DEFAULT_MAX_LOG_LINES = 500;
export const DEFAULT_MAX_RESTART_RETRIES = 5;
export const DEFAULT_RESTART_COOLDOWN_MINUTES = 10;
export const DEFAULT_RETRY_BACKOFF_SECONDS = [5, 10, 20, 40, 60];
export const DEFAULT_SAMPLE_SCRIPT_PREFIX = "sc-demo";
export const DEFAULT_PLUGIN_DIRECTORY_NAME = ".script-console-plugins";
export const DEFAULT_TEMPLATE_DIRECTORY_NAME = ".script-console-templates";
export const ALLOWED_EXECUTABLES = [
  "python",
  "py",
  "node",
  "npm",
  "pwsh",
  "powershell",
  "cmd",
];

export const APP_EVENT_CHANNEL = "app:event";

export const IPC_CHANNELS = {
  getOverview: "app.getOverview",
  listScripts: "scripts.list",
  getScriptDetail: "scripts.getDetail",
  startScript: "scripts.start",
  stopScript: "scripts.stop",
  restartScript: "scripts.restart",
  forceKillScript: "scripts.forceKill",
  rescanScripts: "scripts.rescan",
  openFolder: "scripts.openFolder",
  getLogs: "logs.tail",
  searchLogs: "logs.search",
  exportLogs: "logs.export",
  clearLogIndex: "logs.clearIndex",
  getSettings: "settings.get",
  saveSettings: "settings.save",
  wizardDetect: "wizard.detect",
  wizardValidateManifest: "wizard.validateManifest",
  wizardTestLaunch: "wizard.testLaunch",
  wizardTestHealth: "wizard.testHealth",
  wizardGenerateTemplate: "wizard.generateTemplate",
  wizardImportExisting: "wizard.importExisting",
  pluginsList: "plugins.list",
  manifestSchema: "manifest.schema",
} as const;

export const APP_EVENTS = {
  scriptsUpdated: "scripts-updated",
  overviewUpdated: "overview-updated",
  scriptRuntimeUpdated: "script-runtime-updated",
  logsUpdated: "logs-updated",
  settingsUpdated: "settings-updated",
  scanCompleted: "scan-completed",
  healthUpdated: "health-updated",
} as const;
