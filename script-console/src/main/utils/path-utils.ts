import fs from "node:fs";
import path from "node:path";

export function ensureDir(target: string): string {
  fs.mkdirSync(target, { recursive: true });
  return target;
}

export function ensureParentDir(filePath: string): void {
  ensureDir(path.dirname(filePath));
}

export function fileExists(target: string): boolean {
  try {
    fs.accessSync(target, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

export function isDirectory(target: string): boolean {
  try {
    return fs.statSync(target).isDirectory();
  } catch {
    return false;
  }
}

export function isSubPath(parentPath: string, childPath: string): boolean {
  const parent = path.resolve(parentPath).toLowerCase();
  const child = path.resolve(childPath).toLowerCase();
  return child === parent || child.startsWith(`${parent}${path.sep}`);
}

export function safeResolve(rootDir: string, maybeRelativePath: string | undefined): string | undefined {
  if (!maybeRelativePath) {
    return undefined;
  }
  return path.isAbsolute(maybeRelativePath)
    ? path.normalize(maybeRelativePath)
    : path.resolve(rootDir, maybeRelativePath);
}

export function normalizeTag(value: string): string {
  return value.trim().toLowerCase();
}

export function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-_]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function readJsonFile<T>(target: string): T | undefined {
  try {
    const raw = fs.readFileSync(target, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return undefined;
  }
}

export function writeJsonFile(target: string, value: unknown): void {
  ensureParentDir(target);
  fs.writeFileSync(target, JSON.stringify(value, null, 2), "utf8");
}

export function listFirstLevelDirectories(target: string): string[] {
  if (!isDirectory(target)) {
    return [];
  }
  return fs
    .readdirSync(target, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(target, entry.name));
}

export function toPosixPath(value: string): string {
  return value.split(path.sep).join("/");
}
