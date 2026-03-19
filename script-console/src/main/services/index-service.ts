import fs from "node:fs";
import path from "node:path";
import { shell } from "electron";
import {
  FaultTimelineItem,
  HealthCheckItem,
  LogEvent,
  OverviewData,
  RunHistoryItem,
  ScriptDetail,
  ScriptFilters,
  ScriptRecord,
  ScriptRuntimeSnapshot,
  ScriptSummary,
} from "@shared/types";
import { DEFAULT_PLUGIN_DIRECTORY_NAME, DEFAULT_TEMPLATE_DIRECTORY_NAME } from "@shared/constants";
import { DatabaseService } from "./database-service";
import { AuditService } from "./audit-service";
import { EventBus } from "./event-bus";
import { buildScriptRecord } from "@main/utils/script-manifest";
import { listFirstLevelDirectories } from "@main/utils/path-utils";
import { createDefaultRuntime } from "@main/utils/state-machine";
import { nowIso, startOfTodayIso } from "@main/utils/time-utils";

interface ScriptRow {
  id: string;
  source_mode: string;
  root_dir: string;
  manifest_path?: string;
  folder_name: string;
  heuristic_reason?: string;
  is_configured: number;
  is_missing: number;
  manifest_json: string;
  indexed_at: string;
  created_at: string;
  updated_at: string;
  lifecycle_state?: string;
  display_status?: string;
  health_state?: string;
  desired_state?: string;
  pid?: number;
  last_started_at?: string;
  last_stopped_at?: string;
  last_exit_code?: number;
  last_failure_reason?: string;
  uptime_started_at?: string;
  restart_count?: number;
  fault_count?: number;
  consecutive_failures?: number;
  circuit_state?: string;
  circuit_opened_at?: string;
  circuit_reason?: string;
  next_retry_at?: string;
  external_process?: number;
  last_health_summary?: string;
  resource_json?: string;
  runtime_updated_at?: string;
}

interface HistoryRow {
  id: number;
  script_id: string;
  action: string;
  outcome: string;
  pid?: number;
  exit_code?: number;
  message?: string;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  triggered_by: string;
  metadata_json: string;
}

function buildSmartClassification(manifest: ScriptRecord["manifest"], folderName: string) {
  const source = [folderName, manifest.name, manifest.description, manifest.type, ...manifest.display.tags]
    .join(" ")
    .toLowerCase();
  const smartTags = new Set<string>(manifest.display.tags);
  smartTags.add(manifest.type);
  let smartCategory = manifest.display.category || "未分类";
  let classificationSource: ScriptRecord["classificationSource"] =
    manifest.display.category || manifest.display.tags.length ? "hybrid" : "heuristic";

  if (source.includes("demo") || source.includes("sample")) smartTags.add("demo");
  if (source.includes("heartbeat") || source.includes("monitor") || source.includes("watch")) {
    smartTags.add("monitor");
    if (smartCategory === "未分类") smartCategory = "监控守护";
  }
  if (source.includes("server") || source.includes("http") || source.includes("port")) {
    smartTags.add("service");
    if (smartCategory === "未分类") smartCategory = "本地服务";
  }
  if (source.includes("batch") || source.includes("schedule") || source.includes("cron")) {
    smartTags.add("automation");
    if (smartCategory === "未分类") smartCategory = "定时自动化";
  }
  if (source.includes("data") || source.includes("etl") || source.includes("report")) {
    smartTags.add("data");
    if (smartCategory === "未分类") smartCategory = "数据处理";
  }
  if (smartCategory === manifest.display.category && smartTags.size === manifest.display.tags.length) {
    classificationSource = "manifest";
  }

  return {
    smartCategory,
    smartTags: [...smartTags].sort(),
    classificationSource,
  };
}

function hydrateHistory(row: HistoryRow): RunHistoryItem {
  return {
    id: row.id,
    scriptId: row.script_id,
    action: row.action,
    outcome: row.outcome,
    pid: row.pid ?? undefined,
    exitCode: row.exit_code ?? undefined,
    message: row.message ?? undefined,
    startedAt: row.started_at ?? undefined,
    endedAt: row.ended_at ?? undefined,
    durationSeconds: row.duration_seconds ?? undefined,
    triggeredBy: row.triggered_by,
    metadata: JSON.parse(row.metadata_json || "{}"),
  };
}

function hydrateSummary(row: ScriptRow): ScriptSummary {
  const manifest = JSON.parse(row.manifest_json);
  const classification = buildSmartClassification(manifest, row.folder_name);

  const record: ScriptRecord = {
    id: row.id,
    sourceMode: row.source_mode as ScriptRecord["sourceMode"],
    rootDir: row.root_dir,
    manifestPath: row.manifest_path,
    folderName: row.folder_name,
    heuristicReason: row.heuristic_reason,
    isConfigured: Boolean(row.is_configured),
    isMissing: Boolean(row.is_missing),
    manifest,
    smartCategory: classification.smartCategory,
    smartTags: classification.smartTags,
    classificationSource: classification.classificationSource,
    indexedAt: row.indexed_at,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };

  const fallbackRuntime = createDefaultRuntime(record);
  const runtime: ScriptRuntimeSnapshot = {
    ...fallbackRuntime,
    lifecycleState: (row.lifecycle_state as ScriptRuntimeSnapshot["lifecycleState"]) ?? fallbackRuntime.lifecycleState,
    displayStatus: (row.display_status as ScriptRuntimeSnapshot["displayStatus"]) ?? fallbackRuntime.displayStatus,
    healthState: (row.health_state as ScriptRuntimeSnapshot["healthState"]) ?? fallbackRuntime.healthState,
    desiredState: (row.desired_state as ScriptRuntimeSnapshot["desiredState"]) ?? fallbackRuntime.desiredState,
    pid: row.pid ?? undefined,
    lastStartedAt: row.last_started_at ?? undefined,
    lastStoppedAt: row.last_stopped_at ?? undefined,
    lastExitCode: row.last_exit_code ?? undefined,
    lastFailureReason: row.last_failure_reason ?? undefined,
    uptimeStartedAt: row.uptime_started_at ?? undefined,
    restartCount: row.restart_count ?? 0,
    faultCount: row.fault_count ?? 0,
    consecutiveFailures: row.consecutive_failures ?? 0,
    circuitState: (row.circuit_state as ScriptRuntimeSnapshot["circuitState"]) ?? "closed",
    circuitOpenedAt: row.circuit_opened_at ?? undefined,
    circuitReason: row.circuit_reason ?? undefined,
    nextRetryAt: row.next_retry_at ?? undefined,
    externalProcess: Boolean(row.external_process),
    lastHealthSummary: row.last_health_summary ?? undefined,
    resource: row.resource_json ? JSON.parse(row.resource_json) : fallbackRuntime.resource,
    updatedAt: row.runtime_updated_at ?? fallbackRuntime.updatedAt,
  };

  return { record, runtime };
}

function mapFaultTimelineItem(row: HistoryRow): FaultTimelineItem {
  const occurredAt = row.ended_at ?? row.started_at ?? nowIso();
  const base = {
    id: row.id,
    scriptId: row.script_id,
    occurredAt,
  };

  if (row.outcome === "crashed") {
    return {
      ...base,
      kind: "crash",
      title: "脚本异常退出",
      detail: row.message ?? undefined,
      severity: "error",
    };
  }
  if (row.outcome === "unresponsive") {
    return {
      ...base,
      kind: "unresponsive",
      title: "脚本无响应",
      detail: row.message ?? undefined,
      severity: "error",
    };
  }
  if (row.outcome === "restart-scheduled") {
    return {
      ...base,
      kind: "restart-scheduled",
      title: "已安排自动重启",
      detail: row.message ?? undefined,
      severity: "warn",
    };
  }
  if (row.outcome === "circuit-open") {
    return {
      ...base,
      kind: "circuit-open",
      title: "连续失败已熔断",
      detail: row.message ?? undefined,
      severity: "error",
    };
  }
  if (row.outcome === "recovered") {
    return {
      ...base,
      kind: "recovered",
      title: "脚本恢复运行",
      detail: row.message ?? undefined,
      severity: "info",
    };
  }
  return {
    ...base,
    kind: "start-failed",
    title: "启动失败",
    detail: row.message ?? undefined,
    severity: "warn",
  };
}

export class IndexService {
  private readonly ignoredFolderNames = new Set([
    ".github",
    ".vscode",
    ".tmp-clawhub-vet",
    "__pycache__",
    DEFAULT_PLUGIN_DIRECTORY_NAME,
    DEFAULT_TEMPLATE_DIRECTORY_NAME,
    "script-console",
  ]);

  constructor(
    private readonly db: DatabaseService,
    private readonly audit: AuditService,
    private readonly events: EventBus,
  ) {}

  private upsertScript(record: ScriptRecord): void {
    const existing = this.db.get<{ created_at: string }>("SELECT created_at FROM scripts WHERE id = :id", {
      id: record.id,
    });
    const createdAt = existing?.created_at ?? record.createdAt;

    this.db.run(
      `
      INSERT INTO scripts(
        id, source_mode, root_dir, manifest_path, folder_name, heuristic_reason,
        is_configured, is_missing, manifest_json, indexed_at, created_at, updated_at
      )
      VALUES(
        :id, :sourceMode, :rootDir, :manifestPath, :folderName, :heuristicReason,
        :isConfigured, :isMissing, :manifestJson, :indexedAt, :createdAt, :updatedAt
      )
      ON CONFLICT(id) DO UPDATE SET
        source_mode = excluded.source_mode,
        root_dir = excluded.root_dir,
        manifest_path = excluded.manifest_path,
        folder_name = excluded.folder_name,
        heuristic_reason = excluded.heuristic_reason,
        is_configured = excluded.is_configured,
        is_missing = excluded.is_missing,
        manifest_json = excluded.manifest_json,
        indexed_at = excluded.indexed_at,
        updated_at = excluded.updated_at
      `,
      {
        id: record.id,
        sourceMode: record.sourceMode,
        rootDir: record.rootDir,
        manifestPath: record.manifestPath ?? null,
        folderName: record.folderName,
        heuristicReason: record.heuristicReason ?? null,
        isConfigured: record.isConfigured ? 1 : 0,
        isMissing: record.isMissing ? 1 : 0,
        manifestJson: JSON.stringify(record.manifest),
        indexedAt: record.indexedAt,
        createdAt,
        updatedAt: record.updatedAt,
      },
    );

    const runtime = this.db.get<{ script_id: string }>(
      "SELECT script_id FROM script_runtime WHERE script_id = :scriptId",
      { scriptId: record.id },
    );
    if (!runtime) {
      this.upsertRuntime(createDefaultRuntime(record));
    }
  }

  upsertRuntime(runtime: ScriptRuntimeSnapshot): void {
    this.db.run(
      `
      INSERT INTO script_runtime(
        script_id, lifecycle_state, display_status, health_state, desired_state,
        pid, last_started_at, last_stopped_at, last_exit_code, last_failure_reason,
        uptime_started_at, restart_count, fault_count, consecutive_failures,
        circuit_state, circuit_opened_at, circuit_reason, next_retry_at,
        external_process, last_health_summary, resource_json, updated_at
      )
      VALUES(
        :scriptId, :lifecycleState, :displayStatus, :healthState, :desiredState,
        :pid, :lastStartedAt, :lastStoppedAt, :lastExitCode, :lastFailureReason,
        :uptimeStartedAt, :restartCount, :faultCount, :consecutiveFailures,
        :circuitState, :circuitOpenedAt, :circuitReason, :nextRetryAt,
        :externalProcess, :lastHealthSummary, :resourceJson, :updatedAt
      )
      ON CONFLICT(script_id) DO UPDATE SET
        lifecycle_state = excluded.lifecycle_state,
        display_status = excluded.display_status,
        health_state = excluded.health_state,
        desired_state = excluded.desired_state,
        pid = excluded.pid,
        last_started_at = excluded.last_started_at,
        last_stopped_at = excluded.last_stopped_at,
        last_exit_code = excluded.last_exit_code,
        last_failure_reason = excluded.last_failure_reason,
        uptime_started_at = excluded.uptime_started_at,
        restart_count = excluded.restart_count,
        fault_count = excluded.fault_count,
        consecutive_failures = excluded.consecutive_failures,
        circuit_state = excluded.circuit_state,
        circuit_opened_at = excluded.circuit_opened_at,
        circuit_reason = excluded.circuit_reason,
        next_retry_at = excluded.next_retry_at,
        external_process = excluded.external_process,
        last_health_summary = excluded.last_health_summary,
        resource_json = excluded.resource_json,
        updated_at = excluded.updated_at
      `,
      {
        scriptId: runtime.scriptId,
        lifecycleState: runtime.lifecycleState,
        displayStatus: runtime.displayStatus,
        healthState: runtime.healthState,
        desiredState: runtime.desiredState,
        pid: runtime.pid ?? null,
        lastStartedAt: runtime.lastStartedAt ?? null,
        lastStoppedAt: runtime.lastStoppedAt ?? null,
        lastExitCode: runtime.lastExitCode ?? null,
        lastFailureReason: runtime.lastFailureReason ?? null,
        uptimeStartedAt: runtime.uptimeStartedAt ?? null,
        restartCount: runtime.restartCount,
        faultCount: runtime.faultCount,
        consecutiveFailures: runtime.consecutiveFailures,
        circuitState: runtime.circuitState,
        circuitOpenedAt: runtime.circuitOpenedAt ?? null,
        circuitReason: runtime.circuitReason ?? null,
        nextRetryAt: runtime.nextRetryAt ?? null,
        externalProcess: runtime.externalProcess ? 1 : 0,
        lastHealthSummary: runtime.lastHealthSummary ?? null,
        resourceJson: JSON.stringify(runtime.resource),
        updatedAt: runtime.updatedAt,
      },
    );
  }

  scanWorkspace(rootDir: string): ScriptSummary[] {
    const directories = listFirstLevelDirectories(rootDir).filter((dir) => {
      const folderName = path.basename(dir);
      return !this.ignoredFolderNames.has(folderName);
    });

    const foundIds = new Set<string>();
    const now = nowIso();

    this.db.transaction(() => {
      for (const dir of directories) {
        const record = buildScriptRecord(dir);
        if (!record) {
          continue;
        }
        foundIds.add(record.id);
        this.upsertScript({
          ...record,
          indexedAt: now,
          updatedAt: now,
        });
      }

      const existing = this.db.all<{ id: string; root_dir: string }>(
        "SELECT id, root_dir FROM scripts WHERE root_dir LIKE :rootPrefix",
        { rootPrefix: `${rootDir}%` },
      );

      for (const row of existing) {
        if (foundIds.has(row.id) || fs.existsSync(row.root_dir)) {
          continue;
        }
        this.db.run("UPDATE scripts SET is_missing = 1, updated_at = :updatedAt WHERE id = :id", {
          id: row.id,
          updatedAt: now,
        });
        const summary = this.getScriptSummary(row.id);
        if (summary) {
          this.upsertRuntime({
            ...summary.runtime,
            lifecycleState: "missing",
            displayStatus: "已缺失",
            healthState: "failed",
            updatedAt: now,
          });
        }
      }

      this.db.run(
        `
        INSERT INTO scan_events(event_type, root_dir, summary, created_at, payload_json)
        VALUES(:eventType, :rootDir, :summary, :createdAt, :payloadJson)
        `,
        {
          eventType: "scan",
          rootDir,
          summary: `扫描完成，共识别 ${foundIds.size} 个脚本`,
          createdAt: now,
          payloadJson: JSON.stringify({ total: foundIds.size }),
        },
      );
    });

    this.audit.record({
      action: "scanWorkspace",
      success: true,
      message: `扫描完成，共识别 ${foundIds.size} 个脚本`,
      payload: { rootDir, total: foundIds.size },
    });

    this.events.emit("scan-completed", { rootDir, total: foundIds.size });
    this.events.emit("scripts-updated", {});
    this.events.emit("overview-updated", { changed: true });
    return this.listScripts();
  }

  listScripts(filters?: ScriptFilters): ScriptSummary[] {
    const rows = this.db.all<ScriptRow>(
      `
      SELECT
        s.*,
        r.lifecycle_state,
        r.display_status,
        r.health_state,
        r.desired_state,
        r.pid,
        r.last_started_at,
        r.last_stopped_at,
        r.last_exit_code,
        r.last_failure_reason,
        r.uptime_started_at,
        r.restart_count,
        r.fault_count,
        r.consecutive_failures,
        r.circuit_state,
        r.circuit_opened_at,
        r.circuit_reason,
        r.next_retry_at,
        r.external_process,
        r.last_health_summary,
        r.resource_json,
        r.updated_at AS runtime_updated_at
      FROM scripts s
      LEFT JOIN script_runtime r ON r.script_id = s.id
      ORDER BY s.updated_at DESC
      `,
    );

    let result = rows.map(hydrateSummary);

    if (filters?.search) {
      const search = filters.search.trim().toLowerCase();
      result = result.filter((item) => {
        const haystack = [
          item.record.id,
          item.record.manifest.name,
          item.record.manifest.description,
          item.record.smartCategory,
          ...item.record.smartTags,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(search);
      });
    }

    if (filters?.category) {
      result = result.filter((item) => item.record.smartCategory === filters.category);
    }

    if (filters?.tag) {
      result = result.filter((item) => item.record.smartTags.includes(filters.tag!));
    }

    if (filters?.status && filters.status !== "all") {
      result = result.filter(
        (item) =>
          item.runtime.lifecycleState === filters.status || item.runtime.displayStatus === filters.status,
      );
    }

    switch (filters?.sortBy) {
      case "name":
        result = result.sort((a, b) => a.record.manifest.name.localeCompare(b.record.manifest.name));
        break;
      case "status":
        result = result.sort((a, b) => a.runtime.displayStatus.localeCompare(b.runtime.displayStatus));
        break;
      case "category":
        result = result.sort((a, b) => a.record.smartCategory.localeCompare(b.record.smartCategory));
        break;
      case "recent":
      default:
        result = result.sort((a, b) => b.record.updatedAt.localeCompare(a.record.updatedAt));
        break;
    }

    return result;
  }

  getScriptSummary(scriptId: string): ScriptSummary | undefined {
    const row = this.db.get<ScriptRow>(
      `
      SELECT
        s.*,
        r.lifecycle_state,
        r.display_status,
        r.health_state,
        r.desired_state,
        r.pid,
        r.last_started_at,
        r.last_stopped_at,
        r.last_exit_code,
        r.last_failure_reason,
        r.uptime_started_at,
        r.restart_count,
        r.fault_count,
        r.consecutive_failures,
        r.circuit_state,
        r.circuit_opened_at,
        r.circuit_reason,
        r.next_retry_at,
        r.external_process,
        r.last_health_summary,
        r.resource_json,
        r.updated_at AS runtime_updated_at
      FROM scripts s
      LEFT JOIN script_runtime r ON r.script_id = s.id
      WHERE s.id = :scriptId
      `,
      { scriptId },
    );
    return row ? hydrateSummary(row) : undefined;
  }

  getFaultTimeline(scriptId?: string, limit = 40): FaultTimelineItem[] {
    const rows = this.db.all<HistoryRow>(
      `
      SELECT *
      FROM run_history
      WHERE outcome IN ('crashed', 'unresponsive', 'restart-scheduled', 'circuit-open', 'recovered', 'start-failed')
      ${scriptId ? "AND script_id = :scriptId" : ""}
      ORDER BY id DESC
      LIMIT :limit
      `,
      {
        scriptId,
        limit,
      },
    );
    return rows.map(mapFaultTimelineItem);
  }

  getScriptDetail(scriptId: string): ScriptDetail | undefined {
    const summary = this.getScriptSummary(scriptId);
    if (!summary) {
      return undefined;
    }

    const runs = this.db
      .all<HistoryRow>(
        `
        SELECT *
        FROM run_history
        WHERE script_id = :scriptId
        ORDER BY id DESC
        LIMIT 80
        `,
        { scriptId },
      )
      .map(hydrateHistory);

    const healthChecks = this.db
      .all<HealthCheckItem & { details_json: string }>(
        `
        SELECT *, details_json
        FROM health_checks
        WHERE script_id = :scriptId
        ORDER BY id DESC
        LIMIT 80
        `,
        { scriptId },
      )
      .map((item) => ({
        ...item,
        details: JSON.parse(item.details_json || "{}"),
      }));

    const logs = this.db.all<LogEvent>(
      `
      SELECT
        id,
        script_id AS scriptId,
        timestamp,
        level,
        source,
        message,
        raw,
        file_path AS filePath,
        line_number AS lineNumber
      FROM log_events
      WHERE script_id = :scriptId
      ORDER BY id DESC
      LIMIT 250
      `,
      { scriptId },
    );

    return {
      summary,
      runs,
      healthChecks,
      logs,
      faultTimeline: this.getFaultTimeline(scriptId, 40),
    };
  }

  recordRun(item: Omit<RunHistoryItem, "id">): void {
    this.db.run(
      `
      INSERT INTO run_history(
        script_id, action, outcome, pid, exit_code, message, started_at, ended_at,
        duration_seconds, triggered_by, metadata_json
      )
      VALUES(
        :scriptId, :action, :outcome, :pid, :exitCode, :message, :startedAt, :endedAt,
        :durationSeconds, :triggeredBy, :metadataJson
      )
      `,
      {
        scriptId: item.scriptId,
        action: item.action,
        outcome: item.outcome,
        pid: item.pid ?? null,
        exitCode: item.exitCode ?? null,
        message: item.message ?? null,
        startedAt: item.startedAt ?? null,
        endedAt: item.endedAt ?? null,
        durationSeconds: item.durationSeconds ?? null,
        triggeredBy: item.triggeredBy,
        metadataJson: JSON.stringify(item.metadata ?? {}),
      },
    );
    this.events.emit("overview-updated", { changed: true });
  }

  recordHealthCheck(item: Omit<HealthCheckItem, "id">): void {
    this.db.run(
      `
      INSERT INTO health_checks(script_id, probe_type, status, message, latency_ms, created_at, details_json)
      VALUES(:scriptId, :probeType, :status, :message, :latencyMs, :createdAt, :detailsJson)
      `,
      {
        scriptId: item.scriptId,
        probeType: item.probeType,
        status: item.status,
        message: item.message ?? null,
        latencyMs: item.latencyMs ?? null,
        createdAt: item.createdAt,
        detailsJson: JSON.stringify(item.details ?? {}),
      },
    );
    this.events.emit("health-updated", { scriptId: item.scriptId });
  }

  getOverview(): OverviewData {
    const scripts = this.listScripts();
    const today = startOfTodayIso();
    const recentEvents = this.db
      .all<HistoryRow>(
        `
        SELECT *
        FROM run_history
        ORDER BY id DESC
        LIMIT 30
        `,
      )
      .map(hydrateHistory);

    const todayStartCount =
      this.db.get<{ count: number }>(
        "SELECT COUNT(*) AS count FROM run_history WHERE action = 'start' AND started_at >= :today",
        { today },
      )?.count ?? 0;
    const todayCrashCount =
      this.db.get<{ count: number }>(
        "SELECT COUNT(*) AS count FROM run_history WHERE outcome IN ('crashed', 'unresponsive', 'circuit-open') AND started_at >= :today",
        { today },
      )?.count ?? 0;

    const stats = {
      totalScripts: scripts.length,
      runningCount: scripts.filter((item) => item.runtime.lifecycleState === "running").length,
      stoppedCount: scripts.filter((item) => item.runtime.lifecycleState === "stopped").length,
      crashedCount: scripts.filter((item) => item.runtime.lifecycleState === "crashed").length,
      unresponsiveCount: scripts.filter((item) => item.runtime.lifecycleState === "unresponsive").length,
      unconfiguredCount: scripts.filter((item) => item.runtime.lifecycleState === "unconfigured").length,
      todayStartCount,
      todayCrashCount,
    };

    const distributionMap = new Map<string, number>();
    for (const script of scripts) {
      distributionMap.set(
        script.runtime.displayStatus,
        (distributionMap.get(script.runtime.displayStatus) ?? 0) + 1,
      );
    }

    return {
      stats,
      statusDistribution: [...distributionMap.entries()].map(([name, value]) => ({ name, value })),
      recentScripts: [...scripts]
        .sort((a, b) => b.record.indexedAt.localeCompare(a.record.indexedAt))
        .slice(0, 6),
      recentCrashes: scripts
        .filter((item) =>
          ["crashed", "unresponsive"].includes(item.runtime.lifecycleState),
        )
        .slice(0, 6),
      recentEvents,
      faultTimeline: this.getFaultTimeline(undefined, 24),
    };
  }

  getCategories(): string[] {
    return [...new Set(this.listScripts().map((item) => item.record.smartCategory))].sort();
  }

  getTags(): string[] {
    return [...new Set(this.listScripts().flatMap((item) => item.record.smartTags))].sort();
  }

  async openScriptFolder(scriptId: string): Promise<void> {
    const summary = this.getScriptSummary(scriptId);
    if (!summary) {
      throw new Error("脚本不存在");
    }
    await shell.openPath(summary.record.rootDir);
  }
}
