import { useState } from "react";
import { Link } from "react-router-dom";
import { getCoreRowModel, useReactTable, flexRender, createColumnHelper } from "@tanstack/react-table";
import { toast } from "react-hot-toast";
import { Play, RotateCcw, Square, Table2, LayoutGrid, ShieldAlert } from "lucide-react";
import { DisplayStatus, LifecycleState, ScriptSummary } from "@shared/types";
import { Button, Card, CardHeader, EmptyState, StatusBadge } from "@renderer/components/ui/primitives";
import { formatRelative, formatTime } from "@renderer/lib/format";
import { useUiStore } from "@renderer/store/ui-store";
import { useQuery } from "@tanstack/react-query";

const columnHelper = createColumnHelper<ScriptSummary>();

export function ScriptsPage() {
  const globalSearch = useUiStore((state) => state.globalSearch);
  const scriptsView = useUiStore((state) => state.scriptsView);
  const setScriptsView = useUiStore((state) => state.setScriptsView);
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState<DisplayStatus | LifecycleState | "all">("all");
  const [tag, setTag] = useState("all");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const scriptsQuery = useQuery({
    queryKey: ["scripts", globalSearch, category, status, tag, scriptsView],
    queryFn: async () =>
      (await window.scriptConsole.listScripts({
        search: globalSearch,
        category: category === "all" ? undefined : category,
        status: status === "all" ? "all" : status,
        tag: tag === "all" ? undefined : tag,
        sortBy: "recent",
      })) as ScriptSummary[],
  });

  const rows = scriptsQuery.data ?? [];
  const categories = ["all", ...new Set(rows.map((item) => item.record.smartCategory))];
  const tags = ["all", ...new Set(rows.flatMap((item) => item.record.smartTags))];

  const toggleSelection = (scriptId: string) => {
    setSelectedIds((current) =>
      current.includes(scriptId) ? current.filter((item) => item !== scriptId) : [...current, scriptId],
    );
  };

  const runBatchAction = async (action: "start" | "stop" | "restart") => {
    for (const scriptId of selectedIds) {
      if (action === "start") {
        await window.scriptConsole.startScript(scriptId);
      } else if (action === "stop") {
        await window.scriptConsole.stopScript(scriptId);
      } else {
        await window.scriptConsole.restartScript(scriptId);
      }
    }
    toast.success(`已执行批量${action === "start" ? "启动" : action === "stop" ? "停止" : "重启"}`);
  };

  const columns = [
    columnHelper.display({
      id: "select",
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selectedIds.includes(row.original.record.id)}
          onChange={() => toggleSelection(row.original.record.id)}
        />
      ),
    }),
    columnHelper.accessor((row) => row.record.manifest.name, {
      id: "name",
      header: "脚本",
      cell: ({ row, getValue }) => (
        <Link to={`/scripts/${row.original.record.id}`} className="table-link">
          <div>{getValue()}</div>
          <div className="table-subtle">{row.original.record.manifest.description}</div>
        </Link>
      ),
    }),
    columnHelper.accessor((row) => row.record.smartCategory, {
      id: "category",
      header: "智能分类",
      cell: (info) => info.getValue(),
    }),
    columnHelper.accessor((row) => row.runtime.displayStatus, {
      id: "status",
      header: "状态",
      cell: (info) => <StatusBadge status={info.getValue()} />,
    }),
    columnHelper.accessor((row) => row.runtime.circuitState, {
      id: "circuit",
      header: "熔断",
      cell: (info) =>
        info.getValue() === "open" ? (
          <span className="tag-chip circuit-open">
            <ShieldAlert size={14} />
            熔断中
          </span>
        ) : (
          "—"
        ),
    }),
    columnHelper.accessor((row) => row.runtime.lastStartedAt, {
      id: "lastStartedAt",
      header: "最近启动",
      cell: (info) => formatTime(info.getValue()),
    }),
  ];

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="page-grid">
      <Card>
        <CardHeader
          title="脚本列表"
          subtitle="按智能分类、标签、状态统一管理全部本地脚本"
          action={
            <div className="toolbar-actions">
              <Button variant={scriptsView === "cards" ? "primary" : "ghost"} onClick={() => setScriptsView("cards")}>
                <LayoutGrid size={16} />
                卡片
              </Button>
              <Button variant={scriptsView === "table" ? "primary" : "ghost"} onClick={() => setScriptsView("table")}>
                <Table2 size={16} />
                表格
              </Button>
            </div>
          }
        />

        <div className="toolbar-row">
          <select className="field-input" value={category} onChange={(event) => setCategory(event.target.value)}>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "全部分类" : item}
              </option>
            ))}
          </select>
          <select className="field-input" value={tag} onChange={(event) => setTag(event.target.value)}>
            {tags.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "全部标签" : item}
              </option>
            ))}
          </select>
          <select
            className="field-input"
            value={status}
            onChange={(event) => setStatus(event.target.value as DisplayStatus | LifecycleState | "all")}
          >
            <option value="all">全部状态</option>
            <option value="运行中">运行中</option>
            <option value="已停止">已停止</option>
            <option value="启动中">启动中</option>
            <option value="异常退出">异常退出</option>
            <option value="无响应">无响应</option>
            <option value="未配置">未配置</option>
          </select>
          <div className="toolbar-actions">
            <Button variant="ghost" onClick={() => void runBatchAction("start")} disabled={!selectedIds.length}>
              <Play size={16} />
              批量启动
            </Button>
            <Button variant="ghost" onClick={() => void runBatchAction("stop")} disabled={!selectedIds.length}>
              <Square size={16} />
              批量停止
            </Button>
            <Button variant="ghost" onClick={() => void runBatchAction("restart")} disabled={!selectedIds.length}>
              <RotateCcw size={16} />
              批量重启
            </Button>
          </div>
        </div>

        {!rows.length ? (
          <EmptyState title="暂无脚本结果" description="调整筛选条件或点击重新扫描以刷新索引。" />
        ) : scriptsView === "cards" ? (
          <div className="cards-grid">
            {rows.map((item) => (
              <Card key={item.record.id} className="script-card">
                <div className="script-card-top">
                  <div>
                    <div className="script-card-title">{item.record.manifest.name}</div>
                    <div className="script-card-description">{item.record.manifest.description}</div>
                  </div>
                  <StatusBadge status={item.runtime.displayStatus} />
                </div>
                <div className="script-meta-grid">
                  <div>
                    <span>智能分类</span>
                    <strong>{item.record.smartCategory}</strong>
                  </div>
                  <div>
                    <span>PID</span>
                    <strong>{item.runtime.pid ?? "—"}</strong>
                  </div>
                  <div>
                    <span>最近启动</span>
                    <strong>{formatRelative(item.runtime.lastStartedAt)}</strong>
                  </div>
                  <div>
                    <span>源模式</span>
                    <strong>{item.record.sourceMode}</strong>
                  </div>
                </div>
                <div className="tag-row">
                  {item.record.smartTags.map((itemTag) => (
                    <span key={itemTag} className="tag-chip">
                      {itemTag}
                    </span>
                  ))}
                  {item.runtime.circuitState === "open" ? (
                    <span className="tag-chip circuit-open">
                      <ShieldAlert size={14} />
                      熔断中
                    </span>
                  ) : null}
                </div>
                <div className="script-card-actions">
                  <Button variant="primary" onClick={() => void window.scriptConsole.startScript(item.record.id)}>
                    启动
                  </Button>
                  <Button variant="secondary" onClick={() => void window.scriptConsole.stopScript(item.record.id)}>
                    停止
                  </Button>
                  <Link to={`/scripts/${item.record.id}`} className="inline-link">
                    查看详情
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="table-shell">
            <table className="data-table">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id}>
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
