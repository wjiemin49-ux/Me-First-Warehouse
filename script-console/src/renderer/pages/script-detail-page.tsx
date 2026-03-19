import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { toast } from "react-hot-toast";
import { AlertTriangle, FolderOpen, Play, RotateCcw, ShieldAlert, Square, TerminalSquare } from "lucide-react";
import { ScriptDetail } from "@shared/types";
import { Button, Card, CardHeader, EmptyState, StatusBadge } from "@renderer/components/ui/primitives";
import { formatDuration, formatTime } from "@renderer/lib/format";

export function ScriptDetailPage() {
  const { scriptId = "" } = useParams();
  const detailQuery = useQuery({
    queryKey: ["script-detail", scriptId],
    queryFn: async () => (await window.scriptConsole.getScriptDetail(scriptId)) as ScriptDetail | undefined,
    enabled: Boolean(scriptId),
  });

  if (detailQuery.isLoading) {
    return <div className="loading-panel">脚本详情加载中...</div>;
  }

  if (!detailQuery.data) {
    return <EmptyState title="脚本不存在" description="该脚本可能已被移除或尚未完成索引。" />;
  }

  const detail = detailQuery.data;
  const { summary } = detail;

  return (
    <div className="detail-layout">
      <Card>
        <CardHeader
          title={summary.record.manifest.name}
          subtitle={summary.record.manifest.description}
          action={<StatusBadge status={summary.runtime.displayStatus} />}
        />

        <div className="detail-actions">
          <Button onClick={() => void window.scriptConsole.startScript(summary.record.id)}>
            <Play size={16} />
            启动
          </Button>
          <Button variant="secondary" onClick={() => void window.scriptConsole.stopScript(summary.record.id)}>
            <Square size={16} />
            停止
          </Button>
          <Button variant="ghost" onClick={() => void window.scriptConsole.restartScript(summary.record.id)}>
            <RotateCcw size={16} />
            重启
          </Button>
          <Button
            variant="danger"
            onClick={async () => {
              await window.scriptConsole.forceKillScript(summary.record.id);
              toast.success("已发起强制终止");
            }}
          >
            <AlertTriangle size={16} />
            强制终止
          </Button>
          <Button variant="ghost" onClick={() => void window.scriptConsole.openFolder(summary.record.id)}>
            <FolderOpen size={16} />
            打开目录
          </Button>
        </div>

        <div className="detail-grid">
          <div className="metric-block">
            <span>脚本 ID</span>
            <strong>{summary.record.id}</strong>
          </div>
          <div className="metric-block">
            <span>智能分类</span>
            <strong>{summary.record.smartCategory}</strong>
          </div>
          <div className="metric-block">
            <span>当前 PID</span>
            <strong>{summary.runtime.pid ?? "—"}</strong>
          </div>
          <div className="metric-block">
            <span>熔断状态</span>
            <strong>{summary.runtime.circuitState}</strong>
          </div>
          <div className="metric-block">
            <span>连续失败</span>
            <strong>{summary.runtime.consecutiveFailures}</strong>
          </div>
          <div className="metric-block">
            <span>计划重试</span>
            <strong>{formatTime(summary.runtime.nextRetryAt)}</strong>
          </div>
          <div className="metric-block">
            <span>最近启动</span>
            <strong>{formatTime(summary.runtime.lastStartedAt)}</strong>
          </div>
          <div className="metric-block">
            <span>最近停止</span>
            <strong>{formatTime(summary.runtime.lastStoppedAt)}</strong>
          </div>
          <div className="metric-block">
            <span>退出码</span>
            <strong>{summary.runtime.lastExitCode ?? "—"}</strong>
          </div>
          <div className="metric-block">
            <span>运行时长</span>
            <strong>{formatDuration(summary.runtime.resource.runtimeSeconds)}</strong>
          </div>
          <div className="metric-block">
            <span>最后健康状态</span>
            <strong>{summary.runtime.lastHealthSummary ?? "等待检查"}</strong>
          </div>
          <div className="metric-block">
            <span>熔断原因</span>
            <strong>{summary.runtime.circuitReason ?? "—"}</strong>
          </div>
        </div>
      </Card>

      <div className="detail-columns">
        <Card>
          <CardHeader title="运行配置" subtitle="启动、停止、健康检查与扩展能力" />
          <div className="config-stack">
            <div className="config-row">
              <span>启动命令</span>
              <code>
                {summary.record.manifest.entry.command} {summary.record.manifest.entry.args.join(" ")}
              </code>
            </div>
            <div className="config-row">
              <span>工作目录</span>
              <code>{summary.record.manifest.entry.cwd}</code>
            </div>
            <div className="config-row">
              <span>停止模式</span>
              <code>{summary.record.manifest.stop.mode}</code>
            </div>
            <div className="config-row">
              <span>日志文件</span>
              <code>{summary.record.manifest.logging.filePath ?? "由中控台托管输出"}</code>
            </div>
            <div className="config-row">
              <span>能力声明</span>
              <code>{summary.record.manifest.capabilities?.join(", ") || "—"}</code>
            </div>
          </div>
          <div className="tag-row">
            {summary.record.smartTags.map((tag) => (
              <span key={tag} className="tag-chip">
                {tag}
              </span>
            ))}
            {summary.runtime.circuitState === "open" ? (
              <span className="tag-chip circuit-open">
                <ShieldAlert size={14} />
                熔断中
              </span>
            ) : null}
          </div>
        </Card>

        <Card>
          <CardHeader title="资源信息" subtitle="采样来自本地进程和端口信息" />
          <div className="resource-grid">
            <div className="metric-block">
              <span>CPU</span>
              <strong>{summary.runtime.resource.cpuPercent ?? "—"}%</strong>
            </div>
            <div className="metric-block">
              <span>内存</span>
              <strong>{summary.runtime.resource.memoryMb ?? "—"} MB</strong>
            </div>
            <div className="metric-block">
              <span>线程数</span>
              <strong>{summary.runtime.resource.threadCount ?? "—"}</strong>
            </div>
            <div className="metric-block">
              <span>端口</span>
              <strong>{summary.runtime.resource.ports.join(", ") || "—"}</strong>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="故障时间线" subtitle="异常、重启、熔断、恢复的完整轨迹" />
          <div className="timeline-list">
            {detail.faultTimeline.map((item) => (
              <div key={item.id} className={`timeline-item severity-${item.severity}`}>
                <div className="timeline-rail">
                  <ShieldAlert size={16} />
                </div>
                <div className="timeline-content">
                  <div className="timeline-title">{item.title}</div>
                  <div className="timeline-meta">
                    {item.detail ?? "无附加说明"} · {formatTime(item.occurredAt)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="运行历史" subtitle="最近 80 条生命周期记录" />
          <div className="history-list">
            {detail.runs.map((item) => (
              <div key={item.id} className="history-item">
                <div>
                  <div className="history-title">
                    {item.action} · {item.outcome}
                  </div>
                  <div className="history-meta">{item.message ?? "无附加说明"}</div>
                </div>
                <div className="history-side">{formatTime(item.startedAt ?? item.endedAt)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="最近日志" subtitle="最近 250 条日志事件" action={<TerminalSquare size={18} />} />
          <div className="log-preview">
            {detail.logs.map((log) => (
              <div key={log.id} className={`log-line level-${log.level.toLowerCase()}`}>
                <span>{log.timestamp}</span>
                <span>[{log.level}]</span>
                <span>{log.message}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="健康检查记录" subtitle="探针最近执行结果" />
          <div className="history-list">
            {detail.healthChecks.map((item) => (
              <div key={item.id} className="history-item">
                <div>
                  <div className="history-title">
                    {item.probeType} · {item.status}
                  </div>
                  <div className="history-meta">{item.message ?? "无消息"}</div>
                </div>
                <div className="history-side">{formatTime(item.createdAt)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Manifest 预览" subtitle="当前索引中的标准协议内容" />
          <pre className="code-preview">{JSON.stringify(summary.record.manifest, null, 2)}</pre>
        </Card>
      </div>
    </div>
  );
}
