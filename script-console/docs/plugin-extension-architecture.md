# 插件系统预留架构

v1 不执行第三方插件代码，但已经为未来插件化扩展预留了发现层和协议层。

## 插件目录

```text
<script-root>/.script-console-plugins/
  <plugin-id>/
    plugin.manifest.json
```

## 插件 Manifest 最小结构

```json
{
  "id": "example-plugin",
  "name": "Example Plugin",
  "version": "0.1.0",
  "author": "unknown",
  "apiVersion": 1,
  "hooks": ["register-probes", "classify-scripts"]
}
```

## 预留 Hook

- `register-probes`
- `classify-scripts`
- `augment-dashboard`
- `add-actions`

## 当前已实现

- 插件目录扫描
- `plugin.manifest.json` 发现
- 设置页展示已发现插件

## 未来演进建议

- 隔离插件运行时
- 为插件提供只读脚本索引 API
- 为插件提供受限动作 API
- 为插件 hook 增加版本协商与权限声明
