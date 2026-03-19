import fs from "node:fs";
import path from "node:path";
import { buildSampleProjects } from "@main/utils/template-catalog";
import { ensureParentDir, fileExists } from "@main/utils/path-utils";

export class SampleProjectService {
  ensure(rootDir: string): string[] {
    const created: string[] = [];
    for (const project of buildSampleProjects()) {
      const targetRoot = path.join(rootDir, project.directoryName);
      let touched = false;
      for (const file of project.files) {
        const target = path.join(targetRoot, file.relativePath);
        if (fileExists(target)) {
          continue;
        }
        ensureParentDir(target);
        fs.writeFileSync(target, file.content, "utf8");
        touched = true;
      }
      if (touched) {
        created.push(targetRoot);
      }
    }
    return created;
  }
}
