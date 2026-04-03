import { describe, expect, test, vi } from "vitest";
import { nowIso, secondsBetween, startOfTodayIso } from "./time-utils";

describe("time-utils", () => {
  test("nowIso returns ISO string", () => {
    const value = nowIso();
    expect(new Date(value).toISOString()).toBe(value);
  });

  test("startOfTodayIso normalizes to midnight", () => {
    const value = startOfTodayIso();
    const date = new Date(value);
    expect(date.getHours()).toBe(0);
    expect(date.getMinutes()).toBe(0);
    expect(date.getSeconds()).toBe(0);
    expect(date.getMilliseconds()).toBe(0);
  });

  test("secondsBetween handles empty start and negative duration", () => {
    expect(secondsBetween(undefined)).toBeUndefined();
    expect(secondsBetween("2026-01-01T00:00:10.000Z", "2026-01-01T00:00:05.000Z")).toBe(0);
  });

  test("secondsBetween uses nowIso by default", () => {
    const spy = vi
      .spyOn(globalThis.Date, "parse")
      .mockImplementation((input: string) => new Date(input).getTime());
    expect(secondsBetween("2026-01-01T00:00:00.000Z", "2026-01-01T00:00:05.900Z")).toBe(5);
    spy.mockRestore();
  });
});
