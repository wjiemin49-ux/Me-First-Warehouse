# 脚本接入协议规范

这份文档用于约束“未来任何 AI 生成的新脚本”如何自动被 Script Console 识别、索引、监控和管理。

## 1. 目录结构

推荐目录：

```text
<script-id>/
  script-console.manifest.json
  README.md
  logs/
  runtime/
  assets/
  sdk/
```

最低要求：

- 目录名建议与 `manifest.id` 一致
- 根目录必须有 `script-console.manifest.json`

## 2. Manifest 规则

必须字段：

- `id`
- `name`
- `description`
- `version`
- `author`
- `type`
- `entry`
- `stop`
- `logging`
- `health`
- `display`
- `policy`

重要约束：

- `entry.command` 只能是白名单解释器，或脚本目录内的绝对路径可执行文件
- `entry.args` 必须拆分成数组，不能把整条 shell 命令塞进一个字符串
- 默认 `shell = false`
- `display.tags` 用于列表过滤、智能搜索、批量分组
- `capabilities` 用于声明未来插件或 UI 增强可消费的能力
- `extensions` 预留给插件系统，不影响 v1 核心识别

## 3. 健康检查规则

至少包含一个 `process` 探针。

推荐组合：

- 长运行守护脚本：`process + heartbeat-file + log-update`
- 本地 HTTP 服务：`process + http + port + log-update`
- 短任务脚本：`process + log-update`

## 4. 日志约定

推荐日志格式：

```text
2026-01-01T00:00:00Z [INFO] message
```

建议：

- 日志输出到 `logs/app.log`
- 同时允许 stdout/stderr 被中控台采集
- 错误日志使用 `[ERROR]` 或 JSON 里的 `level=error`

## 5. 退出码约定

- `0`: 正常结束
- `2`: 配置错误
- `3`: 依赖缺失
- `4`: 启动失败
- `5`: 健康初始化失败
- `10+`: 业务 fatal

## 6. 自动接入行为

中控台会：

- 扫描脚本根目录一级子目录
- 优先读取 `script-console.manifest.json`
- manifest 变更时自动重载
- 删除目录时标记为 `missing`
- 新目录进入后自动建立索引

## 7. AI 生成脚本时的最低提示词建议

让任何 AI 生成新脚本时，补一句：

```text
请按 Script Console 接入协议输出，目录名等于脚本 id，根目录包含 script-console.manifest.json，日志写到 logs/app.log，心跳写到 runtime/heartbeat.json。
```
