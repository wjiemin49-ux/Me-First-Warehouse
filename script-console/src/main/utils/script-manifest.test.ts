import { describe, expect, test } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { buildScriptRecord } from "./script-manifest";

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
});
