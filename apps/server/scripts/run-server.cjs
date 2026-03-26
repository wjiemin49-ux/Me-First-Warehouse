const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const preferredDbDir =
  process.env.FOCUSFLOW_DB_DIR ||
  (process.platform === "win32" && fs.existsSync("D:/me") ? "D:/me" : os.tmpdir());
if (!fs.existsSync(preferredDbDir)) {
  fs.mkdirSync(preferredDbDir, { recursive: true });
}
const devDbPath = path.join(preferredDbDir, "focusflow-dev.db").replace(/\\/g, "/");
const env = {
  ...process.env,
  DATABASE_URL: process.env.DATABASE_URL || `file:${devDbPath}`
};

function run(command, args) {
  console.log(`> ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, {
    stdio: "inherit",
    cwd: process.cwd(),
    env,
    shell: true
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  if (result.status !== 0) {
    console.error(`Command failed: ${command} ${args.join(" ")}`);
    process.exit(result.status ?? 1);
  }
}

run("pnpm", ["prisma:generate"]);
run("pnpm", ["prisma:push"]);
run("tsx", ["src/index.ts"]);
