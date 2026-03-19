import {
  DisplayStatus,
  HealthState,
  LifecycleState,
  RuntimeResourceSample,
  ScriptRecord,
  ScriptRuntimeSnapshot,
} from "@shared/types";
import { nowIso } from "./time-utils";

export function lifecycleToDisplayStatus(state: LifecycleState): DisplayStatus {
  switch (state) {
    case "running":
      return "运行中";
    case "starting":
      return "启动中";
    case "stopping":
      return "停止中";
    case "crashed":
      return "异常退出";
    case "unresponsive":
      return "无响应";
    case "disabled":
      return "已禁用";
    case "missing":
      return "已缺失";
    case "unconfigured":
      return "未配置";
    case "stopped":
    case "indexed":
    case "ready":
    case "discovered":
    case "unhealthy":
    default:
      return state === "unhealthy" ? "运行中" : "已停止";
  }
}

export function lifecycleToHealth(state: LifecycleState): HealthState {
  switch (state) {
    case "running":
      return "healthy";
    case "unhealthy":
      return "degraded";
    case "unresponsive":
    case "crashed":
    case "missing":
      return "failed";
    default:
      return "unknown";
  }
}

export function createEmptyResourceSample(): RuntimeResourceSample {
  return {
    cpuPercent: null,
    memoryMb: null,
    threadCount: null,
    runtimeSeconds: null,
    ports: [],
  };
}

export function createDefaultRuntime(record: ScriptRecord): ScriptRuntimeSnapshot {
  const lifecycleState: LifecycleState = record.isMissing
    ? "missing"
    : record.isConfigured
      ? "ready"
      : "unconfigured";

  return {
    scriptId: record.id,
    lifecycleState,
    displayStatus: lifecycleToDisplayStatus(lifecycleState),
    healthState: lifecycleToHealth(lifecycleState),
    desiredState: "stopped",
    restartCount: 0,
    faultCount: 0,
    consecutiveFailures: 0,
    circuitState: "closed",
    externalProcess: false,
    resource: createEmptyResourceSample(),
    updatedAt: nowIso(),
  };
}

export function withRuntimeState(
  runtime: ScriptRuntimeSnapshot,
  lifecycleState: LifecycleState,
  patch?: Partial<ScriptRuntimeSnapshot>,
): ScriptRuntimeSnapshot {
  return {
    ...runtime,
    ...patch,
    lifecycleState,
    displayStatus: patch?.displayStatus ?? lifecycleToDisplayStatus(lifecycleState),
    healthState: patch?.healthState ?? lifecycleToHealth(lifecycleState),
    updatedAt: nowIso(),
  };
}
