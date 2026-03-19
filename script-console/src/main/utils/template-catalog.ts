import { DEFAULT_SAMPLE_SCRIPT_PREFIX } from "@shared/constants";
import { ScriptManifest, WizardTemplateInput } from "@shared/types";
import { nowIso } from "./time-utils";

export interface GeneratedFile {
  relativePath: string;
  content: string;
}

export interface GeneratedProject {
  directoryName: string;
  files: GeneratedFile[];
}

const EXIT_CODE_MAP = {
  0: "正常结束",
  2: "配置错误",
  3: "依赖缺失",
  4: "启动失败",
  5: "健康初始化失败",
  10: "业务 fatal",
};

function stringifyCommand(command: string, args: string[]): string {
  return [command, ...args]
    .map((token) => (/\s/.test(token) ? `"${token}"` : token))
    .join(" ");
}

function manifestDocument(manifest: ScriptManifest) {
  return {
    id: manifest.id,
    name: manifest.name,
    description: manifest.description,
    version: manifest.version,
    author: manifest.author,
    type: manifest.type,
    entry: manifest.entry,
    startCommand: stringifyCommand(manifest.entry.command, manifest.entry.args),
    healthCheck: manifest.health,
    logPath: manifest.logging.filePath ?? "logs/app.log",
    tags: manifest.display.tags,
    category: manifest.display.category,
    stop: manifest.stop,
    logging: manifest.logging,
    health: manifest.health,
    display: manifest.display,
    policy: manifest.policy,
    capabilities: manifest.capabilities ?? [],
    exitCodeMap: EXIT_CODE_MAP,
  };
}

function baseManifest(input: {
  id: string;
  name: string;
  description: string;
  author: string;
  type: ScriptManifest["type"];
  category?: string;
  tags?: string[];
}): ScriptManifest {
  return {
    id: input.id,
    name: input.name,
    description: input.description,
    version: "0.1.0",
    author: input.author,
    type: input.type,
    entry: {
      command: "cmd",
      args: [],
      cwd: ".",
      shell: false,
    },
    stop: {
      mode: "process",
      timeoutMs: 10000,
    },
    logging: {
      filePath: "logs/app.log",
      captureStdout: true,
      captureStderr: true,
      maxTailLines: 500,
    },
    health: {
      graceSeconds: 20,
      probes: [
        { type: "process", severity: "required" },
        { type: "heartbeat-file", severity: "advisory", path: "runtime/heartbeat.json", staleAfterSeconds: 45 },
        { type: "log-update", severity: "advisory", path: "logs/app.log", staleAfterSeconds: 120 },
      ],
    },
    display: {
      category: input.category ?? "未分类",
      tags: input.tags ?? [input.type],
      icon: "assets/icon.txt",
    },
    policy: {
      allowAutoStart: false,
      allowVisible: true,
      restartPolicy: "off",
    },
    capabilities: ["heartbeat-file", "log-file"],
  };
}

function pythonHeartbeatSdk() {
  return `import json\nimport pathlib\nfrom datetime import datetime, timezone\n\n\ndef write_heartbeat(root: str | pathlib.Path, status: str = "alive", extra: dict | None = None) -> None:\n    root_path = pathlib.Path(root)\n    heartbeat_file = root_path / "runtime" / "heartbeat.json"\n    heartbeat_file.parent.mkdir(parents=True, exist_ok=True)\n    payload = {\n        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),\n        "status": status,\n    }\n    if extra:\n        payload.update(extra)\n    heartbeat_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")\n`;
}

function nodeHeartbeatSdk() {
  return `const fs = require("node:fs");\nconst path = require("node:path");\n\nfunction writeHeartbeat(rootDir, status = "alive", extra = {}) {\n  const filePath = path.join(rootDir, "runtime", "heartbeat.json");\n  fs.mkdirSync(path.dirname(filePath), { recursive: true });\n  const payload = {\n    timestamp: new Date().toISOString(),\n    status,\n    ...extra,\n  };\n  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));\n}\n\nmodule.exports = { writeHeartbeat };\n`;
}

function powershellHeartbeatSdk() {
  return `function Write-Heartbeat {\n  param(\n    [string]$RootDir,\n    [string]$Status = "alive"\n  )\n  $runtimeDir = Join-Path $RootDir "runtime"\n  $heartbeat = Join-Path $runtimeDir "heartbeat.json"\n  if (!(Test-Path $runtimeDir)) { New-Item -ItemType Directory -Path $runtimeDir | Out-Null }\n  $payload = @{\n    timestamp = [DateTime]::UtcNow.ToString("o")\n    status = $Status\n  } | ConvertTo-Json\n  Set-Content -Path $heartbeat -Value $payload -Encoding UTF8\n}\n`;
}

function baseFiles(name: string, description: string): GeneratedFile[] {
  return [
    { relativePath: "README.md", content: `# ${name}\n\n${description}\n` },
    { relativePath: "EXIT_CODES.md", content: Object.entries(EXIT_CODE_MAP).map(([code, message]) => `- ${code}: ${message}`).join("\n") + "\n" },
    { relativePath: "logs/.gitkeep", content: "" },
    { relativePath: "runtime/heartbeat.json", content: JSON.stringify({ timestamp: nowIso(), status: "booting" }, null, 2) },
    { relativePath: "assets/icon.txt", content: "SC" },
  ];
}

function manifestFiles(manifest: ScriptManifest): GeneratedFile[] {
  const content = JSON.stringify(manifestDocument(manifest), null, 2);
  return [
    { relativePath: "manifest.json", content },
    { relativePath: "script-console.manifest.json", content },
  ];
}

export function buildTemplateProject(input: WizardTemplateInput): GeneratedProject {
  const manifest = baseManifest({
    id: input.scriptId,
    name: input.name,
    description: input.description,
    author: input.author,
    type: input.templateType === "exe-wrapper" ? "exe" : input.templateType === "bat" ? "bat" : input.templateType,
    category: input.category,
    tags: input.tags,
  });

  const files = [...baseFiles(input.name, input.description)];

  if (input.templateType === "python") {
    manifest.type = "python";
    manifest.entry = { command: "python", args: ["main.py"], cwd: ".", shell: false };
    manifest.display.category = input.category ?? "Python 脚本";
    files.push({ relativePath: "sdk/heartbeat.py", content: pythonHeartbeatSdk() });
    files.push({
      relativePath: "main.py",
      content:
        `import pathlib\nimport time\nfrom sdk.heartbeat import write_heartbeat\n\nROOT = pathlib.Path(__file__).resolve().parent\nLOG_FILE = ROOT / "logs" / "app.log"\nLOG_FILE.parent.mkdir(parents=True, exist_ok=True)\n\nwhile True:\n    write_heartbeat(ROOT)\n    with LOG_FILE.open("a", encoding="utf-8") as fp:\n        fp.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} [INFO] template heartbeat\\n")\n    print("template heartbeat")\n    time.sleep(15)\n`,
    });
  } else if (input.templateType === "node") {
    manifest.type = "node";
    manifest.entry = { command: "node", args: ["index.js"], cwd: ".", shell: false };
    manifest.display.category = input.category ?? "Node 应用";
    files.push({ relativePath: "sdk/heartbeat.js", content: nodeHeartbeatSdk() });
    files.push({
      relativePath: "package.json",
      content: JSON.stringify(
        {
          name: input.scriptId,
          version: "0.1.0",
          private: true,
          scripts: { start: "node index.js" },
        },
        null,
        2,
      ),
    });
    files.push({
      relativePath: "index.js",
      content:
        `const fs = require("node:fs");\nconst path = require("node:path");\nconst { writeHeartbeat } = require("./sdk/heartbeat");\nconst root = __dirname;\nconst logFile = path.join(root, "logs", "app.log");\nfs.mkdirSync(path.dirname(logFile), { recursive: true });\nsetInterval(() => {\n  writeHeartbeat(root, "alive");\n  fs.appendFileSync(logFile, new Date().toISOString() + " [INFO] template heartbeat\\n");\n  console.log("template heartbeat");\n}, 15000);\n`,
    });
  } else if (input.templateType === "bat") {
    manifest.type = "bat";
    manifest.entry = { command: "cmd", args: ["/c", "run.bat"], cwd: ".", shell: false };
    manifest.display.category = input.category ?? "批处理";
    files.push({
      relativePath: "run.bat",
      content:
        `@echo off\r\nset ROOT=%~dp0\r\nset LOGDIR=%ROOT%logs\r\nset RUNTIMEDIR=%ROOT%runtime\r\nif not exist "%LOGDIR%" mkdir "%LOGDIR%"\r\nif not exist "%RUNTIMEDIR%" mkdir "%RUNTIMEDIR%"\r\n:loop\r\necho %date%T%time% [INFO] batch heartbeat>> "%LOGDIR%\\app.log"\r\necho {"timestamp":"%date%T%time%","status":"alive"}> "%RUNTIMEDIR%\\heartbeat.json"\r\ntimeout /t 15 >nul\r\ngoto loop\r\n`,
    });
  } else {
    manifest.type = "exe";
    manifest.entry = { command: ".\\bin\\app.exe", args: [], cwd: ".", shell: false };
    manifest.display.category = input.category ?? "可执行程序";
    files.push({
      relativePath: "wrapper-note.txt",
      content: "将你的 exe 放入 bin/app.exe，即可被中控台按标准协议管理。",
    });
    files.push({ relativePath: "bin/.gitkeep", content: "" });
  }

  files.unshift(...manifestFiles(manifest));
  return {
    directoryName: input.scriptId,
    files,
  };
}

export function buildSampleProjects(): GeneratedProject[] {
  const sampleInputs: WizardTemplateInput[] = [
    {
      templateType: "python",
      targetDirectory: "",
      scriptId: `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-python-heartbeat`,
      name: "Python Heartbeat Demo",
      description: "持续写入 heartbeat 与日志的 Python 示例脚本",
      author: "Script Console",
      category: "监控守护",
      tags: ["demo", "python", "monitor"],
    },
    {
      templateType: "node",
      targetDirectory: "",
      scriptId: `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-node-http`,
      name: "Node Local Service Demo",
      description: "带本地 HTTP 健康检查的 Node 服务示例",
      author: "Script Console",
      category: "本地服务",
      tags: ["demo", "node", "service", "http"],
    },
    {
      templateType: "bat",
      targetDirectory: "",
      scriptId: `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-batch-loop`,
      name: "Batch Loop Demo",
      description: "bat/cmd 心跳示例",
      author: "Script Console",
      category: "定时自动化",
      tags: ["demo", "bat", "automation"],
    },
    {
      templateType: "python",
      targetDirectory: "",
      scriptId: `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-flaky-python`,
      name: "Flaky Restart Demo",
      description: "定期崩溃，用于演示自动重启与熔断",
      author: "Script Console",
      category: "故障演示",
      tags: ["demo", "python", "flaky", "fault"],
    },
  ];

  const generated = sampleInputs.map(buildTemplateProject);

  const powershellManifest = baseManifest({
    id: `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-powershell-monitor`,
    name: "PowerShell Monitor Demo",
    description: "PowerShell 守护脚本示例",
    author: "Script Console",
    type: "powershell",
    category: "运维脚本",
    tags: ["demo", "powershell", "ops"],
  });
  powershellManifest.entry = {
    command: "powershell",
    args: ["-ExecutionPolicy", "Bypass", "-File", "run.ps1"],
    cwd: ".",
    shell: false,
  };

  generated.push({
    directoryName: powershellManifest.id,
    files: [
      ...manifestFiles(powershellManifest),
      ...baseFiles(powershellManifest.name, powershellManifest.description),
      { relativePath: "sdk/heartbeat.ps1", content: powershellHeartbeatSdk() },
      {
        relativePath: "run.ps1",
        content:
          `. "$PSScriptRoot\\sdk\\heartbeat.ps1"\n$logFile = Join-Path $PSScriptRoot "logs\\app.log"\nif (!(Test-Path (Split-Path $logFile))) { New-Item -ItemType Directory -Path (Split-Path $logFile) | Out-Null }\nwhile ($true) {\n  Write-Heartbeat -RootDir $PSScriptRoot -Status "alive"\n  Add-Content -Path $logFile -Value ("{0} [INFO] powershell demo alive" -f [DateTime]::UtcNow.ToString("o"))\n  Write-Output "powershell demo alive"\n  Start-Sleep -Seconds 15\n}\n`,
      },
    ],
  });

  const flaky = generated.find((item) => item.directoryName === `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-flaky-python`);
  if (flaky) {
    flaky.files = flaky.files.map((file) =>
      file.relativePath === "main.py"
        ? {
            ...file,
            content:
              `import pathlib\nimport sys\nimport time\nfrom sdk.heartbeat import write_heartbeat\n\nROOT = pathlib.Path(__file__).resolve().parent\nLOG_FILE = ROOT / "logs" / "app.log"\nLOG_FILE.parent.mkdir(parents=True, exist_ok=True)\n\nfor index in range(3):\n    write_heartbeat(ROOT, extra={"iteration": index})\n    with LOG_FILE.open("a", encoding="utf-8") as fp:\n        fp.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} [ERROR] flaky demo step {index}\\n")\n    print(f"flaky demo step {index}")\n    time.sleep(4)\n\nprint("flaky demo crashing now")\nsys.exit(13)\n`,
          }
        : file,
    );
  }

  const nodeDemo = generated.find((item) => item.directoryName === `${DEFAULT_SAMPLE_SCRIPT_PREFIX}-node-http`);
  if (nodeDemo) {
    nodeDemo.files = nodeDemo.files.map((file) =>
      file.relativePath === "manifest.json" || file.relativePath === "script-console.manifest.json"
        ? {
            ...file,
            content: JSON.stringify(
              {
                ...JSON.parse(file.content),
                healthCheck: {
                  graceSeconds: 20,
                  probes: [
                    { type: "process", severity: "required" },
                    { type: "http", severity: "required", url: "http://127.0.0.1:43101/health", expectedStatus: 200 },
                    { type: "port", severity: "advisory", port: 43101, host: "127.0.0.1" },
                    { type: "log-update", severity: "advisory", path: "logs/app.log", staleAfterSeconds: 120 },
                  ],
                },
                health: {
                  graceSeconds: 20,
                  probes: [
                    { type: "process", severity: "required" },
                    { type: "http", severity: "required", url: "http://127.0.0.1:43101/health", expectedStatus: 200 },
                    { type: "port", severity: "advisory", port: 43101, host: "127.0.0.1" },
                    { type: "log-update", severity: "advisory", path: "logs/app.log", staleAfterSeconds: 120 },
                  ],
                },
              },
              null,
              2,
            ),
          }
        : file,
    );
    nodeDemo.files.push({
      relativePath: "index.js",
      content:
        `const http = require("node:http");\nconst fs = require("node:fs");\nconst path = require("node:path");\nconst { writeHeartbeat } = require("./sdk/heartbeat");\nconst root = __dirname;\nconst logFile = path.join(root, "logs", "app.log");\nfs.mkdirSync(path.dirname(logFile), { recursive: true });\nconst server = http.createServer((req, res) => {\n  if (req.url === "/health") {\n    res.writeHead(200, { "Content-Type": "application/json" });\n    return res.end(JSON.stringify({ ok: true, timestamp: new Date().toISOString() }));\n  }\n  res.writeHead(200);\n  res.end("Script Console demo service");\n});\nserver.listen(43101, "127.0.0.1");\nsetInterval(() => {\n  writeHeartbeat(root, "alive", { port: 43101 });\n  const line = new Date().toISOString() + " [INFO] node demo service alive\\n";\n  fs.appendFileSync(logFile, line);\n  console.log(line.trim());\n}, 15000);\n`,
    });
  }

  return generated;
}
