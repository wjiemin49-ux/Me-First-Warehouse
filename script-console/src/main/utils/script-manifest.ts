import fs from "node:fs";
import path from "node:path";
import { manifestSchema } from "@shared/schema";
import { ScriptManifest, ScriptRecord, ScriptType, SourceMode } from "@shared/types";
import { assertSafeLaunch, assertSafeStopCommand } from "./command-security";
import { fileExists, isSubPath, normalizeTag, readJsonFile, safeResolve, slugify } from "./path-utils";
import { nowIso } from "./time-utils";

export const MANIFEST_FILES = ["manifest.json", "script-console.manifest.json"] as const;

function tokenizeCommandString(input: string): string[] {
  const tokens: string[] = [];
  const regex = /"([^"]*)"|'([^']*)'|([^\s]+)/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(input)) !== null) {
    tokens.push(match[1] ?? match[2] ?? match[3] ?? "");
  }
  return tokens.filter(Boolean);
}

function classifyManifest(manifest: ScriptManifest, folderName: string) {
  const source = [folderName, manifest.name, manifest.description, manifest.type, ...manifest.display.tags]
    .join(" ")
    .toLowerCase();

  const inferredTags = new Set<string>(manifest.display.tags.map(normalizeTag));
  inferredTags.add(manifest.type);

  let smartCategory = manifest.display.category || "未分类";

  if (source.includes("http") || source.includes("server") || source.includes("port")) {
    if (smartCategory === "未分类") smartCategory = "本地服务";
    inferredTags.add("service");
  }
  if (source.includes("monitor") || source.includes("watch") || source.includes("heartbeat")) {
    if (smartCategory === "未分类") smartCategory = "监控守护";
    inferredTags.add("monitor");
  }
  if (source.includes("report") || source.includes("daily") || source.includes("summary") || source.includes("briefing")) {
    if (smartCategory === "未分类") smartCategory = "报表摘要";
    inferredTags.add("report");
  }
  if (source.includes("batch") || source.includes("schedule") || source.includes("cron")) {
    if (smartCategory === "未分类") smartCategory = "定时自动化";
    inferredTags.add("automation");
  }
  if (source.includes("data") || source.includes("etl") || source.includes("transform")) {
    if (smartCategory === "未分类") smartCategory = "数据处理";
    inferredTags.add("data");
  }
  if (source.includes("demo") || source.includes("sample")) {
    inferredTags.add("demo");
  }

  return {
    smartCategory,
    smartTags: [...inferredTags].sort(),
    classificationSource: manifest.display.category && manifest.display.tags.length ? "hybrid" : "heuristic",
  } as const;
}

function addCapability(manifest: ScriptManifest, capability: string): void {
  const current = new Set(manifest.capabilities ?? []);
  current.add(capability);
  manifest.capabilities = [...current];
}

function parsePyprojectProjectName(raw: string): string | undefined {
  const match = raw.match(/^\s*name\s*=\s*["']([^"']+)["']/m);
  return match?.[1];
}

function extractProjectScripts(raw: string): Record<string, string> {
  const blockMatch = raw.match(/\[project\.scripts\]([\s\S]*?)(?:\n\[|$)/);
  if (!blockMatch) {
    return {};
  }
  const block = blockMatch[1];
  const result: Record<string, string> = {};
  for (const line of block.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const match = trimmed.match(/^([A-Za-z0-9._-]+)\s*=\s*["']([^"']+)["']$/);
    if (match) {
      result[match[1]] = match[2];
    }
  }
  return result;
}

function choosePythonModuleEntry(rootDir: string, projectName: string | undefined, scripts: Record<string, string>): { module?: string; args: string[] } {
  const scriptTarget = Object.values(scripts)[0];
  const targetModule = scriptTarget?.split(":")[0];
  const normalizedProjectModule = projectName?.replace(/-/g, "_");
  const moduleCandidates = [targetModule, normalizedProjectModule].filter(Boolean) as string[];

  for (const candidate of moduleCandidates) {
    const baseModule = candidate.replace(/\.__main__$/, "");
    const modulePath = path.join(rootDir, "src", ...baseModule.split("."));
    const hasMain = fileExists(path.join(modulePath, "__main__.py"));
    if (!hasMain) {
      continue;
    }
    const cliPath = path.join(modulePath, "cli.py");
    const cliSource = fileExists(cliPath) ? fs.readFileSync(cliPath, "utf8") : "";
    if (cliSource.includes('add_parser("run"') || cliSource.includes("add_parser('run'")) {
      return { module: baseModule, args: ["-m", baseModule, "run"] };
    }
    if (cliSource.includes('add_parser("preview"') || cliSource.includes("add_parser('preview'")) {
      return { module: baseModule, args: ["-m", baseModule, "preview"] };
    }
    return { module: baseModule, args: ["-m", baseModule] };
  }

  return { args: [] };
}

function markOneShotIfLikely(manifest: ScriptManifest, folderName: string): void {
  const source = `${folderName} ${manifest.name} ${manifest.description}`.toLowerCase();
  if (source.includes("report") || source.includes("briefing") || source.includes("daily")) {
    addCapability(manifest, "oneshot");
  }
}

export function parseManifestDocument(raw: unknown): ScriptManifest {
  const input = (raw ?? {}) as Record<string, unknown>;
  const startCommand = typeof input.startCommand === "string" ? input.startCommand : undefined;
  const tokens = startCommand ? tokenizeCommandString(startCommand) : [];

  const fallbackEntry =
    tokens.length > 0
      ? {
          command: tokens[0],
          args: tokens.slice(1),
          cwd: ".",
          shell: false,
        }
      : undefined;

  const entryFromRaw =
    input.entry && typeof input.entry === "object" && !Array.isArray(input.entry)
      ? input.entry
      : fallbackEntry;

  const healthAlias =
    input.healthCheck && typeof input.healthCheck === "object" && !Array.isArray(input.healthCheck)
      ? input.healthCheck
      : undefined;

  const normalized = {
    id: input.id,
    name: input.name,
    description: input.description ?? "",
    version: input.version ?? "0.1.0",
    author: input.author ?? "unknown",
    type: input.type ?? "unknown",
    entry: entryFromRaw,
    stop: input.stop ?? { mode: "process", timeoutMs: 10000 },
    logging:
      input.logging && typeof input.logging === "object"
        ? {
            ...(input.logging as Record<string, unknown>),
            filePath: (input.logging as Record<string, unknown>).filePath ?? input.logPath ?? "logs/app.log",
          }
        : {
            filePath: input.logPath ?? "logs/app.log",
            captureStdout: true,
            captureStderr: true,
            maxTailLines: 500,
          },
    health:
      input.health && typeof input.health === "object"
        ? input.health
        : healthAlias ?? {
            graceSeconds: 20,
            probes: [{ type: "process", severity: "required" }],
          },
    display:
      input.display && typeof input.display === "object"
        ? {
            ...(input.display as Record<string, unknown>),
            category: (input.display as Record<string, unknown>).category ?? input.category ?? "未分类",
            tags: (input.display as Record<string, unknown>).tags ?? input.tags ?? [],
          }
        : {
            category: input.category ?? "未分类",
            tags: input.tags ?? [],
          },
    policy:
      input.policy && typeof input.policy === "object"
        ? input.policy
        : {
            allowAutoStart: false,
            allowVisible: true,
            restartPolicy: "off",
          },
    processMatch: input.processMatch,
    capabilities: input.capabilities,
    extensions: input.extensions,
  };

  return manifestSchema.parse(normalized);
}

function normalizeManifest(rootDir: string, manifest: ScriptManifest): ScriptManifest {
  const resolvedEntry = {
    ...manifest.entry,
    cwd: safeResolve(rootDir, manifest.entry.cwd) ?? rootDir,
  };

  const resolvedStopCommand = manifest.stop.command
    ? {
        ...manifest.stop.command,
        cwd: safeResolve(rootDir, manifest.stop.command.cwd),
      }
    : undefined;

  const resolvedLogging = {
    ...manifest.logging,
    filePath: safeResolve(rootDir, manifest.logging.filePath),
  };

  const resolvedDisplay = {
    ...manifest.display,
    category: manifest.display.category || "未分类",
    icon: safeResolve(rootDir, manifest.display.icon),
    tags: manifest.display.tags.map(normalizeTag),
  };

  const resolvedHealth = {
    ...manifest.health,
    probes: manifest.health.probes.map((probe) => {
      if (probe.type === "heartbeat-file") {
        return { ...probe, path: safeResolve(rootDir, probe.path) ?? probe.path };
      }
      if (probe.type === "log-update") {
        return { ...probe, path: safeResolve(rootDir, probe.path) };
      }
      return probe;
    }),
  };

  const normalized: ScriptManifest = {
    ...manifest,
    entry: resolvedEntry,
    stop: {
      ...manifest.stop,
      command: resolvedStopCommand,
    },
    logging: resolvedLogging,
    display: resolvedDisplay,
    health: resolvedHealth,
  };

  assertSafeLaunch(normalized.entry, rootDir);
  assertSafeStopCommand(normalized.stop.command, rootDir);

  return normalized;
}

function buildBaseManifest(rootDir: string, folderName: string, type: ScriptType): ScriptManifest {
  return normalizeManifest(rootDir, {
    id: slugify(folderName),
    name: folderName,
    description: "兼容模式自动识别的脚本",
    version: "0.1.0",
    author: "unknown",
    type,
    entry: {
      command: "cmd",
      args: [],
      cwd: rootDir,
      shell: false,
    },
    stop: {
      mode: "process",
      timeoutMs: 10_000,
    },
    logging: {
      captureStdout: true,
      captureStderr: true,
      maxTailLines: 500,
    },
    health: {
      graceSeconds: 20,
      probes: [{ type: "process", severity: "required" }],
    },
    display: {
      category: "未分类",
      tags: [type],
      icon: undefined,
    },
    policy: {
      allowAutoStart: false,
      allowVisible: true,
      restartPolicy: "off",
    },
    capabilities: [],
  });
}

function detectNodeManifest(rootDir: string, folderName: string): ScriptManifest | undefined {
  const packageJson = readJsonFile<{
    name?: string;
    description?: string;
    version?: string;
    author?: string | { name?: string };
    main?: string;
    scripts?: Record<string, string>;
  }>(path.join(rootDir, "package.json"));
  if (!packageJson) {
    return undefined;
  }

  const manifest = buildBaseManifest(rootDir, folderName, "node");
  manifest.name = packageJson.name || folderName;
  manifest.description = packageJson.description || manifest.description;
  manifest.version = packageJson.version || manifest.version;
  manifest.author = typeof packageJson.author === "string" ? packageJson.author : packageJson.author?.name || manifest.author;

  if (packageJson.scripts?.start) {
    manifest.entry = {
      command: "npm",
      args: ["run", "start"],
      cwd: rootDir,
      shell: false,
    };
  } else if (packageJson.main) {
    manifest.entry = {
      command: "node",
      args: [packageJson.main],
      cwd: rootDir,
      shell: false,
    };
  } else {
    const defaultFile = ["index.js", "main.js", "server.js"].find((candidate) => fileExists(path.join(rootDir, candidate)));
    if (!defaultFile) {
      return undefined;
    }
    manifest.entry = {
      command: "node",
      args: [defaultFile],
      cwd: rootDir,
      shell: false,
    };
  }

  manifest.display.category = "Node 应用";
  return normalizeManifest(rootDir, manifest);
}

function detectPythonManifest(rootDir: string, folderName: string): ScriptManifest | undefined {
  const pyprojectPath = path.join(rootDir, "pyproject.toml");
  const directEntryFile = ["main.py", "__main__.py", "app.py"].find((candidate) => fileExists(path.join(rootDir, candidate)));
  if (!fileExists(pyprojectPath) && !directEntryFile) {
    return undefined;
  }

  const manifest = buildBaseManifest(rootDir, folderName, "python");

  if (fileExists(pyprojectPath)) {
    const raw = fs.readFileSync(pyprojectPath, "utf8");
    const projectName = parsePyprojectProjectName(raw);
    const scripts = extractProjectScripts(raw);
    const moduleEntry = choosePythonModuleEntry(rootDir, projectName, scripts);
    if (moduleEntry.module) {
      manifest.entry = {
        command: "python",
        args: moduleEntry.args,
        cwd: rootDir,
        env: {
          PYTHONPATH: path.join(rootDir, "src"),
        },
        shell: false,
      };
      addCapability(manifest, "oneshot");
    } else if (directEntryFile) {
      manifest.entry = {
        command: "python",
        args: [directEntryFile],
        cwd: rootDir,
        shell: false,
      };
    } else {
      return undefined;
    }
  } else if (directEntryFile) {
    manifest.entry = {
      command: "python",
      args: [directEntryFile],
      cwd: rootDir,
      shell: false,
    };
  } else {
    return undefined;
  }

  markOneShotIfLikely(manifest, folderName);
  manifest.display.category = "Python 脚本";
  return normalizeManifest(rootDir, manifest);
}

function detectPowerShellManifest(rootDir: string, folderName: string): ScriptManifest | undefined {
  const entryFile = ["main.ps1", "run.ps1"].find((candidate) => fileExists(path.join(rootDir, candidate)));
  if (!entryFile) {
    return undefined;
  }
  const manifest = buildBaseManifest(rootDir, folderName, "powershell");
  manifest.entry = {
    command: "powershell",
    args: ["-ExecutionPolicy", "Bypass", "-File", entryFile],
    cwd: rootDir,
    shell: false,
  };
  manifest.display.category = "PowerShell";
  return normalizeManifest(rootDir, manifest);
}

function detectBatchManifest(rootDir: string, folderName: string): ScriptManifest | undefined {
  const entryFile = ["run.bat", "run.cmd", "start.bat", "start.cmd"].find((candidate) => fileExists(path.join(rootDir, candidate)));
  if (!entryFile) {
    return undefined;
  }
  const manifest = buildBaseManifest(rootDir, folderName, "bat");
  manifest.entry = {
    command: "cmd",
    args: ["/c", entryFile],
    cwd: rootDir,
    shell: false,
  };
  manifest.display.category = "批处理";
  return normalizeManifest(rootDir, manifest);
}

function detectExeManifest(rootDir: string, folderName: string): ScriptManifest | undefined {
  const rootExecutables = fs
    .readdirSync(rootDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".exe"))
    .map((entry) => path.join(rootDir, entry.name));

  const binDir = path.join(rootDir, "bin");
  const binExecutables = fileExists(binDir)
    ? fs
        .readdirSync(binDir, { withFileTypes: true })
        .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".exe"))
        .map((entry) => path.join(binDir, entry.name))
    : [];

  const candidates = [...rootExecutables, ...binExecutables];
  if (candidates.length !== 1) {
    return undefined;
  }

  const manifest = buildBaseManifest(rootDir, folderName, "exe");
  manifest.entry = {
    command: candidates[0],
    args: [],
    cwd: rootDir,
    shell: false,
  };
  manifest.display.category = "可执行程序";
  return normalizeManifest(rootDir, manifest);
}

export function parseManifestFile(rootDir: string): ScriptManifest | undefined {
  const manifestPath = MANIFEST_FILES.map((fileName) => path.join(rootDir, fileName)).find(fileExists);
  if (!manifestPath) {
    return undefined;
  }
  const raw = fs.readFileSync(manifestPath, "utf8");
  const parsed = parseManifestDocument(JSON.parse(raw));
  return normalizeManifest(rootDir, parsed);
}

export function detectManifest(rootDir: string): {
  manifest?: ScriptManifest;
  sourceMode: SourceMode;
  heuristicReason?: string;
  manifestPath?: string;
  warnings: string[];
} {
  const warnings: string[] = [];
  const manifestPath = MANIFEST_FILES.map((fileName) => path.join(rootDir, fileName)).find(fileExists);
  if (manifestPath) {
    return {
      manifest: parseManifestFile(rootDir),
      sourceMode: "manifest",
      manifestPath,
      warnings,
    };
  }

  const folderName = path.basename(rootDir);
  const heuristics: Array<[string, () => ScriptManifest | undefined]> = [
    ["package.json", () => detectNodeManifest(rootDir, folderName)],
    ["pyproject.toml / python entry", () => detectPythonManifest(rootDir, folderName)],
    ["main.ps1 / run.ps1", () => detectPowerShellManifest(rootDir, folderName)],
    ["run.bat / run.cmd", () => detectBatchManifest(rootDir, folderName)],
    ["single exe", () => detectExeManifest(rootDir, folderName)],
  ];

  for (const [reason, resolver] of heuristics) {
    const manifest = resolver();
    if (manifest) {
      warnings.push("当前为兼容模式接入，建议补全标准 manifest。");
      return {
        manifest,
        sourceMode: "heuristic",
        heuristicReason: reason,
        warnings,
      };
    }
  }

  return {
    sourceMode: "heuristic",
    heuristicReason: "unrecognized",
    warnings: ["未识别到可运行入口，请通过接入向导补全配置。"],
  };
}

export function buildScriptRecord(rootDir: string): ScriptRecord | undefined {
  const detected = detectManifest(rootDir);
  if (!detected.manifest) {
    return undefined;
  }

  const now = nowIso();
  const classification = classifyManifest(detected.manifest, path.basename(rootDir));

  return {
    id: detected.manifest.id,
    sourceMode: detected.sourceMode,
    rootDir,
    manifestPath: detected.manifestPath,
    folderName: path.basename(rootDir),
    heuristicReason: detected.heuristicReason,
    isConfigured: detected.sourceMode === "manifest",
    isMissing: false,
    manifest: detected.manifest,
    smartCategory: classification.smartCategory,
    smartTags: classification.smartTags,
    classificationSource: classification.classificationSource,
    indexedAt: now,
    createdAt: now,
    updatedAt: now,
  };
}

export function validateWorkspacePath(scriptRoot: string, candidateDir: string): void {
  if (!isSubPath(scriptRoot, candidateDir)) {
    throw new Error("脚本目录必须位于脚本根目录内");
  }
}
