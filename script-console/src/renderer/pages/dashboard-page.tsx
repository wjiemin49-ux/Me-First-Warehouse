import { useQuery } from "@tanstack/react-query";
import { ArrowRight, RefreshCw, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { OverviewData, ScriptSummary } from "@shared/types";
import { StatusDistributionChart } from "@renderer/components/charts/status-distribution-chart";
import { Button, Card, CardHeader, EmptyState, StatCard, StatusBadge } from "@renderer/components/ui/primitives";
import { compactNumber, formatRelative, formatTime } from "@renderer/lib/format";

export function DashboardPage() {
  const overviewQuery = useQuery({
    queryKey: ["overview"],
    queryFn: async () => (await window.scriptConsole.getOverview()) as OverviewData,
  });

  if (overviewQuery.isLoading) {
    return <div className="loading-panel">仪表盘载入中...</div>;
  }

  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <EmptyState
        title="无法加载仪表盘"
        description="请检查主进程服务是否正常启动。"
        action={
          <Button onClick={() => void window.scriptConsole.rescanScripts()} variant="primary">
            手动重扫
          </Button>
        }
      />
    );
  }

  const { stats, statusDistribution, recentCrashes, recentEvents, recentScripts, faultTimeline } = overviewQuery.data;

  return (
    <div className="page-grid">
      <div className="stats-grid">
        <StatCard label="总脚本数" value={compactNumber(stats.totalScripts)} helper="当前已索引项目" accent="brand" />
        <StatCard label="运行中" value={compactNumber(stats.runningCount)} helper="正在执行中的脚本" accent="ok" />
        <StatCard label="已停止" value={compactNumber(stats.stoppedCount)} helper="当前处于停止状态" />
        <StatCard label="异常 / 无响应" value={compactNumber(stats.crashedCount + stats.unresponsiveCount)} helper="需要优先处理" accent="danger" />
        <StatCard label="今日启动次数" value={compactNumber(stats.todayStartCount)} helper="启动动作总量" accent="warn" />
        <StatCard label="今日异常次数" value={compactNumber(stats.todayCrashCount)} helper="故障记录" accent="danger" />
      </div>

      <div className="dashboard-layout">
        <Card>
          <CardHeader
            title="状态分布"
            subtitle="统一观察各脚本当前运行面貌"
            action={
              <Button variant="ghost" onClick={() => void window.scriptConsole.rescanScripts()}>
                <RefreshCw size={16} />
                重新扫描
              </Button>
            }
          />
          <StatusDistributionChart items={statusDistribution} />
        </Card>

        <Card>
          <CardHeader title="最近新增脚本" subtitle="首次运行时会自动播种 5 个示例项目" />
          <div className="list-stack">
            {recentScripts.map((item) => (
              <SummaryRow key={item.record.id} item={item} />
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="最近异常脚本" subtitle="优先排查失败与无响应项目" />
          {recentCrashes.length ? (
            <div className="list-stack">
              {recentCrashes.map((item) => (
                <SummaryRow key={item.record.id} item={item} />
              ))}
            </div>
          ) : (
            <div className="placeholder-copy">最近没有新的故障脚本。</div>
          )}
        </Card>

        <Card>
          <CardHeader title="日志事件流" subtitle="运行历史与用户动作总览" />
          <div className="event-feed">
            {recentEvents.map((event) => (
              <div key={event.id} className="event-item">
                <div className="event-dot" />
                <div>
                  <div className="event-title">
                    {event.scriptId} · {event.action} · {event.outcome}
                  </div>
                  <div className="event-meta">
                    {event.message ?? "无附加说明"} · {formatTime(event.startedAt ?? event.endedAt)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="span-two">
          <CardHeader title="故障时间线" subtitle="自动重启、熔断、恢复过程的连续视图" />
          <div className="timeline-list">
            {faultTimeline.map((item) => (
              <div key={item.id} className={`timeline-item severity-${item.severity}`}>
                <div className="timeline-rail">
                  <ShieldAlert size={16} />
                </div>
                <div className="timeline-content">
                  <div className="timeline-title">
                    {item.title} · {item.scriptId}
                  </div>
                  <div className="timeline-meta">
                    {item.detail ?? "无附加说明"} · {formatTime(item.occurredAt)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function SummaryRow({ item }: { item: ScriptSummary }) {
  return (
    <Link to={`/scripts/${item.record.id}`} className="summary-row">
      <div>
        <div className="summary-title">{item.record.manifest.name}</div>
        <div className="summary-meta">
          {item.record.smartCategory} · {item.record.smartTags.join(", ") || "无标签"}
        </div>
      </div>
      <div className="summary-side">
        <StatusBadge status={item.runtime.displayStatus} />
        <span className="summary-age">{formatRelative(item.record.indexedAt)}</span>
        <ArrowRight size={16} />
      </div>
    </Link>
  );
}
