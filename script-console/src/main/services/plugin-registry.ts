import fs from "node:fs";
import path from "node:path";
import { PluginDescriptor, PluginManifest } from "@shared/types";
import { DEFAULT_PLUGIN_DIRECTORY_NAME } from "@shared/constants";

const PLUGIN_MANIFEST = "plugin.manifest.json";

function isPluginManifest(value: unknown): value is PluginManifest {
  if (!value || typeof value !== "object") return false;
  const manifest = value as Record<string, unknown>;
  return (
    typeof manifest.id === "string" &&
    typeof manifest.name === "string" &&
    typeof manifest.version === "string" &&
    typeof manifest.author === "string" &&
    manifest.apiVersion === 1 &&
    Array.isArray(manifest.hooks)
  );
}

export class PluginRegistry {
  getRoot(scriptRoot: string): string {
    return path.join(scriptRoot, DEFAULT_PLUGIN_DIRECTORY_NAME);
  }

  list(scriptRoot: string): PluginDescriptor[] {
    const pluginRoot = this.getRoot(scriptRoot);
    if (!fs.existsSync(pluginRoot)) {
      return [];
    }
    return fs
      .readdirSync(pluginRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .flatMap((entry) => {
        const rootDir = path.join(pluginRoot, entry.name);
        const manifestPath = path.join(rootDir, PLUGIN_MANIFEST);
        if (!fs.existsSync(manifestPath)) {
          return [];
        }
        try {
          const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
          if (!isPluginManifest(manifest)) {
            return [];
          }
          return [{ manifest, rootDir, manifestPath }];
        } catch {
          return [];
        }
      });
  }
}
