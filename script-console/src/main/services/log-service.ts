import fs from "node:fs";
import path from "node:path";
import { ChildProcessWithoutNullStreams } from "node:child_process";
import { AppSettings, LogEvent, LogLevel, LogSearchFilters, ScriptSummary } from "@shared/types";
import { DatabaseService } from "./database-service";
import { EventBus } from "./event-bus";
import { ensureDir, ensureParentDir, fileExists } from "@main/utils/path-utils";
import { nowIso } from "@main/utils/time-utils";

function detectLevel(line: string): LogLevel {
  const upper = line.toUpperCase();
  if (upper.includes("[TRACE]")) return "TRACE";
  if (upper.includes("[DEBUG]")) return "DEBUG";
  if (upper.includes("[INFO]")) return "INFO";
  if (upper.includes("[WARN]")) return "WARN";
  if (upper.includes("[ERROR]")) return "ERROR";
  if (upper.includes("[FATAL]")) return "FATAL";
  try {
    const parsed = JSON.parse(line) as { level?: string };
    if (parsed.level) {
      return parsed.level.toUpperCase() as LogLevel;
    }
  } catch {
    // noop
  }
  return "UNKNOWN";
}

function detectTimestamp(line: string): string {
  const match = line.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z/);
  if (match?.[0]) {
    return new Date(match[0]).toISOString();
  }
  try {
    const parsed = JSON.parse(line) as { timestamp?: string; time?: string };
    const ts = parsed.timestamp ?? parsed.time;
    if (ts) {
      return new Date(ts).toISOString();
    }
  } catch {
    // noop
  }
  return nowIso();
}

export class LogService {
  private readonly fileWatchers = new Map<string, fs.FSWatcher>();
  private readonly watchedSizes = new Map<string, number>();

  constructor(
    private readonly db: DatabaseService,
    private readonly events: EventBus,
    private readonly getSettings: () => AppSettings,
  ) {}

  private getGeneratedLogsDir(): string {
    return ensureDir(path.join(this.getSettings().dataDirectory, "logs"));
  }

  private getExportsDir(): string {
    return ensureDir(path.join(this.getSettings().dataDirectory, "exports"));
  }

  resolveLogPath(summary: ScriptSummary): string {
    return summary.record.manifest.logging.filePath
      ? summary.record.manifest.logging.filePath
      : path.join(this.getGeneratedLogsDir(), `${summary.record.id}.log`);
  }

  private ingestLine(
    scriptId: string,
    source: "stdout" | "stderr" | "file",
    raw: string,
    filePath?: string,
    lineNumber?: number,
  ): void {
    const message = raw.trim();
    if (!message) {
      return;
    }
    const timestamp = detectTimestamp(message);
    const level = detectLevel(message);
    this.db.run(
      `
      INSERT INTO log_events(script_id, timestamp, level, source, message, raw, file_path, line_number, created_at)
      VALUES(:scriptId, :timestamp, :level, :source, :message, :raw, :filePath, :lineNumber, :createdAt)
      `,
      {
        scriptId,
        timestamp,
        level,
        source,
        message,
        raw,
        filePath: filePath ?? null,
        lineNumber: lineNumber ?? null,
        createdAt: nowIso(),
      },
    );
    this.events.emit("logs-updated", { scriptId });
  }

  attachProcessStreams(summary: ScriptSummary, child: ChildProcessWithoutNullStreams): () => void {
    const logPath = this.resolveLogPath(summary);
    ensureParentDir(logPath);
    const stream = fs.createWriteStream(logPath, { flags: "a" });
    const buffers = new Map<string, string>([
      ["stdout", ""],
      ["stderr", ""],
    ]);

    const consumeChunk = (source: "stdout" | "stderr", chunk: Buffer) => {
      const text = chunk.toString("utf8");
      stream.write(text);
      const previous = buffers.get(source) ?? "";
      const combined = previous + text;
      const lines = combined.split(/\r?\n/);
      const incomplete = lines.pop() ?? "";
      buffers.set(source, incomplete);
      lines.forEach((line) => this.ingestLine(summary.record.id, source, line, logPath));
    };

    child.stdout.on("data", (chunk) => consumeChunk("stdout", chunk));
    child.stderr.on("data", (chunk) => consumeChunk("stderr", chunk));

    return () => {
      for (const [source, rest] of buffers.entries()) {
        if (rest.trim()) {
          this.ingestLine(summary.record.id, source as "stdout" | "stderr", rest, logPath);
        }
      }
      stream.end();
    };
  }

  watchExternalLogFile(scriptId: string, filePath: string): void {
    if (!fileExists(filePath) || this.fileWatchers.has(scriptId)) {
      return;
    }

    this.watchedSizes.set(scriptId, fs.statSync(filePath).size);
    const watcher = fs.watch(filePath, async (eventType) => {
      if (eventType !== "change") {
        return;
      }
      const previousSize = this.watchedSizes.get(scriptId) ?? 0;
      const currentSize = fs.statSync(filePath).size;
      if (currentSize <= previousSize) {
        this.watchedSizes.set(scriptId, currentSize);
        return;
      }

      const fd = fs.openSync(filePath, "r");
      try {
        const buffer = Buffer.alloc(currentSize - previousSize);
        fs.readSync(fd, buffer, 0, buffer.length, previousSize);
        this.watchedSizes.set(scriptId, currentSize);
        const text = buffer.toString("utf8");
        text
          .split(/\r?\n/)
          .filter(Boolean)
          .forEach((line) => this.ingestLine(scriptId, "file", line, filePath));
      } finally {
        fs.closeSync(fd);
      }
    });

    this.fileWatchers.set(scriptId, watcher);
  }

  stopWatching(scriptId: string): void {
    this.fileWatchers.get(scriptId)?.close();
    this.fileWatchers.delete(scriptId);
    this.watchedSizes.delete(scriptId);
  }

  getTail(scriptId?: string, limit = 300): LogEvent[] {
    const rows = this.db.all<LogEvent & { scriptId: string }>(
      `
      SELECT
        id,
        script_id AS scriptId,
        timestamp,
        level,
        source,
        message,
        raw,
        file_path AS filePath,
        line_number AS lineNumber
      FROM log_events
      ${scriptId ? "WHERE script_id = :scriptId" : ""}
      ORDER BY id DESC
      LIMIT :limit
      `,
      {
        scriptId,
        limit,
      },
    );
    return rows;
  }

  search(filters: LogSearchFilters): LogEvent[] {
    const params: Record<string, unknown> = {
      limit: filters.limit ?? 300,
    };
    const conditions: string[] = [];

    if (filters.scriptIds?.length) {
      const placeholders = filters.scriptIds.map((_, index) => `:script${index}`);
      filters.scriptIds.forEach((value, index) => {
        params[`script${index}`] = value;
      });
      conditions.push(`le.script_id IN (${placeholders.join(", ")})`);
    }

    if (filters.levels?.length) {
      const placeholders = filters.levels.map((_, index) => `:level${index}`);
      filters.levels.forEach((value, index) => {
        params[`level${index}`] = value;
      });
      conditions.push(`le.level IN (${placeholders.join(", ")})`);
    }

    if (filters.from) {
      conditions.push("le.timestamp >= :from");
      params.from = filters.from;
    }

    if (filters.to) {
      conditions.push("le.timestamp <= :to");
      params.to = filters.to;
    }

    if (filters.search?.trim()) {
      params.match = filters.search.trim().replace(/"/g, '""');
      const sql = `
        SELECT
          le.id,
          le.script_id AS scriptId,
          le.timestamp,
          le.level,
          le.source,
          le.message,
          le.raw,
          le.file_path AS filePath,
          le.line_number AS lineNumber
        FROM log_index li
        JOIN log_events le ON le.id = li.rowid
        WHERE li.log_index MATCH :match
        ${conditions.length ? `AND ${conditions.join(" AND ")}` : ""}
        ORDER BY le.id DESC
        LIMIT :limit
      `;
      return this.db.all<LogEvent>(sql, params);
    }

    const sql = `
      SELECT
        id,
        script_id AS scriptId,
        timestamp,
        level,
        source,
        message,
        raw,
        file_path AS filePath,
        line_number AS lineNumber
      FROM log_events le
      ${conditions.length ? `WHERE ${conditions.join(" AND ")}` : ""}
      ORDER BY id DESC
      LIMIT :limit
    `;
    return this.db.all<LogEvent>(sql, params);
  }

  export(filters: LogSearchFilters): string {
    const rows = this.search({ ...filters, limit: filters.limit ?? 1000 });
    const filePath = path.join(
      this.getExportsDir(),
      `logs-export-${new Date().toISOString().replace(/[:.]/g, "-")}.txt`,
    );
    ensureParentDir(filePath);
    const content = rows
      .map((row) => `${row.timestamp} [${row.level}] [${row.scriptId}] ${row.message}`)
      .join("\n");
    fs.writeFileSync(filePath, content, "utf8");
    return filePath;
  }

  clearIndex(scriptId?: string): void {
    if (scriptId) {
      this.db.run("DELETE FROM log_events WHERE script_id = :scriptId", { scriptId });
      this.events.emit("logs-updated", { scriptId });
      return;
    }
    this.db.exec("DELETE FROM log_events");
    this.events.emit("overview-updated", { changed: true });
  }
}
