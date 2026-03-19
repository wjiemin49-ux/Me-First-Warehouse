# 脚本心跳 SDK 最小规范

## 目标

让脚本主动以极小成本向中控台表明“我还活着”。

## 最小文件

脚本应定期写入：

```text
runtime/heartbeat.json
```

## 最小结构

```json
{
  "timestamp": "2026-01-01T00:00:00Z",
  "status": "alive"
}
```

## 推荐扩展字段

- `pid`
- `port`
- `phase`
- `progress`
- `message`
- `iteration`

## 时间要求

- 推荐刷新间隔：15 秒
- 默认过期阈值：45 秒

## 退出前建议

如果脚本能优雅结束，建议在退出前写一次：

```json
{
  "timestamp": "2026-01-01T00:00:00Z",
  "status": "stopping"
}
```

## SDK 最小职责

SDK 只需要做一件事：

- 接收根目录
- 组装 `runtime/heartbeat.json`
- 写入当前 UTC 时间和状态

项目模板生成器已经为 Python / Node / PowerShell 模板附带最小 heartbeat SDK 示例。
