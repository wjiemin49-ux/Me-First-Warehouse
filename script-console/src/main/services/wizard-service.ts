import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { manifestJsonSchema } from "@shared/manifest-json-schema";
import { manifestSchema, wizardTemplateSchema } from "@shared/schema";
import {
  ScriptManifest,
  WizardDetectResult,
  WizardHealthResult,
  WizardLaunchResult,
  WizardTemplateInput,
} from "@shared/types";
import { buildScriptRecord, detectManifest, parseManifestDocument } from "@main/utils/script-manifest";
import { buildTemplateProject } from "@main/utils/template-catalog";
import { ensureDir, ensureParentDir, fileExists } from "@main/utils/path-utils";

export class WizardService {
  detect(rootDir: string): WizardDetectResult {
    const detected = detectManifest(rootDir);
    return {
      rootDir,
      detected: Boolean(detected.manifest),
      sourceMode: detected.sourceMode,
      manifest: detected.manifest,
      heuristicReason: detected.heuristicReason,
      warnings: detected.warnings,
      errors: [],
    };
  }

  validateManifest(content: string, rootDir: string): WizardDetectResult {
    try {
      const parsed = parseManifestDocument(JSON.parse(content));
      return {
        rootDir,
        detected: true,
        sourceMode: "manifest",
        manifest: parsed,
        warnings: [],
        errors: [],
      };
    } catch (error) {
      return {
        rootDir,
        detected: false,
        sourceMode: "manifest",
        warnings: [],
        errors: [error instanceof Error ? error.message : "Manifest 校验失败"],
      };
    }
  }

  getManifestSchema(): unknown {
    return manifestJsonSchema;
  }

  async testLaunch(manifest: ScriptManifest, rootDir: string): Promise<WizardLaunchResult> {
    return new Promise((resolve) => {
      const child = spawn(manifest.entry.command, manifest.entry.args, {
        cwd: path.resolve(rootDir, manifest.entry.cwd),
        shell: false,
        windowsHide: true,
      });

      let output = "";
      child.stdout.on("data", (chunk) => {
        output += chunk.toString("utf8");
      });
      child.stderr.on("data", (chunk) => {
        output += chunk.toString("utf8");
      });
      child.on("error", (error) => {
        resolve({
          success: false,
          message: error.message,
          outputSnippet: output.slice(-500),
        });
      });
      child.on("spawn", () => {
        setTimeout(() => {
          try {
            child.kill();
          } catch {
            // ignore
          }
          resolve({
            success: true,
            message: "启动测试成功",
            pid: child.pid,
            outputSnippet: output.slice(-500),
          });
        }, 4000);
      });
    });
  }

  async testHealth(manifest: ScriptManifest, rootDir: string): Promise<WizardHealthResult> {
    const checks = manifest.health.probes.map((probe) => {
      if (probe.type === "heartbeat-file") {
        const target = path.resolve(rootDir, probe.path);
        return {
          type: probe.type,
          success: fileExists(target),
          message: fileExists(target) ? "heartbeat 文件存在" : "heartbeat 文件不存在",
        };
      }
      if (probe.type === "log-update") {
        const target = path.resolve(rootDir, probe.path ?? "logs/app.log");
        return {
          type: probe.type,
          success: fileExists(target),
          message: fileExists(target) ? "日志文件存在" : "日志文件不存在",
        };
      }
      if (probe.type === "port") {
        return {
          type: probe.type,
          success: true,
          message: `端口 ${probe.port} 配置有效`,
        };
      }
      if (probe.type === "http") {
        return {
          type: probe.type,
          success: probe.url.startsWith("http://127.0.0.1") || probe.url.startsWith("http://localhost"),
          message: "HTTP 健康检查配置有效",
        };
      }
      return {
        type: probe.type,
        success: true,
        message: "进程探针配置有效",
      };
    });

    return {
      success: checks.every((item) => item.success),
      message: checks.every((item) => item.success) ? "健康检查配置有效" : "存在失败的健康检查配置",
      checks,
    };
  }

  generateTemplate(input: WizardTemplateInput): string {
    const validated = wizardTemplateSchema.parse(input);
    const project = buildTemplateProject(validated);
    const targetRoot = path.join(validated.targetDirectory, project.directoryName);
    ensureDir(targetRoot);
    for (const file of project.files) {
      const target = path.join(targetRoot, file.relativePath);
      ensureParentDir(target);
      fs.writeFileSync(target, file.content, "utf8");
    }
    return targetRoot;
  }

  importExisting(sourceDir: string, workspaceRoot: string): string {
    const detection = buildScriptRecord(sourceDir);
    if (!detection) {
      throw new Error("无法识别该脚本目录");
    }
    const junctionPath = path.join(workspaceRoot, detection.id);
    if (fs.existsSync(junctionPath)) {
      throw new Error("目标工作区中已存在同名目录");
    }
    fs.symlinkSync(sourceDir, junctionPath, "junction");
    return junctionPath;
  }
}
