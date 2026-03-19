import { useEffect } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, FileClock, LayoutGrid, Logs, Settings, WandSparkles } from "lucide-react";
import { useLiveEvents } from "@renderer/hooks/use-live-events";
import { useUiStore } from "@renderer/store/ui-store";
import { DashboardPage } from "@renderer/pages/dashboard-page";
import { LogsPage } from "@renderer/pages/logs-page";
import { ScriptDetailPage } from "@renderer/pages/script-detail-page";
import { ScriptsPage } from "@renderer/pages/scripts-page";
import { SettingsPage } from "@renderer/pages/settings-page";
import { WizardPage } from "@renderer/pages/wizard-page";

const NAV_ITEMS = [
  { to: "/", label: "总览", icon: BarChart3 },
  { to: "/scripts", label: "脚本列表", icon: LayoutGrid },
  { to: "/logs", label: "日志中心", icon: Logs },
  { to: "/wizard", label: "接入向导", icon: WandSparkles },
  { to: "/settings", label: "设置", icon: Settings },
];

export default function App() {
  useLiveEvents();
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => window.scriptConsole.getSettings(),
  });
  const globalSearch = useUiStore((state) => state.globalSearch);
  const setGlobalSearch = useUiStore((state) => state.setGlobalSearch);

  useEffect(() => {
    const theme = settings?.theme ?? "dark";
    document.documentElement.dataset.theme = theme;
  }, [settings?.theme]);

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-panel">
          <div className="brand-mark">SC</div>
          <div>
            <div className="brand-title">Script Console</div>
            <div className="brand-subtitle">Offline Control Center</div>
          </div>
        </div>

        <nav className="nav-stack">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-chip">
            <FileClock size={14} />
            <span>{settings?.scriptRoot ?? "读取根目录中..."}</span>
          </div>
        </div>
      </aside>

      <main className="app-main">
        <header className="app-header">
          <div>
            <h1 className="page-title">本地离线脚本中控台</h1>
            <p className="page-subtitle">离线管理、统一监控、自动接入、实时反馈</p>
          </div>
          <div className="header-actions">
            <input
              className="search-input"
              placeholder="全局搜索脚本 / 分类 / 标签"
              value={globalSearch}
              onChange={(event) => setGlobalSearch(event.target.value)}
            />
          </div>
        </header>

        <section className="page-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/scripts" element={<ScriptsPage />} />
            <Route path="/scripts/:scriptId" element={<ScriptDetailPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/wizard" element={<WizardPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </section>
      </main>
    </div>
  );
}
