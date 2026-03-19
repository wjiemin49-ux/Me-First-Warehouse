import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { AppSettings, PluginDescriptor } from "@shared/types";
import { Button, Card, CardHeader } from "@renderer/components/ui/primitives";

export function SettingsPage() {
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => window.scriptConsole.getSettings(),
  });
  const pluginsQuery = useQuery({
    queryKey: ["plugins"],
    queryFn: () => window.scriptConsole.listPlugins(),
  });
  const [form, setForm] = useState<AppSettings | null>(null);

  useEffect(() => {
    if (settingsQuery.data) {
      setForm(settingsQuery.data);
    }
  }, [settingsQuery.data]);

  if (!form) {
    return <div className="loading-panel">设置载入中...</div>;
  }

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  };

  return (
    <div className="settings-layout">
      <Card>
        <CardHeader title="系统设置" subtitle="管理扫描、健康检查、主题、托盘与本地数据策略" />
        <div className="settings-grid">
          <label className="field">
            <span>脚本根目录</span>
            <input className="field-input" value={form.scriptRoot} onChange={(event) => update("scriptRoot", event.target.value)} />
          </label>
          <label className="field">
            <span>运行数据目录</span>
            <input className="field-input" value={form.dataDirectory} onChange={(event) => update("dataDirectory", event.target.value)} />
          </label>
          <label className="field">
            <span>扫描频率（秒）</span>
            <input className="field-input" type="number" value={form.scanIntervalSeconds} onChange={(event) => update("scanIntervalSeconds", Number(event.target.value))} />
          </label>
          <label className="field">
            <span>健康检查频率（秒）</span>
            <input className="field-input" type="number" value={form.healthIntervalSeconds} onChange={(event) => update("healthIntervalSeconds", Number(event.target.value))} />
          </label>
          <label className="field">
            <span>无响应超时（秒）</span>
            <input className="field-input" type="number" value={form.unresponsiveTimeoutSeconds} onChange={(event) => update("unresponsiveTimeoutSeconds", Number(event.target.value))} />
          </label>
          <label className="field">
            <span>日志保留天数</span>
            <input className="field-input" type="number" value={form.logRetentionDays} onChange={(event) => update("logRetentionDays", Number(event.target.value))} />
          </label>
          <label className="field">
            <span>自动重启策略</span>
            <select className="field-input" value={form.restartPolicy} onChange={(event) => update("restartPolicy", event.target.value as AppSettings["restartPolicy"])}>
              <option value="off">关闭</option>
              <option value="on-crash">异常退出后重启</option>
              <option value="on-crash-or-unresponsive">异常或无响应后重启</option>
            </select>
          </label>
          <label className="field">
            <span>最大重试次数</span>
            <input className="field-input" type="number" value={form.restartMaxRetries} onChange={(event) => update("restartMaxRetries", Number(event.target.value))} />
          </label>
          <label className="field">
            <span>熔断冷却（分钟）</span>
            <input className="field-input" type="number" value={form.restartCooldownMinutes} onChange={(event) => update("restartCooldownMinutes", Number(event.target.value))} />
          </label>
          <label className="field">
            <span>主题</span>
            <select className="field-input" value={form.theme} onChange={(event) => update("theme", event.target.value as AppSettings["theme"])}>
              <option value="system">跟随系统</option>
              <option value="dark">深色</option>
              <option value="light">浅色</option>
            </select>
          </label>
        </div>

        <div className="toggle-grid">
          <label className="toggle-card">
            <input type="checkbox" checked={form.autoScan} onChange={(event) => update("autoScan", event.target.checked)} />
            <div>
              <strong>自动扫描</strong>
              <span>监听工作区变化并自动刷新索引</span>
            </div>
          </label>
          <label className="toggle-card">
            <input type="checkbox" checked={form.trayEnabled} onChange={(event) => update("trayEnabled", event.target.checked)} />
            <div>
              <strong>系统托盘</strong>
              <span>允许最小化后继续后台运行</span>
            </div>
          </label>
          <label className="toggle-card">
            <input type="checkbox" checked={form.openAtLogin} onChange={(event) => update("openAtLogin", event.target.checked)} />
            <div>
              <strong>开机启动</strong>
              <span>随 Windows 登录自动启动中控台</span>
            </div>
          </label>
        </div>

        <div className="detail-actions">
          <Button
            onClick={async () => {
              await window.scriptConsole.saveSettings(form);
              toast.success("设置已保存");
            }}
          >
            保存设置
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader title="插件预留架构" subtitle="v1 暂不执行插件代码，但已预留发现与描述层" />
        <div className="settings-grid">
          <div className="metric-block">
            <span>插件工作目录</span>
            <strong>{form.scriptRoot}\\.script-console-plugins</strong>
          </div>
          <div className="metric-block">
            <span>已发现插件数</span>
            <strong>{pluginsQuery.data?.length ?? 0}</strong>
          </div>
        </div>
        <div className="history-list">
          {(pluginsQuery.data ?? []).map((plugin: PluginDescriptor) => (
            <div key={plugin.manifest.id} className="history-item">
              <div>
                <div className="history-title">{plugin.manifest.name}</div>
                <div className="history-meta">{plugin.manifest.hooks.join(", ")}</div>
              </div>
              <div className="history-side">{plugin.manifest.version}</div>
            </div>
          ))}
          {!pluginsQuery.data?.length ? (
            <div className="placeholder-copy">当前没有已注册插件；后续可在该目录下放置 plugin.manifest.json 扩展能力。</div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
