export type SourceMode = "manifest" | "heuristic" | "imported-junction";

export type ScriptType =
  | "python"
  | "node"
  | "powershell"
  | "bat"
  | "exe"
  | "java"
  | "go"
  | "rust"
  | "unknown";

export type LifecycleState =
  | "discovered"
  | "indexed"
  | "ready"
  | "starting"
  | "running"
  | "unhealthy"
  | "unresponsive"
  | "stopping"
  | "stopped"
  | "crashed"
  | "disabled"
  | "missing"
  | "unconfigured";

export type HealthState = "healthy" | "degraded" | "failed" | "unknown";

export type DisplayStatus =
  | "运行中"
  | "已停止"
  | "启动中"
  | "停止中"
  | "异常退出"
  | "无响应"
  | "未配置"
  | "已禁用"
  | "已缺失";

export type RestartPolicy = "off" | "on-crash" | "on-crash-or-unresponsive";
export type CircuitState = "closed" | "open" | "half-open";

export type StopMode = "process" | "command" | "http" | "none";

export type ProbeType = "process" | "heartbeat-file" | "http" | "port" | "log-update";

export type ProbeSeverity = "required" | "advisory";

export type LogLevel = "TRACE" | "DEBUG" | "INFO" | "WARN" | "ERROR" | "FATAL" | "UNKNOWN";

export interface AppSettings {
  scriptRoot: string;
  autoScan: boolean;
  scanIntervalSeconds: number;
  healthIntervalSeconds: number;
  openAtLogin: boolean;
  theme: "system" | "dark" | "light";
  dataDirectory: string;
  trayEnabled: boolean;
  closeBehavior: "confirm" | "minimize-to-tray" | "exit";
  logRetentionDays: number;
  restartPolicy: RestartPolicy;
  restartMaxRetries: number;
  restartCooldownMinutes: number;
  restartBackoffSeconds: number[];
  defaultLogTailLines: number;
  unresponsiveTimeoutSeconds: number;
  logStaleSeconds: number;
  heartbeatStaleSeconds: number;
  processSampleIntervalSeconds: number;
}

export interface LaunchConfig {
  command: string;
  args: string[];
  cwd: string;
  env?: Record<string, string>;
  shell?: boolean;
}

export interface StopCommandConfig {
  command: string;
  args: string[];
  cwd?: string;
}

export interface StopHttpConfig {
  url: string;
  method?: "GET" | "POST";
  timeoutMs?: number;
}

export interface StopConfig {
  mode: StopMode;
  timeoutMs?: number;
  command?: StopCommandConfig;
  http?: StopHttpConfig;
}

export interface LoggingConfig {
  filePath?: string;
  maxTailLines?: number;
  levelPattern?: string;
  captureStdout?: boolean;
  captureStderr?: boolean;
}

export interface ProbeBase {
  type: ProbeType;
  severity: ProbeSeverity;
  timeoutMs?: number;
}

export interface ProcessProbe extends ProbeBase {
  type: "process";
}

export interface HeartbeatProbe extends ProbeBase {
  type: "heartbeat-file";
  path: string;
  staleAfterSeconds?: number;
}

export interface HttpProbe extends ProbeBase {
  type: "http";
  url: string;
  expectedStatus?: number;
}

export interface PortProbe extends ProbeBase {
  type: "port";
  port: number;
  host?: string;
}

export interface LogUpdateProbe extends ProbeBase {
  type: "log-update";
  path?: string;
  staleAfterSeconds?: number;
}

export type ProbeConfig = ProcessProbe | HeartbeatProbe | HttpProbe | PortProbe | LogUpdateProbe;

export interface HealthConfig {
  graceSeconds?: number;
  probes: ProbeConfig[];
}

export interface DisplayConfig {
  category: string;
  tags: string[];
  icon?: string;
}

export interface PolicyConfig {
  allowAutoStart: boolean;
  allowVisible: boolean;
  restartPolicy?: RestartPolicy;
  restartMaxRetries?: number;
  cooldownMinutes?: number;
}

export interface ProcessMatchConfig {
  executableName?: string;
  commandLineIncludes?: string;
}

export interface ScriptManifest {
  id: string;
  name: string;
  description: string;
  version: string;
  author: string;
  type: ScriptType;
  entry: LaunchConfig;
  stop: StopConfig;
  logging: LoggingConfig;
  health: HealthConfig;
  display: DisplayConfig;
  policy: PolicyConfig;
  processMatch?: ProcessMatchConfig;
  capabilities?: string[];
  extensions?: Record<string, unknown>;
}

export interface ScriptRecord {
  id: string;
  sourceMode: SourceMode;
  rootDir: string;
  manifestPath?: string;
  folderName: string;
  heuristicReason?: string;
  isConfigured: boolean;
  isMissing: boolean;
  manifest: ScriptManifest;
  smartCategory: string;
  smartTags: string[];
  classificationSource: "manifest" | "heuristic" | "hybrid";
  indexedAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface RuntimeResourceSample {
  cpuPercent: number | null;
  memoryMb: number | null;
  threadCount: number | null;
  runtimeSeconds: number | null;
  ports: number[];
  lastFileUpdateAt?: string;
}

export interface ScriptRuntimeSnapshot {
  scriptId: string;
  lifecycleState: LifecycleState;
  displayStatus: DisplayStatus;
  healthState: HealthState;
  desiredState: "running" | "stopped";
  pid?: number;
  lastStartedAt?: string;
  lastStoppedAt?: string;
  lastExitCode?: number;
  lastFailureReason?: string;
  uptimeStartedAt?: string;
  restartCount: number;
  faultCount: number;
  consecutiveFailures: number;
  circuitState: CircuitState;
  circuitOpenedAt?: string;
  circuitReason?: string;
  nextRetryAt?: string;
  externalProcess: boolean;
  lastHealthSummary?: string;
  resource: RuntimeResourceSample;
  updatedAt: string;
}

export interface ScriptSummary {
  record: ScriptRecord;
  runtime: ScriptRuntimeSnapshot;
}

export interface RunHistoryItem {
  id: number;
  scriptId: string;
  action: string;
  outcome: string;
  pid?: number;
  exitCode?: number;
  message?: string;
  startedAt?: string;
  endedAt?: string;
  durationSeconds?: number;
  triggeredBy: string;
  metadata: Record<string, unknown>;
}

export interface HealthCheckItem {
  id: number;
  scriptId: string;
  probeType: ProbeType;
  status: HealthState;
  message?: string;
  latencyMs?: number;
  createdAt: string;
  details: Record<string, unknown>;
}

export interface LogEvent {
  id: number;
  scriptId: string;
  timestamp: string;
  level: LogLevel;
  source: "stdout" | "stderr" | "file";
  message: string;
  raw: string;
  filePath?: string;
  lineNumber?: number;
}

export interface OverviewStats {
  totalScripts: number;
  runningCount: number;
  stoppedCount: number;
  crashedCount: number;
  unresponsiveCount: number;
  unconfiguredCount: number;
  todayStartCount: number;
  todayCrashCount: number;
}

export interface FaultTimelineItem {
  id: number;
  scriptId: string;
  kind: "crash" | "unresponsive" | "restart-scheduled" | "circuit-open" | "recovered" | "start-failed";
  title: string;
  detail?: string;
  occurredAt: string;
  severity: "info" | "warn" | "error";
}

export interface OverviewData {
  stats: OverviewStats;
  statusDistribution: Array<{ name: string; value: number }>;
  recentScripts: ScriptSummary[];
  recentCrashes: ScriptSummary[];
  recentEvents: RunHistoryItem[];
  faultTimeline: FaultTimelineItem[];
}

export interface ScriptFilters {
  search?: string;
  category?: string;
  tag?: string;
  status?: LifecycleState | DisplayStatus | "all";
  sortBy?: "name" | "recent" | "status" | "category";
}

export interface ScriptDetail {
  summary: ScriptSummary;
  runs: RunHistoryItem[];
  healthChecks: HealthCheckItem[];
  logs: LogEvent[];
  faultTimeline: FaultTimelineItem[];
}

export interface LogSearchFilters {
  scriptIds?: string[];
  levels?: LogLevel[];
  search?: string;
  from?: string;
  to?: string;
  limit?: number;
}

export interface WizardTemplateInput {
  templateType: "python" | "node" | "bat" | "exe-wrapper";
  targetDirectory: string;
  scriptId: string;
  name: string;
  description: string;
  author: string;
  category?: string;
  tags?: string[];
}

export interface WizardDetectResult {
  rootDir: string;
  detected: boolean;
  sourceMode: SourceMode;
  manifest?: ScriptManifest;
  heuristicReason?: string;
  warnings: string[];
  errors: string[];
}

export interface WizardLaunchResult {
  success: boolean;
  message: string;
  pid?: number;
  outputSnippet?: string;
}

export interface WizardHealthResult {
  success: boolean;
  message: string;
  checks: Array<{
    type: ProbeType;
    success: boolean;
    message: string;
  }>;
}

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  author: string;
  description?: string;
  apiVersion: 1;
  entry?: string;
  hooks: Array<"register-probes" | "classify-scripts" | "augment-dashboard" | "add-actions">;
}

export interface PluginDescriptor {
  manifest: PluginManifest;
  rootDir: string;
  manifestPath: string;
}

export interface AppEventPayloadMap {
  "scripts-updated": { changedScriptIds?: string[] };
  "overview-updated": { changed?: boolean };
  "script-runtime-updated": { scriptId: string };
  "logs-updated": { scriptId: string };
  "settings-updated": { changedKeys: string[] };
  "scan-completed": { rootDir: string; total: number };
  "health-updated": { scriptId: string };
}
