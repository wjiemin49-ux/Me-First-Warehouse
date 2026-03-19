import fs from "node:fs";
import { ProcessMatchConfig, RuntimeResourceSample } from "@shared/types";
import { runPowerShellJson } from "@main/utils/powershell";

interface RawProcessSample {
  cpuPercent?: number;
  memoryMb?: number;
  threadCount?: number;
  ports?: number[];
}

export class ResourceSampler {
  async processExists(pid: number): Promise<boolean> {
    try {
      const result = await runPowerShellJson<Array<{ Id: number }>>(
        `@(Get-Process -Id ${pid} -ErrorAction SilentlyContinue | Select-Object Id) | ConvertTo-Json -Compress`,
      );
      return Array.isArray(result) ? result.length > 0 : Boolean((result as { Id?: number })?.Id);
    } catch {
      return false;
    }
  }

  async findExternalProcess(processMatch: ProcessMatchConfig): Promise<number | undefined> {
    const conditions: string[] = [];
    if (processMatch.executableName) {
      conditions.push(`$_.Name -eq '${processMatch.executableName.replace(/'/g, "''")}'`);
    }
    if (processMatch.commandLineIncludes) {
      conditions.push(`$_.CommandLine -like '*${processMatch.commandLineIncludes.replace(/'/g, "''")}*'`);
    }
    if (!conditions.length) {
      return undefined;
    }
    try {
      const rows = await runPowerShellJson<Array<{ ProcessId: number }>>(
        `@(Get-CimInstance Win32_Process | Where-Object { ${conditions.join(" -and ")} } | Select-Object ProcessId | Select-Object -First 1) | ConvertTo-Json -Compress`,
      );
      const row = Array.isArray(rows) ? rows[0] : (rows as { ProcessId?: number });
      return row?.ProcessId;
    } catch {
      return undefined;
    }
  }

  async sample(pid: number, trackedFilePath?: string): Promise<RuntimeResourceSample> {
    try {
      const query = `
        $perf = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object { $_.IDProcess -eq ${pid} } | Select-Object PercentProcessorTime, WorkingSetPrivate, ThreadCount;
        $ports = @(Get-NetTCPConnection -OwningProcess ${pid} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalPort);
        if ($perf) {
          [pscustomobject]@{
            cpuPercent = [double]$perf.PercentProcessorTime;
            memoryMb = [math]::Round([double]$perf.WorkingSetPrivate / 1MB, 2);
            threadCount = [int]$perf.ThreadCount;
            ports = $ports;
          } | ConvertTo-Json -Compress
        }
      `;
      const raw = await runPowerShellJson<RawProcessSample>(query);
      return {
        cpuPercent: raw?.cpuPercent ?? null,
        memoryMb: raw?.memoryMb ?? null,
        threadCount: raw?.threadCount ?? null,
        runtimeSeconds: null,
        ports: raw?.ports ?? [],
        lastFileUpdateAt: trackedFilePath && fs.existsSync(trackedFilePath) ? fs.statSync(trackedFilePath).mtime.toISOString() : undefined,
      };
    } catch {
      return {
        cpuPercent: null,
        memoryMb: null,
        threadCount: null,
        runtimeSeconds: null,
        ports: [],
        lastFileUpdateAt: trackedFilePath && fs.existsSync(trackedFilePath) ? fs.statSync(trackedFilePath).mtime.toISOString() : undefined,
      };
    }
  }
}
