import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, test } from "vitest";
import { assertSafeLaunch, assertSafeStopCommand, isAllowedExecutable } from "./command-security";

describe("command-security", () => {
  test("allows known executables even with wrapping quotes", () => {
    expect(isAllowedExecutable('"python"', "D:/root")).toBe(true);
    expect(isAllowedExecutable("  node  ", "D:/root")).toBe(true);
  });

  test("allows absolute executable under script root when file exists", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-cmd-root-"));
    const bin = path.join(root, "bin");
    fs.mkdirSync(bin, { recursive: true });
    const executable = path.join(bin, "tool.exe");
    fs.writeFileSync(executable, "", "utf8");

    expect(isAllowedExecutable(executable, root)).toBe(true);
    expect(isAllowedExecutable(path.join(root, "bin", "missing.exe"), root)).toBe(false);
  });

  test("rejects command not in allow list", () => {
    expect(isAllowedExecutable("bash", "D:/root")).toBe(false);
  });

  test("assertSafeLaunch blocks shell=true and disallowed command", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-launch-"));
    expect(() =>
      assertSafeLaunch(
        {
          command: "node",
          args: ["index.js"],
          cwd: root,
          shell: true,
        },
        root,
      ),
    ).toThrow();

    expect(() =>
      assertSafeLaunch(
        {
          command: "bash",
          args: ["run.sh"],
          cwd: root,
          shell: false,
        },
        root,
      ),
    ).toThrow();
  });

  test("assertSafeLaunch accepts safe launch config", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-launch-safe-"));
    expect(() =>
      assertSafeLaunch(
        {
          command: "node",
          args: ["index.js"],
          cwd: root,
          shell: false,
        },
        root,
      ),
    ).not.toThrow();
  });

  test("assertSafeStopCommand validates command and cwd scope", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-stop-safe-"));
    const outside = fs.mkdtempSync(path.join(os.tmpdir(), "script-console-stop-outside-"));

    expect(() => assertSafeStopCommand(undefined, root)).not.toThrow();
    expect(() =>
      assertSafeStopCommand(
        {
          command: "node",
          args: ["stop.js"],
          cwd: root,
        },
        root,
      ),
    ).not.toThrow();
    expect(() =>
      assertSafeStopCommand(
        {
          command: "bash",
          args: [],
        },
        root,
      ),
    ).toThrow();
    expect(() =>
      assertSafeStopCommand(
        {
          command: "node",
          args: [],
          cwd: outside,
        },
        root,
      ),
    ).toThrow();
  });
});
