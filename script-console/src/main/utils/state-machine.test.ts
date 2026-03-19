import { describe, expect, test } from "vitest";
import { lifecycleToDisplayStatus } from "./state-machine";

describe("state machine", () => {
  test("maps running to visible status", () => {
    expect(lifecycleToDisplayStatus("running")).toBe("运行中");
    expect(lifecycleToDisplayStatus("crashed")).toBe("异常退出");
  });
});
