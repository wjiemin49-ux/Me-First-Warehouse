# Script Console

Windows 本地离线脚本中控台。双击 EXE 后即可打开，用于统一发现、索引、启动、停止、监控和查看本地脚本。

## 技术栈

- Electron 41
- React 19 + TypeScript + Vite
- Node.js 主进程服务
- `node:sqlite` 本地 SQLite 数据库

## 快速开始

```powershell
npm install
npm run dev
```

## 构建

```powershell
npm run package
```

目录打包产物默认输出到：

`C:\Users\MACHENIKE\AppData\Local\ScriptConsoleBuild\win-unpacked`

其中可直接运行：

- `Script Console.exe`

## 附加文档

- `docs/script-onboarding-protocol.md`
- `docs/heartbeat-sdk-min-spec.md`
- `docs/plugin-extension-architecture.md`
- `docs/sample-projects.md`
- `schemas/script-console.manifest.schema.json`

## 首次运行

应用首次启动会自动在默认脚本根目录下播种 5 个示例项目，方便立即看到状态管理、日志聚合、健康检查、自动重启与熔断效果。

## 目录

```text
script-console/
  docs/
  src/
    main/
    renderer/
    shared/
  dist/
  dist-electron/
```
