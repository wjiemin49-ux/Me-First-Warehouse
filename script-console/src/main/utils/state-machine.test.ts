import { ScriptRecord } from "@shared/types";
import { describe, expect, test, vi } from "vitest";
import {
  createDefaultRuntime,
  createEmptyResourceSample,
  lifecycleToDisplayStatus,
  lifecycleToHealth,
  withRuntimeState,
} from "./state-machine";

function buildBaseRecord(nowIso: string): ScriptRecord {
  return {
    id: "demo",
    sourceMode: "manifest",
    rootDir: "D:/me/scripts/demo",
    folderName: "demo",
    isConfigured: true,
    isMissing: false,
    manifest: {
      id: "demo",
      name: "demo",
      description: "",
      version: "1.0.0",
      author: "test",
      type: "node",
      entry: { command: "node", args: ["index.js"], cwd: ".", shell: false },
      stop: { mode: "process", timeoutMs: 1000 },
      logging: {},
      health: { probes: [{ type: "process", severity: "required" }] },
      display: { category: "", tags: [] },
      policy: { allowAutoStart: false, allowVisible: true, restartPolicy: "off" },
    },
    smartCategory: "",
    smartTags: [],
    classificationSource: "manifest",
    indexedAt: nowIso,
    createdAt: nowIso,
    updatedAt: nowIso,
  };
}

describe("state machine", () => {
  test("maps lifecycle states to display statuses", () => {
    const running = lifecycleToDisplayStatus("running");
    const crashed = lifecycleToDisplayStatus("crashed");
    const stopped = lifecycleToDisplayStatus("stopped");
    const unhealthy = lifecycleToDisplayStatus("unhealthy");

    expect(running).not.toBe(stopped);
    expect(crashed).not.toBe(stopped);
    expect(unhealthy).toBe(running);
  });

  test("maps lifecycle state to health state", () => {
    expect(lifecycleToHealth("running")).toBe("healthy");
    expect(lifecycleToHealth("unhealthy")).toBe("degraded");
    expect(lifecycleToHealth("missing")).toBe("failed");
    expect(lifecycleToHealth("ready")).toBe("unknown");
  });

  test("creates empty resource sample defaults", () => {
    expect(createEmptyResourceSample()).toEqual({
      cpuPercent: null,
      memoryMb: null,
      threadCount: null,
      runtimeSeconds: null,
      ports: [],
    });
  });

  test("createDefaultRuntime infers missing and configured states", () => {
    const fixedNow = "2026-03-23T22:00:00.000Z";
    vi.useFakeTimers();
    vi.setSystemTime(new Date(fixedNow));

    const readyRuntime = createDefaultRuntime(buildBaseRecord(fixedNow));
    expect(readyRuntime.lifecycleState).toBe("ready");
    expect(readyRuntime.healthState).toBe("unknown");
    expect(readyRuntime.updatedAt).toBe(fixedNow);

    const missingRuntime = createDefaultRuntime({ ...buildBaseRecord(fixedNow), isMissing: true });
    expect(missingRuntime.lifecycleState).toBe("missing");
    expect(missingRuntime.healthState).toBe("failed");

    const unconfiguredRuntime = createDefaultRuntime({
      ...buildBaseRecord(fixedNow),
      isConfigured: false,
    });
    expect(unconfiguredRuntime.lifecycleState).toBe("unconfigured");
    expect(unconfiguredRuntime.healthState).toBe("unknown");
    vi.useRealTimers();
  });

  test("withRuntimeState respects explicit display and health patches", () => {
    const fixedNow = "2026-03-23T22:01:00.000Z";
    vi.useFakeTimers();
    vi.setSystemTime(new Date(fixedNow));
    const runtime = {
      scriptId: "demo",
      lifecycleState: "ready",
      displayStatus: lifecycleToDisplayStatus("ready"),
      healthState: "unknown",
      desiredState: "stopped",
      restartCount: 0,
      faultCount: 0,
      consecutiveFailures: 0,
      circuitState: "closed",
      externalProcess: false,
      resource: createEmptyResourceSample(),
      updatedAt: "2026-03-20T00:00:00.000Z",
    } as const;

    const autoMapped = withRuntimeState(runtime, "running");
    expect(autoMapped.displayStatus).toBe(lifecycleToDisplayStatus("running"));
    expect(autoMapped.healthState).toBe("healthy");
    expect(autoMapped.updatedAt).toBe(fixedNow);

    const explicit = withRuntimeState(runtime, "running", {
      displayStatus: lifecycleToDisplayStatus("stopped"),
      healthState: "failed",
    });
    expect(explicit.displayStatus).toBe(lifecycleToDisplayStatus("stopped"));
    expect(explicit.healthState).toBe("failed");
    vi.useRealTimers();
  });
});
