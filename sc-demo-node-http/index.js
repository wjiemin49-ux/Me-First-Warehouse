const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { writeHeartbeat } = require("./sdk/heartbeat");
const root = __dirname;
const logFile = path.join(root, "logs", "app.log");
fs.mkdirSync(path.dirname(logFile), { recursive: true });
const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ ok: true, timestamp: new Date().toISOString() }));
  }
  res.writeHead(200);
  res.end("Script Console demo service");
});
server.listen(43101, "127.0.0.1");
setInterval(() => {
  writeHeartbeat(root, "alive", { port: 43101 });
  const line = new Date().toISOString() + " [INFO] node demo service alive\n";
  fs.appendFileSync(logFile, line);
  console.log(line.trim());
}, 15000);
