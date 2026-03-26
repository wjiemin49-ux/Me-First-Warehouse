import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const preferredDbDir =
  process.env.FOCUSFLOW_DB_DIR ||
  (process.platform === "win32" && fs.existsSync("D:/me") ? "D:/me" : os.tmpdir());
const defaultDbPath = path.join(preferredDbDir, "focusflow-dev.db").replace(/\\/g, "/");
const nodeEnv = process.env.NODE_ENV ?? "development";

const derivedDevSecret = crypto
  .createHash("sha256")
  .update(`${os.hostname()}::${process.cwd()}`)
  .digest("hex");
const sessionSecret =
  process.env.SESSION_SECRET || (nodeEnv === "production" ? "" : derivedDevSecret);

if (nodeEnv === "production" && !sessionSecret) {
  throw new Error("SESSION_SECRET is required in production.");
}

export const env = {
  nodeEnv,
  databaseUrl: process.env.DATABASE_URL ?? `file:${defaultDbPath}`,
  sessionSecret,
  cookieSecure: process.env.COOKIE_SECURE === "true" || nodeEnv === "production"
};

process.env.DATABASE_URL = env.databaseUrl;
process.env.SESSION_SECRET = env.sessionSecret;
