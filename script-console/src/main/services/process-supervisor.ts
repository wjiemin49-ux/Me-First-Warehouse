import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { AppSettings, RestartPolicy, ScriptManifest, ScriptSummary } from "@shared/types";
import { AuditService } from "./audit-service";
import { EventBus } from "./event-bus";
import { IndexService } from "./index-service";
import { LogService } from "./log-service";
import { ResourceSampler } from "./resource-sampler";
import { nowIso, secondsBetween } from "@main/utils/time-utils";
import { withRuntimeState } from "@main/utils/state-machine";

interface ManagedProcess {
  child: ChildProcessWithoutNullStreams;
  cleanupLogs: () => void;
  desiredState: "running" | "stopped";
}

function hasCapability(manifest: ScriptManifest, capability: string): boolean {
  return (manifest.capabilities ?? []).includes(capability);
}

function resolveWindowsCommand(command: string): string {
  if (process.platform !== "win32") {
    return command;
  }
  const lower = command.toLowerCase();
  if (lower === "npm") return "npm.cmd";
  if (lower === "npx") return "npx.cmd";
  if (lower === "pnpm") return "pnpm.cmd";
  if (lower === "yarn") return "yarn.cmd";
  return command;
}

export class ProcessSupervisor {
  private readonly managedProcesses = new Map<string, ManagedProcess>();
  private readonly restartTimers = new Map<string, NodeJS.Timeout>();

  constructor(
    private readonly indexService: IndexService,
    private readonly audit: AuditService,
    private readonly events: EventBus,
    private readonly logService: LogService,
    private readonly resourceSampler: ResourceSampler,
    private readonly getSettings: () => AppSettings,
  ) {}

  private resolveRestartPolicy(summary: ScriptSummary): RestartPolicy {
    return summary.record.manifest.policy.restartPolicy ?? this.getSettings().restartPolicy;
  }

  private resolveRestartLimit(summary: ScriptSummary): number {
    return summary.record.manifest.policy.restartMaxRetries ?? this.getSettings().restartMaxRetries;
  }

  private resolveCooldownMinutes(summary: ScriptSummary): number {
    return summary.record.manifest.policy.cooldownMinutes ?? this.getSettings().restartCooldownMinutes;
  }

  private clearRestartTimer(scriptId: string): void {
    const timer = this.restartTimers.get(scriptId);
    if (timer) {
      clearTimeout(timer);
      this.restartTimers.delete(scriptId);
    }
  }

  private async forceKillByPid(pid: number): Promise<void> {
    await new Promise<void>((resolve) => {
      const killer = spawn("taskkill", ["/PID", String(pid), "/T", "/F"], {
        windowsHide: true,
        shell: false,
      });
      killer.on("close", () => resolve());
      killer.on("error", () => resolve());
    });
  }

  private openCircuit(summary: ScriptSummary, reason: string): void {
    const cooldownMinutes = this.resolveCooldownMinutes(summary);
    const reopenAt = new Date(Date.now() + cooldownMinutes * 60_000).toISOString();
    const runtime = withRuntimeState(summary.runtime, "crashed", {
      desiredState: "stopped",
      circuitState: "open",
      circuitOpenedAt: nowIso(),
      circuitReason: reason,
      nextRetryAt: reopenAt,
    });
    this.indexService.upsertRuntime(runtime);
    this.indexService.recordRun({
      scriptId: summary.record.id,
      action: "circuit-breaker",
      outcome: "circuit-open",
      pid: summary.runtime.pid,
      message: reason,
      startedAt: runtime.lastStartedAt,
      endedAt: runtime.updatedAt,
      triggeredBy: "system",
      metadata: { reopenAt },
    });

    this.clearRestartTimer(summary.record.id);
    const timer = setTimeout(() => {
      this.restartTimers.delete(summary.record.id);
      void this.tryHalfOpenRestart(summary.record.id);
    }, cooldownMinutes * 60_000);
    this.restartTimers.set(summary.record.id, timer);
  }

  private async tryHalfOpenRestart(scriptId: string): Promise<void> {
    const summary = this.indexService.getScriptSummary(scriptId);
    if (!summary || summary.runtime.circuitState !== "open") {
      return;
    }
    this.indexService.upsertRuntime(
      withRuntimeState(summary.runtime, "starting", {
        circuitState: "half-open",
        nextRetryAt: undefined,
        circuitReason: "冷却结束，准备半开重试",
      }),
    );
    await this.startScript(scriptId, "circuit-half-open");
  }

  private scheduleRestart(scriptId: string): void {
    const summary = this.indexService.getScriptSummary(scriptId);
    if (!summary) {
      return;
    }
    const policy = this.resolveRestartPolicy(summary);
    if (policy === "off") {
      return;
    }
    if (hasCapability(summary.record.manifest, "oneshot")) {
      return;
    }

    const maxRetries = this.resolveRestartLimit(summary);
    if (summary.runtime.consecutiveFailures >= maxRetries) {
      this.openCircuit(summary, `连续失败 ${summary.runtime.consecutiveFailures} 次，已触发熔断`);
      return;
    }

    this.clearRestartTimer(scriptId);
    const settings = this.getSettings();
    const delaySeconds =
      settings.restartBackoffSeconds[
        Math.min(summary.runtime.restartCount, settings.restartBackoffSeconds.length - 1)
      ] ?? settings.restartBackoffSeconds.at(-1) ?? 5;

    const nextRetryAt = new Date(Date.now() + delaySeconds * 1000).toISOString();
    const pendingRuntime = withRuntimeState(summary.runtime, "starting", {
      restartCount: summary.runtime.restartCount + 1,
      desiredState: "running",
      nextRetryAt,
      lastFailureReason: `将在 ${delaySeconds}s 后自动重启`,
    });
    this.indexService.upsertRuntime(pendingRuntime);
    this.indexService.recordRun({
      scriptId,
      action: "restart",
      outcome: "restart-scheduled",
      pid: summary.runtime.pid,
      message: `计划在 ${delaySeconds}s 后重启`,
      startedAt: summary.runtime.lastStartedAt,
      endedAt: pendingRuntime.updatedAt,
      triggeredBy: "system",
      metadata: { delaySeconds, nextRetryAt },
    });
    this.events.emit("script-runtime-updated", { scriptId });

    const timer = setTimeout(() => {
      this.restartTimers.delete(scriptId);
      void this.startScript(scriptId, "auto-restart");
    }, delaySeconds * 1000);
    this.restartTimers.set(scriptId, timer);
  }

  private async handleProcessExit(scriptId: string, exitCode: number | null): Promise<void> {
    const summary = this.indexService.getScriptSummary(scriptId);
    if (!summary) {
      return;
    }
    const managed = this.managedProcesses.get(scriptId);
    const exitedNormally = exitCode === 0 && hasCapability(summary.record.manifest, "oneshot");
    const expectedStop = managed?.desiredState === "stopped" || exitedNormally;
    managed?.cleanupLogs();
    this.managedProcesses.delete(scriptId);

    const nextRuntime = withRuntimeState(
      {
        ...summary.runtime,
        pid: undefined,
        lastStoppedAt: nowIso(),
        lastExitCode: exitCode ?? undefined,
        lastFailureReason: expectedStop ? undefined : "脚本进程异常退出",
        uptimeStartedAt: undefined,
      },
      expectedStop ? "stopped" : "crashed",
      {
        desiredState: "stopped",
        faultCount: expectedStop ? summary.runtime.faultCount : summary.runtime.faultCount + 1,
        consecutiveFailures: expectedStop ? 0 : summary.runtime.consecutiveFailures + 1,
        circuitState: expectedStop ? "closed" : summary.runtime.circuitState,
        circuitOpenedAt: expectedStop ? undefined : summary.runtime.circuitOpenedAt,
        circuitReason: expectedStop ? undefined : summary.runtime.circuitReason,
        nextRetryAt: undefined,
      },
    );
    this.indexService.upsertRuntime(nextRuntime);
    this.indexService.recordRun({
      scriptId,
      action: "exit",
      outcome: expectedStop ? "stopped" : "crashed",
      pid: summary.runtime.pid,
      exitCode: exitCode ?? undefined,
      message: expectedStop ? "脚本已停止" : "脚本异常退出",
      startedAt: summary.runtime.lastStartedAt,
      endedAt: nextRuntime.lastStoppedAt,
      durationSeconds: secondsBetween(summary.runtime.lastStartedAt, nextRuntime.lastStoppedAt),
      triggeredBy: expectedStop ? "user" : "system",
      metadata: {},
    });
    this.audit.record({
      scriptId,
      action: expectedStop ? "stop-complete" : "crash-detected",
      success: expectedStop,
      message: expectedStop ? "脚本已停止" : `退出码: ${exitCode ?? "unknown"}`,
    });
    this.events.emit("script-runtime-updated", { scriptId });
    this.events.emit("overview-updated", { changed: true });

    if (!expectedStop) {
      this.scheduleRestart(scriptId);
    }
  }

  async startScript(scriptId: string, triggeredBy = "user"): Promise<ScriptSummary> {
    this.clearRestartTimer(scriptId);
    const summary = this.indexService.getScriptSummary(scriptId);
    if (!summary) {
      throw new Error("脚本不存在");
    }
    if (summary.runtime.lifecycleState === "running" || summary.runtime.lifecycleState === "starting") {
      return summary;
    }
    if (summary.runtime.circuitState === "open" && triggeredBy !== "user") {
      return summary;
    }

    const preparingRuntime = withRuntimeState(summary.runtime, "starting", {
      desiredState: "running",
      lastFailureReason: undefined,
      externalProcess: false,
      circuitState: summary.runtime.circuitState === "open" ? "half-open" : summary.runtime.circuitState,
      nextRetryAt: undefined,
    });
    this.indexService.upsertRuntime(preparingRuntime);
    this.events.emit("script-runtime-updated", { scriptId });

    const child = spawn(resolveWindowsCommand(summary.record.manifest.entry.command), summary.record.manifest.entry.args, {
      cwd: summary.record.manifest.entry.cwd,
      env: {
        ...process.env,
        ...summary.record.manifest.entry.env,
      },
      shell: false,
      windowsHide: true,
      stdio: "pipe",
    });

    const cleanupLogs = this.logService.attachProcessStreams(summary, child);
    this.managedProcesses.set(scriptId, {
      child,
      cleanupLogs,
      desiredState: "running",
    });

    if (summary.record.manifest.logging.filePath) {
      this.logService.watchExternalLogFile(scriptId, summary.record.manifest.logging.filePath);
    }

    child.once("spawn", () => {
      const updated = this.indexService.getScriptSummary(scriptId);
      if (!updated) {
        return;
      }
      const hadFailures = updated.runtime.consecutiveFailures > 0 || updated.runtime.circuitState !== "closed";
      const nextRuntime = withRuntimeState(updated.runtime, "running", {
        pid: child.pid,
        desiredState: "running",
        lastStartedAt: nowIso(),
        uptimeStartedAt: nowIso(),
        externalProcess: false,
        consecutiveFailures: 0,
        circuitState: "closed",
        circuitOpenedAt: undefined,
        circuitReason: undefined,
        nextRetryAt: undefined,
      });
      this.indexService.upsertRuntime(nextRuntime);
      this.indexService.recordRun({
        scriptId,
        action: "start",
        outcome: hadFailures ? "recovered" : "started",
        pid: child.pid,
        startedAt: nextRuntime.lastStartedAt,
        triggeredBy,
        metadata: {},
      });
      this.events.emit("script-runtime-updated", { scriptId });
      this.events.emit("overview-updated", { changed: true });
    });

    child.once("error", (error) => {
      const failed = this.indexService.getScriptSummary(scriptId);
      if (!failed) {
        return;
      }
      const nextRuntime = withRuntimeState(failed.runtime, "crashed", {
        lastFailureReason: error.message,
        desiredState: "stopped",
        pid: undefined,
        consecutiveFailures: failed.runtime.consecutiveFailures + 1,
        faultCount: failed.runtime.faultCount + 1,
      });
      this.indexService.upsertRuntime(nextRuntime);
      this.indexService.recordRun({
        scriptId,
        action: "start",
        outcome: "start-failed",
        message: error.message,
        triggeredBy,
        startedAt: nowIso(),
        metadata: {},
      });
      this.scheduleRestart(scriptId);
      this.events.emit("script-runtime-updated", { scriptId });
    });

    child.once("exit", (code) => {
      void this.handleProcessExit(scriptId, code);
    });

    return this.indexService.getScriptSummary(scriptId) ?? summary;
  }

  async stopScript(scriptId: string, forced = false, triggeredBy = "user"): Promise<ScriptSummary | undefined> {
    this.clearRestartTimer(scriptId);
    const summary = this.indexService.getScriptSummary(scriptId);
    if (!summary) {
      return undefined;
    }

    const managed = this.managedProcesses.get(scriptId);
    if (managed) {
      managed.desiredState = "stopped";
    }

    this.indexService.upsertRuntime(
      withRuntimeState(summary.runtime, "stopping", {
        desiredState: "stopped",
      }),
    );
    this.events.emit("script-runtime-updated", { scriptId });

    const pid = summary.runtime.pid;
    if (!pid) {
      this.indexService.upsertRuntime(
        withRuntimeState(summary.runtime, "stopped", {
          desiredState: "stopped",
          circuitState: "closed",
          consecutiveFailures: 0,
          circuitOpenedAt: undefined,
          circuitReason: undefined,
        }),
      );
      return this.indexService.getScriptSummary(scriptId);
    }

    if (!forced && summary.record.manifest.stop.mode === "command" && summary.record.manifest.stop.command) {
      await new Promise<void>((resolve) => {
        const proc = spawn(
          resolveWindowsCommand(summary.record.manifest.stop.command!.command),
          summary.record.manifest.stop.command!.args,
          {
            cwd: summary.record.manifest.stop.command!.cwd ?? summary.record.rootDir,
            shell: false,
            windowsHide: true,
          },
        );
        proc.on("close", () => resolve());
        proc.on("error", () => resolve());
      });
    } else if (!forced && summary.record.manifest.stop.mode === "http" && summary.record.manifest.stop.http?.url) {
      try {
        await fetch(summary.record.manifest.stop.http.url, {
          method: summary.record.manifest.stop.http.method ?? "POST",
        });
      } catch {
        // noop
      }
    }

    await this.forceKillByPid(pid);
    this.indexService.recordRun({
      scriptId,
      action: forced ? "force-kill" : "stop",
      outcome: "requested",
      pid,
      startedAt: summary.runtime.lastStartedAt,
      triggeredBy,
      metadata: {},
    });
    return this.indexService.getScriptSummary(scriptId);
  }

  async restartScript(scriptId: string, triggeredBy = "user"): Promise<ScriptSummary | undefined> {
    await this.stopScript(scriptId, false, triggeredBy);
    return this.startScript(scriptId, triggeredBy);
  }

  async forceKillScript(scriptId: string, triggeredBy = "user"): Promise<ScriptSummary | undefined> {
    return this.stopScript(scriptId, true, triggeredBy);
  }

  async syncExternalProcess(summary: ScriptSummary): Promise<void> {
    if (!summary.record.manifest.processMatch) {
      return;
    }
    const externalPid = await this.resourceSampler.findExternalProcess(summary.record.manifest.processMatch);
    if (!externalPid) {
      return;
    }
    const nextRuntime = withRuntimeState(summary.runtime, "running", {
      pid: externalPid,
      externalProcess: true,
      desiredState: summary.runtime.desiredState,
      lastStartedAt: summary.runtime.lastStartedAt ?? nowIso(),
      uptimeStartedAt: summary.runtime.uptimeStartedAt ?? nowIso(),
    });
    this.indexService.upsertRuntime(nextRuntime);
    this.events.emit("script-runtime-updated", { scriptId: summary.record.id });
  }

  async markUnresponsive(scriptId: string, message: string): Promise<void> {
    const summary = this.indexService.getScriptSummary(scriptId);
    if (!summary) {
      return;
    }
    if (hasCapability(summary.record.manifest, "oneshot")) {
      this.indexService.upsertRuntime(
        withRuntimeState(summary.runtime, "stopped", {
          desiredState: "stopped",
          pid: undefined,
          lastFailureReason: undefined,
          consecutiveFailures: 0,
        }),
      );
      return;
    }
    const nextRuntime = withRuntimeState(summary.runtime, "unresponsive", {
      lastFailureReason: message,
      consecutiveFailures: summary.runtime.consecutiveFailures + 1,
      faultCount: summary.runtime.faultCount + 1,
    });
    this.indexService.upsertRuntime(nextRuntime);
    this.indexService.recordRun({
      scriptId,
      action: "health-check",
      outcome: "unresponsive",
      message,
      pid: summary.runtime.pid,
      startedAt: nowIso(),
      triggeredBy: "health-monitor",
      metadata: {},
    });
    if (this.resolveRestartPolicy(summary) === "on-crash-or-unresponsive") {
      this.scheduleRestart(scriptId);
    }
  }
}
