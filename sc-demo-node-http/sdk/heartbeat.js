const fs = require("node:fs");
const path = require("node:path");

function writeHeartbeat(rootDir, status = "alive", extra = {}) {
  const filePath = path.join(rootDir, "runtime", "heartbeat.json");
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const payload = {
    timestamp: new Date().toISOString(),
    status,
    ...extra,
  };
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));
}

module.exports = { writeHeartbeat };
