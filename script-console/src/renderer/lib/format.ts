export function formatTime(value?: string): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
  });
}

export function formatRelative(value?: string): string {
  if (!value) return "刚刚";
  const diff = Date.now() - Date.parse(value);
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s 前`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m 前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h 前`;
  const days = Math.floor(hours / 24);
  return `${days}d 前`;
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds && seconds !== 0) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${remaining}s`;
  return `${remaining}s`;
}

export function compactNumber(value?: number | null): string {
  if (!value && value !== 0) return "—";
  return new Intl.NumberFormat("zh-CN", { notation: "compact" }).format(value);
}

export function statusTone(status: string): "ok" | "warn" | "danger" | "idle" {
  if (status.includes("运行")) return "ok";
  if (status.includes("异常") || status.includes("无响应")) return "danger";
  if (status.includes("启动") || status.includes("停止")) return "warn";
  return "idle";
}
