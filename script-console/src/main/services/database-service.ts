import type { DatabaseSync as DatabaseSyncType } from "node:sqlite";
import { ensureDir } from "@main/utils/path-utils";
import path from "node:path";

const { DatabaseSync } = (eval("require") as NodeJS.Require)("node:sqlite") as {
  DatabaseSync: typeof DatabaseSyncType;
};

const SCHEMA_SQL = `
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scripts (
  id TEXT PRIMARY KEY,
  source_mode TEXT NOT NULL,
  root_dir TEXT NOT NULL,
  manifest_path TEXT,
  folder_name TEXT NOT NULL,
  heuristic_reason TEXT,
  is_configured INTEGER NOT NULL DEFAULT 0,
  is_missing INTEGER NOT NULL DEFAULT 0,
  manifest_json TEXT NOT NULL,
  indexed_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS script_runtime (
  script_id TEXT PRIMARY KEY REFERENCES scripts(id) ON DELETE CASCADE,
  lifecycle_state TEXT NOT NULL,
  display_status TEXT NOT NULL,
  health_state TEXT NOT NULL,
  desired_state TEXT NOT NULL DEFAULT 'stopped',
  pid INTEGER,
  last_started_at TEXT,
  last_stopped_at TEXT,
  last_exit_code INTEGER,
  last_failure_reason TEXT,
  uptime_started_at TEXT,
  restart_count INTEGER NOT NULL DEFAULT 0,
  fault_count INTEGER NOT NULL DEFAULT 0,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  circuit_state TEXT NOT NULL DEFAULT 'closed',
  circuit_opened_at TEXT,
  circuit_reason TEXT,
  next_retry_at TEXT,
  external_process INTEGER NOT NULL DEFAULT 0,
  last_health_summary TEXT,
  resource_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id TEXT NOT NULL,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  pid INTEGER,
  exit_code INTEGER,
  message TEXT,
  started_at TEXT,
  ended_at TEXT,
  duration_seconds INTEGER,
  triggered_by TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS health_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id TEXT NOT NULL,
  probe_type TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT,
  latency_ms INTEGER,
  created_at TEXT NOT NULL,
  details_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS operation_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id TEXT,
  action TEXT NOT NULL,
  actor TEXT NOT NULL,
  success INTEGER NOT NULL,
  message TEXT,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS scan_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  root_dir TEXT NOT NULL,
  summary TEXT,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS log_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  level TEXT NOT NULL,
  source TEXT NOT NULL,
  message TEXT NOT NULL,
  raw TEXT NOT NULL,
  file_path TEXT,
  line_number INTEGER,
  created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS log_index USING fts5(
  script_id UNINDEXED,
  level UNINDEXED,
  message,
  raw,
  content='log_events',
  content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS log_events_ai AFTER INSERT ON log_events BEGIN
  INSERT INTO log_index(rowid, script_id, level, message, raw)
  VALUES (new.id, new.script_id, new.level, new.message, new.raw);
END;

CREATE TRIGGER IF NOT EXISTS log_events_ad AFTER DELETE ON log_events BEGIN
  INSERT INTO log_index(log_index, rowid, script_id, level, message, raw)
  VALUES ('delete', old.id, old.script_id, old.level, old.message, old.raw);
END;

CREATE TRIGGER IF NOT EXISTS log_events_au AFTER UPDATE ON log_events BEGIN
  INSERT INTO log_index(log_index, rowid, script_id, level, message, raw)
  VALUES ('delete', old.id, old.script_id, old.level, old.message, old.raw);
  INSERT INTO log_index(rowid, script_id, level, message, raw)
  VALUES (new.id, new.script_id, new.level, new.message, new.raw);
END;

CREATE INDEX IF NOT EXISTS idx_scripts_root_dir ON scripts(root_dir);
CREATE INDEX IF NOT EXISTS idx_runtime_state ON script_runtime(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_history_script_id ON run_history(script_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_outcome ON run_history(outcome, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_script_id ON health_checks(script_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_script_id ON log_events(script_id, timestamp DESC);
`;

export class DatabaseService {
  private readonly db: DatabaseSyncType;

  constructor(public readonly dbPath: string) {
    ensureDir(path.dirname(dbPath));
    this.db = new DatabaseSync(dbPath);
    this.db.exec(SCHEMA_SQL);
    this.ensureRuntimeColumns();
  }

  private ensureRuntimeColumns(): void {
    const columns = new Set(
      this.db
        .prepare("PRAGMA table_info(script_runtime)")
        .all() as Array<{ name: string }>,
    );

    const hasColumn = (name: string) =>
      (this.db.prepare("PRAGMA table_info(script_runtime)").all() as Array<{ name: string }>).some(
        (column) => column.name === name,
      );

    if (!hasColumn("consecutive_failures")) {
      this.db.exec("ALTER TABLE script_runtime ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0");
    }
    if (!hasColumn("circuit_state")) {
      this.db.exec("ALTER TABLE script_runtime ADD COLUMN circuit_state TEXT NOT NULL DEFAULT 'closed'");
    }
    if (!hasColumn("circuit_opened_at")) {
      this.db.exec("ALTER TABLE script_runtime ADD COLUMN circuit_opened_at TEXT");
    }
    if (!hasColumn("circuit_reason")) {
      this.db.exec("ALTER TABLE script_runtime ADD COLUMN circuit_reason TEXT");
    }
    if (!hasColumn("next_retry_at")) {
      this.db.exec("ALTER TABLE script_runtime ADD COLUMN next_retry_at TEXT");
    }
  }

  run(sql: string, params?: Record<string, unknown>): void {
    if (params) {
      this.db.prepare(sql).run(params as never);
      return;
    }
    this.db.exec(sql);
  }

  get<T>(sql: string, params?: Record<string, unknown>): T | undefined {
    return this.db.prepare(sql).get((params ?? {}) as never) as T | undefined;
  }

  all<T>(sql: string, params?: Record<string, unknown>): T[] {
    return this.db.prepare(sql).all((params ?? {}) as never) as T[];
  }

  exec(sql: string): void {
    this.db.exec(sql);
  }

  transaction<T>(callback: () => T): T {
    this.db.exec("BEGIN");
    try {
      const result = callback();
      this.db.exec("COMMIT");
      return result;
    } catch (error) {
      this.db.exec("ROLLBACK");
      throw error;
    }
  }

  close(): void {
    this.db.close();
  }
}
