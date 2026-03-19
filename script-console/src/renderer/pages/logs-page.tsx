import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { toast } from "react-hot-toast";
import { Download, Eraser, Search } from "lucide-react";
import { LogEvent, ScriptSummary } from "@shared/types";
import { Button, Card, CardHeader, EmptyState, StatCard } from "@renderer/components/ui/primitives";

export function LogsPage() {
  const [scriptId, setScriptId] = useState("all");
  const [level, setLevel] = useState("all");
  const [keyword, setKeyword] = useState("");
  const parentRef = useRef<HTMLDivElement | null>(null);

  const scriptsQuery = useQuery({
    queryKey: ["scripts", "logs-filter"],
    queryFn: async () => (await window.scriptConsole.listScripts({ sortBy: "name" })) as ScriptSummary[],
  });

  const logsQuery = useQuery({
    queryKey: ["logs", scriptId, level, keyword],
    queryFn: async () =>
      (await window.scriptConsole.searchLogs({
        scriptIds: scriptId === "all" ? undefined : [scriptId],
        levels: level === "all" ? undefined : [level as LogEvent["level"]],
        search: keyword || undefined,
        limit: 1200,
      })) as LogEvent[],
  });

  const logs = logsQuery.data ?? [];
  const byScript = useMemo(() => {
    const map = new Map<string, number>();
    for (const log of logs) {
      map.set(log.scriptId, (map.get(log.scriptId) ?? 0) + 1);
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [logs]);

  const byLevel = useMemo(() => {
    const map = new Map<string, number>();
    for (const log of logs) {
      map.set(log.level, (map.get(log.level) ?? 0) + 1);
    }
    return [...map.entries()];
  }, [logs]);

  const virtualizer = useVirtualizer({
    count: logs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 34,
    overscan: 10,
  });

  return (
    <div className="page-grid">
      <div className="stats-grid compact">
        <StatCard label="当前日志数" value={logs.length} helper="符合当前过滤条件" accent="brand" />
        <StatCard label="活跃脚本" value={byScript.length} helper="有日志输出的脚本" accent="ok" />
        <StatCard label="错误级别" value={byLevel.find(([name]) => name === "ERROR")?.[1] ?? 0} helper="ERROR 条数" accent="danger" />
      </div>

      <Card>
        <CardHeader
          title="日志聚合视图"
          subtitle="多脚本日志聚合、分级过滤、关键词搜索与导出"
          action={
            <div className="toolbar-actions">
              <Button
                variant="ghost"
                onClick={async () => {
                  const file = await window.scriptConsole.exportLogs({
                    scriptIds: scriptId === "all" ? undefined : [scriptId],
                    levels: level === "all" ? undefined : [level as LogEvent["level"]],
                    search: keyword || undefined,
                    limit: 1200,
                  });
                  toast.success(`日志已导出到 ${file}`);
                }}
              >
                <Download size={16} />
                导出
              </Button>
              <Button
                variant="danger"
                onClick={async () => {
                  await window.scriptConsole.clearLogIndex(scriptId === "all" ? undefined : scriptId);
                  toast.success("日志索引已清理");
                }}
              >
                <Eraser size={16} />
                清空
              </Button>
            </div>
          }
        />

        <div className="toolbar-row">
          <div className="search-with-icon">
            <Search size={16} />
            <input
              className="search-input"
              placeholder="搜索日志关键字"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
          </div>
          <select className="field-input" value={scriptId} onChange={(event) => setScriptId(event.target.value)}>
            <option value="all">全部脚本</option>
            {(scriptsQuery.data ?? []).map((item) => (
              <option key={item.record.id} value={item.record.id}>
                {item.record.manifest.name}
              </option>
            ))}
          </select>
          <select className="field-input" value={level} onChange={(event) => setLevel(event.target.value)}>
            <option value="all">全部级别</option>
            {["INFO", "WARN", "ERROR", "DEBUG", "FATAL", "UNKNOWN"].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        <div className="aggregates-grid">
          <Card className="nested-card">
            <CardHeader title="按脚本聚合" subtitle="最活跃日志来源" />
            <div className="history-list">
              {byScript.map(([name, count]) => (
                <div key={name} className="history-item">
                  <div className="history-title">{name}</div>
                  <div className="history-side">{count} 条</div>
                </div>
              ))}
            </div>
          </Card>
          <Card className="nested-card">
            <CardHeader title="按级别聚合" subtitle="错误波动一目了然" />
            <div className="history-list">
              {byLevel.map(([name, count]) => (
                <div key={name} className="history-item">
                  <div className="history-title">{name}</div>
                  <div className="history-side">{count} 条</div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {!logs.length ? (
          <EmptyState title="没有匹配日志" description="尝试调整关键字、级别或脚本过滤条件。" />
        ) : (
          <div ref={parentRef} className="log-viewport">
            <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const item = logs[virtualRow.index];
                return (
                  <div
                    key={item.id}
                    className={`virtual-log-row level-${item.level.toLowerCase()}`}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <span>{item.timestamp}</span>
                    <span>[{item.level}]</span>
                    <span className="log-script-pill">{item.scriptId}</span>
                    <span>{item.message}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
