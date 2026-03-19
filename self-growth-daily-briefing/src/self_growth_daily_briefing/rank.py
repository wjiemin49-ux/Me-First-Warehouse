from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher

from .models import SourceItem, TopicCluster, utc_now

STOPWORDS = {"the", "a", "an", "and", "or", "to", "for", "of", "on", "in", "how", "why", "what", "is"}


def _normalize_title(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    filtered = [word for word in words if word not in STOPWORDS]
    return " ".join(filtered)


def _title_similarity(left: str, right: str) -> float:
    left_norm = _normalize_title(left)
    right_norm = _normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_set = set(left_norm.split())
    right_set = set(right_norm.split())
    jaccard = len(left_set & right_set) / max(1, len(left_set | right_set))
    return max(ratio, jaccard)


def _should_join_cluster(item: SourceItem, cluster_items: list[SourceItem]) -> bool:
    for existing in cluster_items:
        if item.canonical_url == existing.canonical_url:
            return True
        if _title_similarity(item.title, existing.title) >= 0.84:
            return True
    return False


def cluster_items(items: list[SourceItem]) -> list[list[SourceItem]]:
    clusters: list[list[SourceItem]] = []
    for item in sorted(items, key=lambda candidate: candidate.published_at, reverse=True):
        for cluster in clusters:
            if _should_join_cluster(item, cluster):
                cluster.append(item)
                break
        else:
            clusters.append([item])
    return clusters


def _cluster_title(items: list[SourceItem]) -> str:
    counts = Counter(item.title for item in items)
    return max(items, key=lambda item: (counts[item.title], item.keyword_score, item.published_at)).title


def _score_cluster(items: list[SourceItem], now: datetime) -> tuple[float, float, float, float, float]:
    latest = max(item.published_at for item in items)
    age_hours = max(0.0, (now - latest).total_seconds() / 3600)
    recency_score = max(0.0, 1.0 - min(age_hours, 72.0) / 72.0)
    diversity_score = min(1.0, len({item.source_name for item in items}) / 3.0)
    keyword_score = min(1.0, sum(item.keyword_score for item in items) / max(1, len(items)))
    trend_score = min(1.0, sum(max(0.0, item.trend_bonus - 1.0) for item in items) / max(1, len(items)))
    total = round(100.0 * (0.38 * recency_score + 0.28 * diversity_score + 0.22 * keyword_score + 0.12 * trend_score), 4)
    return total, round(recency_score, 4), round(diversity_score, 4), round(keyword_score, 4), round(trend_score, 4)


def rank_clusters(items: list[SourceItem], now: datetime | None = None) -> list[TopicCluster]:
    reference_time = now.astimezone(timezone.utc) if now else utc_now()
    ranked: list[TopicCluster] = []
    for index, grouped_items in enumerate(cluster_items(items), start=1):
        total, recency_score, diversity_score, keyword_score, trend_score = _score_cluster(grouped_items, reference_time)
        representative_title = _cluster_title(grouped_items)
        ranked.append(
            TopicCluster(
                cluster_id=f"cluster-{index:02d}",
                representative_title=representative_title,
                items=sorted(grouped_items, key=lambda item: item.published_at, reverse=True),
                source_names=sorted({item.source_name for item in grouped_items}),
                score=total,
                recency_score=recency_score,
                diversity_score=diversity_score,
                keyword_score=keyword_score,
                trend_score=trend_score,
                score_breakdown={
                    "recency": recency_score,
                    "diversity": diversity_score,
                    "keyword": keyword_score,
                    "trend": trend_score,
                },
            )
        )
    ranked.sort(key=lambda cluster: (cluster.score, cluster.recency_score, len(cluster.source_names)), reverse=True)
    return ranked
