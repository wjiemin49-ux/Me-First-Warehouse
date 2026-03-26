import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const preferredDbDir =
  process.env.FOCUSFLOW_DB_DIR ||
  (process.platform === "win32" && fs.existsSync("D:/me") ? "D:/me" : os.tmpdir());
const testDbPath = path.join(preferredDbDir, "focusflow-test.db").replace(/\\/g, "/");

process.env.NODE_ENV = "test";
process.env.DATABASE_URL = process.env.DATABASE_URL ?? `file:${testDbPath}`;
process.env.SESSION_SECRET = process.env.SESSION_SECRET ?? "focusflow-test-secret";
