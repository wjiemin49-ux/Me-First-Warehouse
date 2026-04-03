import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, test } from "vitest";
import {
  ensureDir,
  ensureParentDir,
  fileExists,
  isDirectory,
  isSubPath,
  listFirstLevelDirectories,
  normalizeTag,
  readJsonFile,
  safeResolve,
  slugify,
  toPosixPath,
  writeJsonFile,
} from "./path-utils";

describe("path-utils", () => {
  test("ensureDir and ensureParentDir create directories", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-path-"));
    const nested = path.join(root, "a", "b");
    expect(ensureDir(nested)).toBe(nested);
    expect(fs.existsSync(nested)).toBe(true);

    const fileTarget = path.join(root, "c", "d", "data.json");
    ensureParentDir(fileTarget);
    expect(fs.existsSync(path.dirname(fileTarget))).toBe(true);
  });

  test("fileExists and isDirectory handle present and missing paths", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-path-fs-"));
    const file = path.join(root, "hello.txt");
    fs.writeFileSync(file, "hi", "utf8");

    expect(fileExists(file)).toBe(true);
    expect(fileExists(path.join(root, "missing.txt"))).toBe(false);
    expect(isDirectory(root)).toBe(true);
    expect(isDirectory(file)).toBe(false);
    expect(isDirectory(path.join(root, "missing"))).toBe(false);
  });

  test("isSubPath validates parent-child relationship", () => {
    const root = path.resolve("D:/tmp/root");
    const child = path.join(root, "sub", "file.txt");
    const outsider = path.resolve("D:/tmp/other/file.txt");
    expect(isSubPath(root, root)).toBe(true);
    expect(isSubPath(root, child)).toBe(true);
    expect(isSubPath(root, outsider)).toBe(false);
  });

  test("safeResolve handles undefined, relative and absolute values", () => {
    const root = path.resolve("D:/tmp/root");
    expect(safeResolve(root, undefined)).toBeUndefined();
    expect(safeResolve(root, "logs/app.log")).toBe(path.join(root, "logs", "app.log"));
    expect(safeResolve(root, path.resolve("D:/tmp/abs.txt"))).toBe(path.resolve("D:/tmp/abs.txt"));
  });

  test("normalizeTag and slugify normalize user values", () => {
    expect(normalizeTag("  Data-Flow  ")).toBe("data-flow");
    expect(slugify("  Hello, Script Console!  ")).toBe("hello-script-console");
    expect(slugify("---A__B---")).toBe("a__b");
  });

  test("readJsonFile and writeJsonFile support safe JSON IO", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-path-json-"));
    const target = path.join(root, "meta", "config.json");
    writeJsonFile(target, { enabled: true, retries: 3 });
    expect(readJsonFile<{ enabled: boolean; retries: number }>(target)).toEqual({
      enabled: true,
      retries: 3,
    });

    const invalid = path.join(root, "meta", "invalid.json");
    fs.writeFileSync(invalid, "{oops", "utf8");
    expect(readJsonFile(invalid)).toBeUndefined();
    expect(readJsonFile(path.join(root, "meta", "missing.json"))).toBeUndefined();
  });

  test("listFirstLevelDirectories returns only direct child directories", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-path-list-"));
    const dirs = ["one", "two", "three"];
    for (const dir of dirs) {
      fs.mkdirSync(path.join(root, dir), { recursive: true });
    }
    fs.writeFileSync(path.join(root, "file.txt"), "x", "utf8");

    const listed = listFirstLevelDirectories(root).map((value) => path.basename(value)).sort();
    expect(listed).toEqual(["one", "three", "two"]);
    expect(listFirstLevelDirectories(path.join(root, "missing"))).toEqual([]);
  });

  test("toPosixPath converts separators to slash", () => {
    const original = `foo${path.sep}bar${path.sep}baz.txt`;
    expect(toPosixPath(original)).toBe("foo/bar/baz.txt");
  });
});
