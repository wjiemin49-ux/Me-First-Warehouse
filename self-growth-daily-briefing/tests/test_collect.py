from __future__ import annotations

from pathlib import Path

from self_growth_daily_briefing.collect import collect_candidates, parse_rss_content
from self_growth_daily_briefing.config import FeedDefinition, Settings

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_rss_content_extracts_relevant_items(fixed_now):
    definition = FeedDefinition(
        name="Tiny Buddha",
        kind="rss",
        url="https://tinybuddha.com/feed/",
        tags=["self-growth", "mindfulness", "resilience"],
        trend_weight=1.0,
    )
    items = parse_rss_content(fixture_text("tiny_buddha.xml"), definition, fixed_now)
    assert len(items) == 2
    assert items[0].title == "Stop Measuring Your Worth by Productivity"
    assert items[0].canonical_url == "https://tinybuddha.com/blog/stop-measuring-your-worth-by-productivity"
    assert "burnout" in items[0].keyword_hits


def test_collect_candidates_falls_back_to_72_hours_when_needed(fixed_now):
    feeds = [
        FeedDefinition(
            name="Tiny Buddha",
            kind="rss",
            url="https://tinybuddha.com/feed/",
            tags=["self-growth", "mindfulness", "resilience"],
            trend_weight=1.0,
        ),
        FeedDefinition(
            name="Older Window Feed",
            kind="rss",
            url="https://example.com/older.xml",
            tags=["habits", "purpose", "burnout"],
            trend_weight=1.0,
        ),
    ]
    mapping = {
        "https://tinybuddha.com/feed/": fixture_text("tiny_buddha.xml"),
        "https://example.com/older.xml": fixture_text("older_window.xml"),
    }
    settings = Settings(
        timezone="Asia/Shanghai",
        send_time="09:00",
        output_language="zh-CN",
        article_length="1200-1800",
        max_candidates=10,
        fallback_window_hours=72,
        dedupe_days=7,
        collection_window_hours=48,
        minimum_candidate_count=3,
    )

    result = collect_candidates(feeds, settings, now=fixed_now, fetcher=lambda url: mapping[url])

    assert result.window_hours == 72
    assert len(result.items) >= 3
