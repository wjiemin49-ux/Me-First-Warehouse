from __future__ import annotations

from datetime import datetime, timedelta, timezone

from self_growth_daily_briefing.models import SourceItem
from self_growth_daily_briefing.rank import rank_clusters


def make_item(title: str, url: str, source_name: str, published_offset_hours: int, keyword_hits: list[str]) -> SourceItem:
    now = datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc)
    return SourceItem(
        source_name=source_name,
        source_type="rss",
        source_url=f"https://{source_name}.example/feed",
        title=title,
        summary=title,
        url=url,
        canonical_url=url,
        published_at=now - timedelta(hours=published_offset_hours),
        collected_at=now,
        keyword_hits=keyword_hits,
        keyword_score=0.72,
        trend_bonus=1.1,
        metadata={},
    )


def test_rank_clusters_deduplicates_similar_titles():
    items = [
        make_item(
            "Stop Measuring Your Worth by Productivity",
            "https://a.example/productivity-worth",
            "Tiny Buddha",
            2,
            ["burnout", "self-growth"],
        ),
        make_item(
            "Why We Measure Our Worth by Productivity",
            "https://b.example/worth-productivity",
            "Greater Good",
            3,
            ["burnout", "self-growth"],
        ),
        make_item(
            "Attention Residue Is Quietly Draining Your Growth",
            "https://c.example/attention-residue",
            "Ness Labs",
            1,
            ["focus", "discipline"],
        ),
    ]

    clusters = rank_clusters(items, now=datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc))

    assert len(clusters) == 2
    assert len(clusters[0].items) == 2
    assert set(clusters[0].source_names) == {"Greater Good", "Tiny Buddha"}
