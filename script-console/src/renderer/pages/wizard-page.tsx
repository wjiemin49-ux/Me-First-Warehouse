import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import { ScriptManifest, WizardDetectResult } from "@shared/types";
import { Button, Card, CardHeader } from "@renderer/components/ui/primitives";

const DEFAULT_MANIFEST = `{
  "id": "example-script",
  "name": "Example Script",
  "description": "Describe your script",
  "version": "0.1.0",
  "author": "unknown",
  "type": "python",
  "entry": {
    "command": "python",
    "args": ["main.py"],
    "cwd": ".",
    "shell": false
  },
  "stop": { "mode": "process", "timeoutMs": 10000 },
  "logging": { "filePath": "logs/app.log", "captureStdout": true, "captureStderr": true, "maxTailLines": 500 },
  "health": { "graceSeconds": 20, "probes": [{ "type": "process", "severity": "required" }] },
  "display": { "category": "Python 脚本", "tags": ["python"] },
  "policy": { "allowAutoStart": false, "allowVisible": true, "restartPolicy": "off" },
  "capabilities": ["heartbeat-file", "log-file"]
}`;

const HEARTBEAT_SPEC = `最小心跳 SDK 规范

1. 建议脚本每 15 秒写一次 runtime/heartbeat.json
2. 结构最少包含：
   {
     "timestamp": "2026-01-01T00:00:00Z",
     "status": "alive"
   }
3. 可扩展字段：
   pid, port, phase, progress, message
4. 当脚本退出前可写入 status = "stopping"
5. 中控台默认按最近修改时间与 timestamp 双重判断存活`;

export function WizardPage() {
  const [targetDirectory, setTargetDirectory] = useState("D:\\me\\脚本");
  const [scriptId, setScriptId] = useState("sample-script");
  const [scriptName, setScriptName] = useState("示例脚本");
  const [description, setDescription] = useState("这是一个通过接入向导创建的标准化脚本");
  const [author, setAuthor] = useState("Script Console");
  const [category, setCategory] = useState("未分类");
  const [tags, setTags] = useState("demo,template");
  const [templateType, setTemplateType] = useState<"python" | "node" | "bat" | "exe-wrapper">("python");
  const [existingPath, setExistingPath] = useState("");
  const [manifestText, setManifestText] = useState(DEFAULT_MANIFEST);
  const [detectResult, setDetectResult] = useState<WizardDetectResult | null>(null);
  const [schemaText, setSchemaText] = useState("{}");

  useEffect(() => {
    void window.scriptConsole.getManifestSchema().then((value) => {
      setSchemaText(JSON.stringify(value, null, 2));
    });
  }, []);

  const parseManifest = () => JSON.parse(manifestText) as ScriptManifest;
  const normalizedTags = useMemo(
    () =>
      tags
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    [tags],
  );

  return (
    <div className="wizard-layout">
      <Card>
        <CardHeader title="脚本创建向导" subtitle="在中控台内一键创建标准化脚本项目，并自动符合接入协议" />
        <div className="settings-grid">
          <label className="field">
            <span>模板类型</span>
            <select className="field-input" value={templateType} onChange={(event) => setTemplateType(event.target.value as typeof templateType)}>
              <option value="python">Python</option>
              <option value="node">Node</option>
              <option value="bat">bat / cmd</option>
              <option value="exe-wrapper">本地 exe 包装</option>
            </select>
          </label>
          <label className="field">
            <span>目标目录</span>
            <input className="field-input" value={targetDirectory} onChange={(event) => setTargetDirectory(event.target.value)} />
          </label>
          <label className="field">
            <span>脚本 ID</span>
            <input className="field-input" value={scriptId} onChange={(event) => setScriptId(event.target.value)} />
          </label>
          <label className="field">
            <span>脚本名称</span>
            <input className="field-input" value={scriptName} onChange={(event) => setScriptName(event.target.value)} />
          </label>
          <label className="field">
            <span>作者</span>
            <input className="field-input" value={author} onChange={(event) => setAuthor(event.target.value)} />
          </label>
          <label className="field">
            <span>智能分类</span>
            <input className="field-input" value={category} onChange={(event) => setCategory(event.target.value)} />
          </label>
          <label className="field span-two">
            <span>描述</span>
            <input className="field-input" value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label className="field span-two">
            <span>标签（逗号分隔）</span>
            <input className="field-input" value={tags} onChange={(event) => setTags(event.target.value)} />
          </label>
        </div>
        <div className="detail-actions">
          <Button
            onClick={async () => {
              const created = await window.scriptConsole.wizardGenerateTemplate({
                templateType,
                targetDirectory,
                scriptId,
                name: scriptName,
                description,
                author,
                category,
                tags: normalizedTags,
              });
              toast.success(`模板已生成: ${created}`);
            }}
          >
            一键生成标准化脚本
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader title="导入现有脚本" subtitle="兼容模式检测并可通过 junction 接入工作区" />
        <div className="settings-grid">
          <label className="field">
            <span>现有脚本目录</span>
            <input className="field-input" value={existingPath} onChange={(event) => setExistingPath(event.target.value)} />
          </label>
          <label className="field">
            <span>工作区根目录</span>
            <input className="field-input" value={targetDirectory} onChange={(event) => setTargetDirectory(event.target.value)} />
          </label>
        </div>
        <div className="detail-actions">
          <Button
            variant="secondary"
            onClick={async () => {
              const result = (await window.scriptConsole.wizardDetect(existingPath)) as WizardDetectResult;
              setDetectResult(result);
            }}
          >
            检测现有脚本
          </Button>
          <Button
            onClick={async () => {
              const junction = await window.scriptConsole.wizardImportExisting(existingPath, targetDirectory);
              toast.success(`已创建接入链接: ${junction}`);
            }}
          >
            导入到工作区
          </Button>
        </div>
        {detectResult ? <pre className="code-preview">{JSON.stringify(detectResult, null, 2)}</pre> : null}
      </Card>

      <Card>
        <CardHeader title="Manifest 校验与测试" subtitle="校验标准协议，测试启动命令与健康探针" />
        <textarea className="manifest-editor" value={manifestText} onChange={(event) => setManifestText(event.target.value)} />
        <div className="detail-actions">
          <Button
            variant="secondary"
            onClick={async () => {
              const result = await window.scriptConsole.wizardValidateManifest(manifestText, targetDirectory);
              toast.success("Manifest 校验已完成");
              setDetectResult(result as WizardDetectResult);
            }}
          >
            校验 Manifest
          </Button>
          <Button
            variant="ghost"
            onClick={async () => {
              const result = await window.scriptConsole.wizardTestLaunch(parseManifest(), targetDirectory);
              toast.success((result as { message: string }).message);
            }}
          >
            测试启动命令
          </Button>
          <Button
            variant="ghost"
            onClick={async () => {
              const result = await window.scriptConsole.wizardTestHealth(parseManifest(), targetDirectory);
              toast.success((result as { message: string }).message);
            }}
          >
            测试健康检查
          </Button>
        </div>
      </Card>

      <div className="detail-columns">
        <Card>
          <CardHeader title="Manifest JSON Schema" subtitle="可直接交给未来 AI 用于配置校验" />
          <pre className="code-preview">{schemaText}</pre>
        </Card>
        <Card>
          <CardHeader title="心跳 SDK 最小规范" subtitle="脚本主动上报存活状态时需遵循的最小约束" />
          <pre className="code-preview">{HEARTBEAT_SPEC}</pre>
        </Card>
      </div>
    </div>
  );
}
