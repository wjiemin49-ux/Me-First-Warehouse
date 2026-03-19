# AI 新脚本接入协议

未来任何 AI 生成的新脚本，请优先遵循以下规则：

1. 每个脚本一个独立目录
2. 根目录生成 `manifest.json`
3. 建议同时生成 `script-console.manifest.json` 作为兼容别名
4. 日志输出到 `logs/`
5. 心跳输出到 `runtime/heartbeat.json`

## 最小目录

```text
<script-id>/
  manifest.json
  README.md
  logs/
  runtime/
  assets/
```

## 必填字段

- `id`
- `name`
- `version`
- `entry`
- `startCommand`
- `healthCheck`
- `logPath`
- `tags`
- `category`

## 说明

中控台现在同时兼容：

- `manifest.json`
- `script-console.manifest.json`

建议未来脚本使用 `manifest.json` 作为主文件。
