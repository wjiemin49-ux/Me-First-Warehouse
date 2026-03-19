import { spawn } from "node:child_process";

export async function runPowerShell(command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(
      "powershell",
      [
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
      ],
      {
        windowsHide: true,
      },
    );

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve(stdout.trim());
        return;
      }
      reject(new Error(stderr.trim() || `PowerShell exited with code ${code}`));
    });
  });
}

export async function runPowerShellJson<T>(command: string): Promise<T> {
  const output = await runPowerShell(command);
  if (!output) {
    return [] as T;
  }
  return JSON.parse(output) as T;
}
