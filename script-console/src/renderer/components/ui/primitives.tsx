import { PropsWithChildren, ReactNode } from "react";
import clsx from "clsx";
import { statusTone } from "@renderer/lib/format";

export function Card(props: PropsWithChildren<{ className?: string }>) {
  return <section className={clsx("panel-card", props.className)}>{props.children}</section>;
}

export function CardHeader(props: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="card-header">
      <div>
        <div className="card-title">{props.title}</div>
        {props.subtitle ? <div className="card-subtitle">{props.subtitle}</div> : null}
      </div>
      {props.action}
    </div>
  );
}

export function StatCard(props: { label: string; value: ReactNode; helper?: string; accent?: "ok" | "warn" | "danger" | "brand" }) {
  return (
    <Card className={clsx("stat-card", props.accent && `accent-${props.accent}`)}>
      <div className="stat-label">{props.label}</div>
      <div className="stat-value">{props.value}</div>
      {props.helper ? <div className="stat-helper">{props.helper}</div> : null}
    </Card>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={clsx("status-badge", `tone-${statusTone(status)}`)}>{status}</span>;
}

export function Button(
  props: PropsWithChildren<{
    onClick?: () => void;
    type?: "button" | "submit";
    variant?: "primary" | "secondary" | "ghost" | "danger";
    disabled?: boolean;
    className?: string;
  }>,
) {
  return (
    <button
      type={props.type ?? "button"}
      className={clsx("btn", props.variant ? `btn-${props.variant}` : "btn-primary", props.className)}
      onClick={props.onClick}
      disabled={props.disabled}
    >
      {props.children}
    </button>
  );
}

export function EmptyState(props: { title: string; description: string; action?: ReactNode }) {
  return (
    <Card className="empty-state">
      <div className="empty-title">{props.title}</div>
      <div className="empty-description">{props.description}</div>
      {props.action}
    </Card>
  );
}
