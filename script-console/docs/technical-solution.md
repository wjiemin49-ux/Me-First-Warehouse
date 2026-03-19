# Script Console 技术方案

## 技术栈

- Electron + React + TypeScript
- Node 主进程服务
- `node:sqlite` 本地数据库
- chokidar 文件监听

## 核心模块

- `SettingsService`: 管理本地配置
- `IndexService`: 工作区扫描、索引、历史记录
- `ProcessSupervisor`: 启停、重启、强杀、重试退避
- `HealthMonitor`: 进程、heartbeat、HTTP、端口、日志更新时间探针
- `LogService`: stdout/stderr 捕获、日志索引、导出
- `WorkspaceWatcher`: 根目录变化监听

## 数据持久化

- `scripts`: 脚本元数据与 manifest
- `script_runtime`: 运行时快照
- `run_history`: 生命周期历史
- `health_checks`: 健康检查记录
- `log_events` + `log_index`: 日志事件与全文检索

## 打包

- `electron-builder`
- Windows 产物：`nsis` + `portable`
