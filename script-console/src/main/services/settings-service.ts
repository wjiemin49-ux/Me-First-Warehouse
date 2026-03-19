import path from "node:path";
import { app } from "electron";
import { appSettingsSchema } from "@shared/schema";
import { AppSettings } from "@shared/types";
import { DatabaseService } from "./database-service";

export class SettingsService {
  private cachedSettings: AppSettings;

  constructor(private readonly db: DatabaseService) {
    const defaultRuntimeDirectory = path.join(app.getPath("appData"), "ScriptConsole", "runtime");
    this.cachedSettings = appSettingsSchema.parse({
      dataDirectory: defaultRuntimeDirectory,
    });
  }

  load(): AppSettings {
    const rows = this.db.all<{ key: string; value: string }>("SELECT key, value FROM settings");
    if (rows.length === 0) {
      this.save(this.cachedSettings);
      return this.cachedSettings;
    }
    const persisted = rows.reduce<Record<string, unknown>>((acc, row) => {
      acc[row.key] = JSON.parse(row.value);
      return acc;
    }, {});
    this.cachedSettings = appSettingsSchema.parse({
      ...this.cachedSettings,
      ...persisted,
    });
    return this.cachedSettings;
  }

  get(): AppSettings {
    return this.cachedSettings;
  }

  save(nextSettings: Partial<AppSettings>): AppSettings {
    this.cachedSettings = appSettingsSchema.parse({
      ...this.cachedSettings,
      ...nextSettings,
    });

    this.db.transaction(() => {
      for (const [key, value] of Object.entries(this.cachedSettings)) {
        this.db.run(
          `
          INSERT INTO settings(key, value)
          VALUES(:key, :value)
          ON CONFLICT(key) DO UPDATE SET value = excluded.value
          `,
          {
            key,
            value: JSON.stringify(value),
          },
        );
      }
    });

    return this.cachedSettings;
  }
}
