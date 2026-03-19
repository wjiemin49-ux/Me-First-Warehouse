from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from .collect import collect_candidates
from .config import AppConfig, load_config
from .mail import load_smtp_config, send_issue, send_test_email
from .models import DailyIssue, SendResult, TopicCluster, TopicDecision
from .rank import rank_clusters
from .schedule import install_daily_task
from .storage import Storage
from .write import HeuristicLLMClient, OpenAICompatibleClient, create_issue


class BriefingApp:
    def __init__(
        self,
        config: AppConfig,
        storage: Storage | None = None,
        llm_client: OpenAICompatibleClient | HeuristicLLMClient | None = None,
    ) -> None:
        self.config = config
        self.storage = storage or Storage(config.state_db_path)
        self.llm_client = llm_client

    @classmethod
    def from_project_root(
        cls,
        project_root: str | None = None,
        llm_client: OpenAICompatibleClient | HeuristicLLMClient | None = None,
    ) -> "BriefingApp":
        return cls(config=load_config(project_root), llm_client=llm_client)

    def _default_llm_client(self) -> OpenAICompatibleClient:
        env = self.config.env
        return OpenAICompatibleClient(
            api_key=env.get("OPENAI_API_KEY"),
            base_url=env.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=env.get("OPENAI_MODEL", "gpt-4.1-mini"),
        )

    def list_sources(self) -> list[dict[str, object]]:
        return [
            {
                "name": feed.name,
                "kind": feed.kind,
                "url": feed.url,
                "tags": feed.tags,
                "trend_weight": feed.trend_weight,
            }
            for feed in self.config.feeds
        ]

    def _issue_date(self, now: datetime) -> str:
        local_time = now.astimezone(_resolve_timezone(self.config.settings.timezone))
        return local_time.date().isoformat()

    def _choose_topic(
        self,
        llm_client: OpenAICompatibleClient | HeuristicLLMClient,
        top_clusters: list[TopicCluster],
        now: datetime,
    ) -> TopicDecision:
        recent_themes = self.storage.recent_themes(self.config.settings.dedupe_days, now=now)
        decision = llm_client.choose_topic(top_clusters, recent_themes=recent_themes)
        if self.storage.was_theme_recent(decision.theme, self.config.settings.dedupe_days, now=now) and len(top_clusters) > 1:
            alternatives = [cluster for cluster in top_clusters if cluster.cluster_id != decision.selected_cluster_id]
            alternative_decision = llm_client.choose_topic(alternatives, recent_themes=recent_themes)
            if not self.storage.was_theme_recent(
                alternative_decision.theme,
                self.config.settings.dedupe_days,
                now=now,
            ):
                return alternative_decision
        return decision

    def build_issue(
        self,
        now: datetime | None = None,
        llm_client: OpenAICompatibleClient | HeuristicLLMClient | None = None,
    ) -> DailyIssue:
        reference_time = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
        collected = collect_candidates(self.config.feeds, self.config.settings, now=reference_time)
        self.storage.record_seen_items(collected.items)
        clusters = rank_clusters(collected.items, now=reference_time)
        if not clusters:
            raise RuntimeError("No ranked clusters were produced from the current source set")
        top_clusters = clusters[:5]
        writer = llm_client or self.llm_client or self._default_llm_client()
        decision = self._choose_topic(writer, top_clusters, reference_time)
        cluster_map = {cluster.cluster_id: cluster for cluster in top_clusters}
        selected_cluster = cluster_map[decision.selected_cluster_id]
        issue_date = self._issue_date(reference_time)
        article_payload = writer.write_article(
            decision=decision,
            cluster=selected_cluster,
            issue_date=issue_date,
            article_length=self.config.settings.article_length,
            language=self.config.settings.output_language,
        )
        issue = create_issue(issue_date=issue_date, decision=decision, cluster=selected_cluster, article_payload=article_payload)
        artifact_path = self.storage.write_run_artifact(
            self.config.runs_dir,
            issue_date,
            {
                "issue": issue.to_dict(),
                "decision": decision.to_dict(),
                "clusters": [cluster.to_dict() for cluster in top_clusters],
                "collection": {
                    "window_hours": collected.window_hours,
                    "errors": collected.errors,
                    "item_count": len(collected.items),
                },
            },
        )
        self.storage.record_theme(issue_date, issue.theme)
        self.storage.record_run(issue_date, status="generated", artifact_path=artifact_path)
        return issue

    def preview(
        self,
        now: datetime | None = None,
        llm_client: OpenAICompatibleClient | HeuristicLLMClient | None = None,
    ) -> DailyIssue:
        return self.build_issue(now=now, llm_client=llm_client)

    def run(
        self,
        send: bool = False,
        now: datetime | None = None,
        llm_client: OpenAICompatibleClient | HeuristicLLMClient | None = None,
    ) -> tuple[DailyIssue, SendResult | None]:
        issue = self.build_issue(now=now, llm_client=llm_client)
        send_result: SendResult | None = None
        if send:
            smtp_config = load_smtp_config(self.config.env)
            send_result = send_issue(issue, smtp_config, templates_dir=self.config.templates_dir)
            self.storage.record_send_result(issue.issue_date, send_result)
            run_status = "sent" if send_result.status == "sent" else "send_failed"
            self.storage.record_run(
                issue.issue_date,
                status=run_status,
                artifact_path=self.config.runs_dir / f"{issue.issue_date}.json",
                error=send_result.error,
            )
        return issue, send_result

    def send_test(self) -> SendResult:
        smtp_config = load_smtp_config(self.config.env)
        return send_test_email(smtp_config)

    def install_task(self, time_text: str | None = None) -> list[str]:
        return list(
            install_daily_task(
                project_root=self.config.project_root,
                time_text=time_text or self.config.settings.send_time,
                task_name=self.config.settings.task_name,
                python_executable=sys.executable,
            )
        )


def make_heuristic_app(project_root: str | None = None) -> BriefingApp:
    return BriefingApp.from_project_root(project_root=project_root, llm_client=HeuristicLLMClient())


def _resolve_timezone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        fallback_offsets = {
            "Asia/Shanghai": timezone(timedelta(hours=8), name="Asia/Shanghai"),
            "UTC": timezone.utc,
        }
        return fallback_offsets.get(name, timezone.utc)
