import { describe, expect, test } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  buildScriptRecord,
  detectManifest,
  parseManifestDocument,
  validateWorkspacePath,
} from "./script-manifest";

describe("script-manifest heuristics", () => {
  test("detects python main.py project", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-python-"));
    fs.writeFileSync(path.join(root, "main.py"), "print('hello')", "utf8");

    const record = buildScriptRecord(root);

    expect(record).toBeTruthy();
    expect(record?.manifest.type).toBe("python");
    expect(record?.sourceMode).toBe("heuristic");
  });

  test("parses manifest.json compatibility format", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-manifest-"));
    fs.writeFileSync(
      path.join(root, "manifest.json"),
      JSON.stringify(
        {
          id: "compat-demo",
          name: "Compat Demo",
          description: "compat",
          version: "1.0.0",
          author: "test",
          type: "python",
          entry: {
            command: "python",
            args: ["main.py"],
            cwd: ".",
            shell: false,
          },
          startCommand: "python main.py",
          healthCheck: {
            graceSeconds: 20,
            probes: [{ type: "process", severity: "required" }],
          },
          logPath: "logs/app.log",
          tags: ["demo", "python"],
          category: "Python 脚本",
          stop: { mode: "process", timeoutMs: 10000 },
          policy: { allowAutoStart: false, allowVisible: true, restartPolicy: "off" },
        },
        null,
        2,
      ),
      "utf8",
    );
    fs.writeFileSync(path.join(root, "main.py"), "print('hello')", "utf8");

    const record = buildScriptRecord(root);

    expect(record).toBeTruthy();
    expect(record?.sourceMode).toBe("manifest");
    expect(record?.manifest.id).toBe("compat-demo");
    expect(record?.manifest.logging.filePath?.endsWith(path.join("logs", "app.log"))).toBe(true);
  });

  test("detects pyproject package entry as module command", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-pyproject-"));
    fs.mkdirSync(path.join(root, "src", "demo_pkg"), { recursive: true });
    fs.writeFileSync(
      path.join(root, "pyproject.toml"),
      [
        "[project]",
        'name = "demo-pkg"',
        'version = "0.1.0"',
        "",
        "[project.scripts]",
        'demo-pkg = "demo_pkg.cli:main"',
        "",
      ].join("\n"),
      "utf8",
    );
    fs.writeFileSync(path.join(root, "src", "demo_pkg", "__main__.py"), "print('ok')", "utf8");
    fs.writeFileSync(
      path.join(root, "src", "demo_pkg", "cli.py"),
      'parser.add_parser("run")\n',
      "utf8",
    );

    const record = buildScriptRecord(root);

    expect(record).toBeTruthy();
    expect(record?.manifest.entry.command).toBe("python");
    expect(record?.manifest.entry.args).toEqual(["-m", "demo_pkg", "run"]);
    expect(record?.manifest.capabilities).toContain("oneshot");
  });

  test("detects node project with start script", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-node-start-"));
    fs.writeFileSync(
      path.join(root, "package.json"),
      JSON.stringify(
        {
          name: "node-start",
          version: "1.0.0",
          scripts: { start: "node server.js" },
        },
        null,
        2,
      ),
      "utf8",
    );

    const detected = detectManifest(root);
    expect(detected.manifest).toBeTruthy();
    expect(detected.sourceMode).toBe("heuristic");
    expect(detected.manifest?.type).toBe("node");
    expect(detected.manifest?.entry.command).toBe("npm");
    expect(detected.manifest?.entry.args).toEqual(["run", "start"]);
  });

  test("detects node project using package main fallback", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-node-main-"));
    fs.writeFileSync(
      path.join(root, "package.json"),
      JSON.stringify(
        {
          name: "node-main",
          version: "1.0.0",
          main: "server.js",
        },
        null,
        2,
      ),
      "utf8",
    );
    fs.writeFileSync(path.join(root, "server.js"), "console.log('ok')", "utf8");

    const record = buildScriptRecord(root);
    expect(record?.manifest.type).toBe("node");
    expect(record?.manifest.entry.command).toBe("node");
    expect(record?.manifest.entry.args).toEqual(["server.js"]);
  });

  test("detects node project using default entry file fallback", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-node-default-"));
    fs.writeFileSync(
      path.join(root, "package.json"),
      JSON.stringify(
        {
          name: "node-default",
          version: "1.0.0",
        },
        null,
        2,
      ),
      "utf8",
    );
    fs.writeFileSync(path.join(root, "index.js"), "console.log('ok')", "utf8");

    const record = buildScriptRecord(root);
    expect(record?.manifest.type).toBe("node");
    expect(record?.manifest.entry.command).toBe("node");
    expect(record?.manifest.entry.args).toEqual(["index.js"]);
  });

  test("detects powershell project from run.ps1", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-pwsh-"));
    fs.writeFileSync(path.join(root, "run.ps1"), "Write-Output 'ok'", "utf8");

    const record = buildScriptRecord(root);
    expect(record?.manifest.type).toBe("powershell");
    expect(record?.manifest.entry.command).toBe("powershell");
    expect(record?.manifest.entry.args).toContain("-File");
    expect(record?.manifest.entry.args).toContain("run.ps1");
  });

  test("detects batch project from run.cmd", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-batch-"));
    fs.writeFileSync(path.join(root, "run.cmd"), "@echo off", "utf8");

    const record = buildScriptRecord(root);
    expect(record?.manifest.type).toBe("bat");
    expect(record?.manifest.entry.command).toBe("cmd");
    expect(record?.manifest.entry.args).toEqual(["/c", "run.cmd"]);
  });

  test("detects single-executable project", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-exe-"));
    fs.writeFileSync(path.join(root, "tool.exe"), "", "utf8");

    const record = buildScriptRecord(root);
    expect(record?.manifest.type).toBe("exe");
    expect(record?.manifest.entry.command.endsWith("tool.exe")).toBe(true);
  });

  test("does not detect executable manifest when multiple exe candidates exist", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-exe-many-"));
    fs.mkdirSync(path.join(root, "bin"), { recursive: true });
    fs.writeFileSync(path.join(root, "tool1.exe"), "", "utf8");
    fs.writeFileSync(path.join(root, "bin", "tool2.exe"), "", "utf8");

    const detected = detectManifest(root);
    expect(detected.manifest).toBeUndefined();
    expect(detected.heuristicReason).toBe("unrecognized");
  });

  test("parseManifestDocument tokenizes startCommand and applies defaults", () => {
    const manifest = parseManifestDocument({
      id: "from-start-command",
      name: "from-start-command",
      type: "node",
      startCommand: 'node "server file.js" --port 3000',
      healthCheck: {
        graceSeconds: 10,
        probes: [{ type: "process", severity: "required" }],
      },
      tags: [" API ", " Demo "],
    });

    expect(manifest.entry.command).toBe("node");
    expect(manifest.entry.args).toEqual(["server file.js", "--port", "3000"]);
    expect(manifest.logging.captureStdout).toBe(true);
    expect(manifest.logging.captureStderr).toBe(true);
    expect(manifest.health.graceSeconds).toBe(10);
    expect(manifest.display.tags).toEqual([" API ", " Demo "]);
  });

  test("parseManifestDocument uses explicit entry over startCommand fallback", () => {
    const manifest = parseManifestDocument({
      id: "explicit-entry",
      name: "explicit-entry",
      type: "python",
      startCommand: "python ignored.py",
      entry: {
        command: "python",
        args: ["main.py"],
        cwd: ".",
        shell: false,
      },
    });

    expect(manifest.entry.args).toEqual(["main.py"]);
  });

  test("detects script-console.manifest.json and preserves configured mode", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-alt-manifest-"));
    fs.writeFileSync(
      path.join(root, "script-console.manifest.json"),
      JSON.stringify(
        {
          id: "alt-manifest",
          name: "Daily Report Service",
          description: "Generates daily report summary over http endpoint",
          version: "1.0.0",
          author: "tester",
          type: "node",
          entry: {
            command: "node",
            args: ["server.js"],
            cwd: ".",
            shell: false,
          },
          stop: { mode: "process", timeoutMs: 10000 },
          logging: { filePath: "logs/app.log", captureStdout: true, captureStderr: true, maxTailLines: 500 },
          health: { graceSeconds: 20, probes: [{ type: "process", severity: "required" }] },
          display: { category: "Custom", tags: ["report", "service"] },
          policy: { allowAutoStart: false, allowVisible: true, restartPolicy: "off" },
        },
        null,
        2,
      ),
      "utf8",
    );
    fs.writeFileSync(path.join(root, "server.js"), "console.log('ok')", "utf8");

    const record = buildScriptRecord(root);
    expect(record?.sourceMode).toBe("manifest");
    expect(record?.manifestPath?.endsWith("script-console.manifest.json")).toBe(true);
    expect(record?.classificationSource).toBe("hybrid");
    expect(record?.smartTags).toContain("report");
    expect(record?.smartTags).toContain("service");
  });

  test("returns undefined record for unrecognized workspace", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-empty-"));
    const record = buildScriptRecord(root);
    expect(record).toBeUndefined();
  });

  test("validateWorkspacePath allows subpaths and rejects outside paths", () => {
    const root = path.resolve("D:/workspace/root");
    expect(() => validateWorkspacePath(root, path.join(root, "sub"))).not.toThrow();
    expect(() => validateWorkspacePath(root, path.resolve("D:/workspace/other"))).toThrow();
  });

  test("detects pyproject with preview parser and direct-entry fallback", () => {
    const previewRoot = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-pyproject-preview-"));
    fs.mkdirSync(path.join(previewRoot, "src", "demo_preview"), { recursive: true });
    fs.writeFileSync(
      path.join(previewRoot, "pyproject.toml"),
      ["[project]", 'name = "demo-preview"', "", "[project.scripts]", 'demo-preview = "demo_preview.cli:main"'].join("\n"),
      "utf8",
    );
    fs.writeFileSync(path.join(previewRoot, "src", "demo_preview", "__main__.py"), "print('ok')", "utf8");
    fs.writeFileSync(path.join(previewRoot, "src", "demo_preview", "cli.py"), 'parser.add_parser("preview")', "utf8");
    const previewRecord = buildScriptRecord(previewRoot);
    expect(previewRecord?.manifest.entry.args).toEqual(["-m", "demo_preview", "preview"]);

    const fallbackRoot = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-pyproject-fallback-"));
    fs.writeFileSync(path.join(fallbackRoot, "pyproject.toml"), "[project]\nversion='0.1.0'", "utf8");
    fs.writeFileSync(path.join(fallbackRoot, "main.py"), "print('fallback')", "utf8");
    const fallbackRecord = buildScriptRecord(fallbackRoot);
    expect(fallbackRecord?.manifest.entry.command).toBe("python");
    expect(fallbackRecord?.manifest.entry.args).toEqual(["main.py"]);
  });
});
