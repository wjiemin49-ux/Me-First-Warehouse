import path from "node:path";
import { ALLOWED_EXECUTABLES } from "@shared/constants";
import { LaunchConfig, StopCommandConfig } from "@shared/types";
import { fileExists, isSubPath } from "./path-utils";

function normalizeCommand(command: string): string {
  return command.trim().replace(/^"+|"+$/g, "");
}

export function isAllowedExecutable(command: string, scriptRoot: string): boolean {
  const normalized = normalizeCommand(command);
  const lower = path.basename(normalized).toLowerCase();
  if (ALLOWED_EXECUTABLES.includes(lower)) {
    return true;
  }
  if (path.isAbsolute(normalized) && isSubPath(scriptRoot, normalized) && fileExists(normalized)) {
    return true;
  }
  return false;
}

export function assertSafeLaunch(config: LaunchConfig, scriptRoot: string): void {
  if (config.shell) {
    throw new Error("禁止使用 shell=true 的启动配置");
  }
  if (!isAllowedExecutable(config.command, scriptRoot)) {
    throw new Error(`不允许的启动命令: ${config.command}`);
  }
  const cwd = path.resolve(config.cwd);
  if (!isSubPath(scriptRoot, cwd) && !path.isAbsolute(cwd)) {
    throw new Error("工作目录必须位于脚本目录内或为合法绝对路径");
  }
}

export function assertSafeStopCommand(config: StopCommandConfig | undefined, scriptRoot: string): void {
  if (!config) {
    return;
  }
  if (!isAllowedExecutable(config.command, scriptRoot)) {
    throw new Error(`不允许的停止命令: ${config.command}`);
  }
  if (config.cwd) {
    const cwd = path.resolve(config.cwd);
    if (!isSubPath(scriptRoot, cwd)) {
      throw new Error("停止命令工作目录必须位于脚本目录内");
    }
  }
}
