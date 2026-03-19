import { z } from "zod";
import {
  ALLOWED_EXECUTABLES,
  DEFAULT_HEALTH_INTERVAL_SECONDS,
  DEFAULT_LOG_STALE_SECONDS,
  DEFAULT_MAX_LOG_LINES,
  DEFAULT_MAX_RESTART_RETRIES,
  DEFAULT_RESTART_COOLDOWN_MINUTES,
  DEFAULT_RETRY_BACKOFF_SECONDS,
  DEFAULT_SCAN_INTERVAL_SECONDS,
  DEFAULT_SCRIPT_ROOT,
  DEFAULT_UNRESPONSIVE_TIMEOUT_SECONDS,
} from "@shared/constants";

const nonEmpty = z.string().trim().min(1);

export const launchConfigSchema = z.object({
  command: nonEmpty,
  args: z.array(z.string()).default([]),
  cwd: nonEmpty,
  env: z.record(z.string(), z.string()).optional(),
  shell: z.boolean().default(false),
});

export const stopCommandSchema = z.object({
  command: nonEmpty,
  args: z.array(z.string()).default([]),
  cwd: z.string().optional(),
});

export const stopHttpSchema = z.object({
  url: nonEmpty,
  method: z.enum(["GET", "POST"]).default("POST"),
  timeoutMs: z.number().int().positive().optional(),
});

export const stopConfigSchema = z.object({
  mode: z.enum(["process", "command", "http", "none"]).default("process"),
  timeoutMs: z.number().int().positive().optional(),
  command: stopCommandSchema.optional(),
  http: stopHttpSchema.optional(),
});

export const loggingConfigSchema = z.object({
  filePath: z.string().optional(),
  maxTailLines: z.number().int().positive().default(DEFAULT_MAX_LOG_LINES),
  levelPattern: z.string().optional(),
  captureStdout: z.boolean().default(true),
  captureStderr: z.boolean().default(true),
});

const probeBaseSchema = z.object({
  severity: z.enum(["required", "advisory"]).default("advisory"),
  timeoutMs: z.number().int().positive().optional(),
});

export const probeSchema = z.discriminatedUnion("type", [
  probeBaseSchema.extend({
    type: z.literal("process"),
  }),
  probeBaseSchema.extend({
    type: z.literal("heartbeat-file"),
    path: nonEmpty,
    staleAfterSeconds: z.number().int().positive().optional(),
  }),
  probeBaseSchema.extend({
    type: z.literal("http"),
    url: nonEmpty,
    expectedStatus: z.number().int().positive().optional(),
  }),
  probeBaseSchema.extend({
    type: z.literal("port"),
    port: z.number().int().positive(),
    host: z.string().default("127.0.0.1"),
  }),
  probeBaseSchema.extend({
    type: z.literal("log-update"),
    path: z.string().optional(),
    staleAfterSeconds: z.number().int().positive().optional(),
  }),
]);

export const healthConfigSchema = z.object({
  graceSeconds: z.number().int().nonnegative().default(20),
  probes: z.array(probeSchema).default([{ type: "process", severity: "required" }]),
});

export const displayConfigSchema = z.object({
  category: nonEmpty.default("未分类"),
  tags: z.array(z.string()).default([]),
  icon: z.string().optional(),
});

export const policyConfigSchema = z.object({
  allowAutoStart: z.boolean().default(false),
  allowVisible: z.boolean().default(true),
  restartPolicy: z.enum(["off", "on-crash", "on-crash-or-unresponsive"]).default("off"),
  restartMaxRetries: z.number().int().min(0).optional(),
  cooldownMinutes: z.number().int().positive().optional(),
});

export const processMatchSchema = z
  .object({
    executableName: z.string().optional(),
    commandLineIncludes: z.string().optional(),
  })
  .refine((value) => Boolean(value.executableName || value.commandLineIncludes), {
    message: "processMatch 至少需要一个匹配条件",
  })
  .optional();

export const manifestSchema = z.object({
  id: z.string().trim().min(1).regex(/^[a-z0-9][a-z0-9-_]+$/),
  name: nonEmpty,
  description: z.string().default(""),
  version: nonEmpty.default("0.1.0"),
  author: nonEmpty.default("unknown"),
  type: z.enum(["python", "node", "powershell", "bat", "exe", "java", "go", "rust", "unknown"]),
  entry: launchConfigSchema,
  stop: stopConfigSchema,
  logging: loggingConfigSchema,
  health: healthConfigSchema,
  display: displayConfigSchema,
  policy: policyConfigSchema,
  processMatch: processMatchSchema,
  capabilities: z.array(z.string()).default([]),
  extensions: z.record(z.string(), z.unknown()).optional(),
});

export const appSettingsSchema = z.object({
  scriptRoot: z.string().default(DEFAULT_SCRIPT_ROOT),
  autoScan: z.boolean().default(true),
  scanIntervalSeconds: z.number().int().positive().default(DEFAULT_SCAN_INTERVAL_SECONDS),
  healthIntervalSeconds: z.number().int().positive().default(DEFAULT_HEALTH_INTERVAL_SECONDS),
  openAtLogin: z.boolean().default(false),
  theme: z.enum(["system", "dark", "light"]).default("system"),
  dataDirectory: z.string().default(""),
  trayEnabled: z.boolean().default(true),
  closeBehavior: z.enum(["confirm", "minimize-to-tray", "exit"]).default("confirm"),
  logRetentionDays: z.number().int().positive().default(14),
  restartPolicy: z.enum(["off", "on-crash", "on-crash-or-unresponsive"]).default("on-crash"),
  restartMaxRetries: z.number().int().min(0).default(DEFAULT_MAX_RESTART_RETRIES),
  restartCooldownMinutes: z.number().int().positive().default(DEFAULT_RESTART_COOLDOWN_MINUTES),
  restartBackoffSeconds: z.array(z.number().int().positive()).default(DEFAULT_RETRY_BACKOFF_SECONDS),
  defaultLogTailLines: z.number().int().positive().default(DEFAULT_MAX_LOG_LINES),
  unresponsiveTimeoutSeconds: z.number().int().positive().default(DEFAULT_UNRESPONSIVE_TIMEOUT_SECONDS),
  logStaleSeconds: z.number().int().positive().default(DEFAULT_LOG_STALE_SECONDS),
  heartbeatStaleSeconds: z.number().int().positive().default(45),
  processSampleIntervalSeconds: z.number().int().positive().default(5),
});

export const scriptIdSchema = nonEmpty;

export const logSearchSchema = z.object({
  scriptIds: z.array(z.string()).optional(),
  levels: z.array(z.enum(["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL", "UNKNOWN"])).optional(),
  search: z.string().optional(),
  from: z.string().optional(),
  to: z.string().optional(),
  limit: z.number().int().positive().max(5000).default(300),
});

export const wizardTemplateSchema = z.object({
  templateType: z.enum(["python", "node", "bat", "exe-wrapper"]),
  targetDirectory: nonEmpty,
  scriptId: manifestSchema.shape.id,
  name: nonEmpty,
  description: z.string().default(""),
  author: nonEmpty,
  category: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

export const commandInputSchema = z
  .string()
  .trim()
  .min(1)
  .refine(
    (value) => ALLOWED_EXECUTABLES.includes(value.toLowerCase()) || /^[A-Za-z]:\\/.test(value),
    "命令必须是白名单解释器或脚本目录内的绝对路径",
  );
