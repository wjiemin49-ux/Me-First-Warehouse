import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { AppSettings, ProbeConfig, ScriptSummary } from "@shared/types";
import { EventBus } from "./event-bus";
import { IndexService } from "./index-service";
import { LogService } from "./log-service";
import { ProcessSupervisor } from "./process-supervisor";
import { ResourceSampler } from "./resource-sampler";
import { nowIso, secondsBetween } from "@main/utils/time-utils";
import { withRuntimeState } from "@main/utils/state-machine";

export class HealthMonitor {
  private timer?: NodeJS.Timeout;

  constructor(
    private readonly indexService: IndexService,
    private readonly events: EventBus,
    private readonly resourceSampler: ResourceSampler,
    private readonly supervisor: ProcessSupervisor,
    private readonly logService: LogService,
    private readonly getSettings: () => AppSettings,
  ) {}

  start(): void {
    this.stop();
    const run = () => void this.pollAll();
    this.timer = setInterval(run, this.getSettings().healthIntervalSeconds * 1000);
    run();
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  private async testPort(host: string, port: number, timeoutMs = 1500): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      const cleanup = () => {
        socket.destroy();
      };
      socket.setTimeout(timeoutMs);
      socket.once("connect", () => {
        cleanup();
        resolve(true);
      });
      socket.once("timeout", () => {
        cleanup();
        resolve(false);
      });
      socket.once("error", () => {
        cleanup();
        resolve(false);
      });
      socket.connect(port, host);
    });
  }

  private async evaluateProbe(summary: ScriptSummary, probe: ProbeConfig): Promise<{ success: boolean; message: string }> {
    const settings = this.getSettings();
    if (probe.type === "process") {
      return {
        success: Boolean(summary.runtime.pid && (await this.resourceSampler.processExists(summary.runtime.pid))),
        message: "进程探针",
      };
    }
    if (probe.type === "heartbeat-file") {
      const filePath = path.resolve(summary.record.rootDir, probe.path);
      if (!fs.existsSync(filePath)) {
        return { success: false, message: "heartbeat 文件不存在" };
      }
      const staleAfter = probe.staleAfterSeconds ?? settings.heartbeatStaleSeconds;
      const ageSeconds = Math.floor((Date.now() - fs.statSync(filePath).mtime.getTime()) / 1000);
      return {
        success: ageSeconds <= staleAfter,
        message: ageSeconds <= staleAfter ? "heartbeat 正常" : `heartbeat 超时 ${ageSeconds}s`,
      };
    }
    if (probe.type === "http") {
      try {
        const response = await fetch(probe.url, {
          signal: AbortSignal.timeout(probe.timeoutMs ?? 2000),
        });
        return {
          success: response.status === (probe.expectedStatus ?? 200),
          message: `HTTP ${response.status}`,
        };
      } catch (error) {
        return {
          success: false,
          message: error instanceof Error ? error.message : "HTTP 探针失败",
        };
      }
    }
    if (probe.type === "port") {
      const success = await this.testPort(probe.host ?? "127.0.0.1", probe.port, probe.timeoutMs);
      return {
        success,
        message: success ? `端口 ${probe.port} 可达` : `端口 ${probe.port} 不可达`,
      };
    }
    const logPath = summary.record.manifest.logging.filePath ?? this.logService.resolveLogPath(summary);
    if (!fs.existsSync(logPath)) {
      return { success: false, message: "日志文件不存在" };
    }
    const staleAfter = probe.staleAfterSeconds ?? settings.logStaleSeconds;
    const ageSeconds = Math.floor((Date.now() - fs.statSync(logPath).mtime.getTime()) / 1000);
    return {
      success: ageSeconds <= staleAfter,
      message: ageSeconds <= staleAfter ? "日志持续更新" : `日志静默 ${ageSeconds}s`,
    };
  }

  private async pollOne(summary: ScriptSummary): Promise<void> {
    if (!summary.runtime.pid) {
      return;
    }

    const exists = await this.resourceSampler.processExists(summary.runtime.pid);
    if (!exists) {
      if ((summary.record.manifest.capabilities ?? []).includes("oneshot")) {
        await this.supervisor.stopScript(summary.record.id, false, "health-monitor");
        return;
      }
      await this.supervisor.forceKillScript(summary.record.id, "health-monitor");
      return;
    }

    const resource = await this.resourceSampler.sample(
      summary.runtime.pid,
      summary.record.manifest.logging.filePath ?? this.logService.resolveLogPath(summary),
    );

    const results = await Promise.all(
      summary.record.manifest.health.probes.map(async (probe) => ({
        probe,
        result: await this.evaluateProbe(summary, probe),
      })),
    );

    results.forEach(({ probe, result }) => {
      this.indexService.recordHealthCheck({
        scriptId: summary.record.id,
        probeType: probe.type,
        status: result.success ? "healthy" : probe.severity === "required" ? "failed" : "degraded",
        message: result.message,
        createdAt: nowIso(),
        details: { severity: probe.severity },
      });
    });

    const requiredFailures = results.filter((item) => item.probe.severity === "required" && !item.result.success);
    const advisoryFailures = results.filter((item) => item.probe.severity === "advisory" && !item.result.success);

    let nextState = summary.runtime.lifecycleState;
    let nextMessage = summary.runtime.lastHealthSummary;
    if (requiredFailures.length === 0 && advisoryFailures.length === 0) {
      nextState = "running";
      nextMessage = "健康状态正常";
    } else if (requiredFailures.length > 0) {
      const runtimeSeconds = secondsBetween(summary.runtime.lastStartedAt) ?? 0;
      if (runtimeSeconds >= this.getSettings().unresponsiveTimeoutSeconds) {
        nextState = "unresponsive";
        nextMessage = requiredFailures.map((item) => item.result.message).join("；");
      } else {
        nextState = "unhealthy";
        nextMessage = requiredFailures.map((item) => item.result.message).join("；");
      }
    } else {
      nextState = "unhealthy";
      nextMessage = advisoryFailures.map((item) => item.result.message).join("；");
    }

    this.indexService.upsertRuntime(
      withRuntimeState(summary.runtime, nextState, {
        lastHealthSummary: nextMessage,
        resource: {
          ...resource,
          runtimeSeconds: secondsBetween(summary.runtime.lastStartedAt) ?? null,
        },
      }),
    );

    this.events.emit("health-updated", { scriptId: summary.record.id });
    this.events.emit("script-runtime-updated", { scriptId: summary.record.id });

    if (nextState === "unresponsive") {
      await this.supervisor.markUnresponsive(summary.record.id, nextMessage ?? "脚本无响应");
    }
  }

  async pollAll(): Promise<void> {
    const scripts = this.indexService.listScripts();
    const targets = scripts.filter(
      (item) =>
        item.runtime.lifecycleState === "running" ||
        item.runtime.lifecycleState === "starting" ||
        item.runtime.lifecycleState === "unhealthy" ||
        item.runtime.lifecycleState === "unresponsive",
    );
    for (const script of targets) {
      await this.pollOne(script);
    }
  }
}
