from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _deserialize_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass(slots=True)
class ArticleSource:
    title: str
    url: str
    source_name: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceItem:
    source_name: str
    source_type: str
    source_url: str
    title: str
    summary: str
    url: str
    canonical_url: str
    published_at: datetime
    collected_at: datetime
    keyword_hits: list[str] = field(default_factory=list)
    keyword_score: float = 0.0
    trend_bonus: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["published_at"] = _serialize_datetime(self.published_at)
        payload["collected_at"] = _serialize_datetime(self.collected_at)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceItem":
        return cls(
            source_name=payload["source_name"],
            source_type=payload["source_type"],
            source_url=payload["source_url"],
            title=payload["title"],
            summary=payload["summary"],
            url=payload["url"],
            canonical_url=payload["canonical_url"],
            published_at=_deserialize_datetime(payload["published_at"]) or utc_now(),
            collected_at=_deserialize_datetime(payload["collected_at"]) or utc_now(),
            keyword_hits=list(payload.get("keyword_hits", [])),
            keyword_score=float(payload.get("keyword_score", 0.0)),
            trend_bonus=float(payload.get("trend_bonus", 1.0)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class TopicCluster:
    cluster_id: str
    representative_title: str
    items: list[SourceItem]
    source_names: list[str]
    score: float
    recency_score: float
    diversity_score: float
    keyword_score: float
    trend_score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "representative_title": self.representative_title,
            "items": [item.to_dict() for item in self.items],
            "source_names": self.source_names,
            "score": self.score,
            "recency_score": self.recency_score,
            "diversity_score": self.diversity_score,
            "keyword_score": self.keyword_score,
            "trend_score": self.trend_score,
            "score_breakdown": self.score_breakdown,
        }


@dataclass(slots=True)
class TopicDecision:
    theme: str
    angle: str
    rationale: str
    selected_cluster_id: str
    supporting_urls: list[str]
    supporting_titles: list[str]
    keywords: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DailyIssue:
    issue_date: str
    subject: str
    theme: str
    title: str
    angle: str
    hook: str
    why_now: str
    core_insight: str
    reflections: list[str]
    action_prompts: list[str]
    closing: str
    article_markdown: str
    source_links: list[ArticleSource]
    selected_cluster_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_links"] = [source.to_dict() for source in self.source_links]
        return payload


@dataclass(slots=True)
class SendResult:
    status: str
    attempts: int
    recipient: str
    subject: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
