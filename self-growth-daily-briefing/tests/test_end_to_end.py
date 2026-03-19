from __future__ import annotations

from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser

import yaml

from self_growth_daily_briefing.app import BriefingApp
from self_growth_daily_briefing.mail import SmtpConfig, send_issue
from self_growth_daily_briefing.models import TopicDecision
from self_growth_daily_briefing.write import HeuristicLLMClient
from tests.helpers import DummySMTPServer


FIXTURE_MAP = {
    "https://tinybuddha.com/feed/": "tiny_buddha.xml",
    "https://nesslabs.com/feed": "ness_labs.xml",
    "https://greatergood.berkeley.edu/rss": "greater_good.xml",
    "https://www.reddit.com/r/selfimprovement/top.json?limit=20&t=day": "reddit_selfimprovement.json",
    "https://www.reddit.com/r/getdisciplined/top.json?limit=20&t=day": "reddit_getdisciplined.json",
}


def _fixture_loader(name: str, request) -> str:
    return (request.config.rootpath / "tests" / "fixtures" / name).read_text(encoding="utf-8")


def test_end_to_end_generates_daily_issue_from_fixtures(project_root, fixed_now, monkeypatch, request):
    def fake_fetch(url: str) -> str:
        if url in FIXTURE_MAP:
            return _fixture_loader(FIXTURE_MAP[url], request)
        raise RuntimeError(f"unmapped feed: {url}")

    monkeypatch.setattr("self_growth_daily_briefing.collect.fetch_url", fake_fetch)
    app = BriefingApp.from_project_root(str(project_root), llm_client=HeuristicLLMClient())

    issue = app.preview(now=fixed_now)

    assert issue.theme
    assert len(issue.source_links) >= 2
    assert (project_root / "runs" / f"{issue.issue_date}.json").exists()


def test_end_to_end_uses_72_hour_fallback_when_news_is_thin(project_root, monkeypatch, request):
    with (project_root / "config" / "feeds.yaml").open("r", encoding="utf-8") as handle:
        config_payload = yaml.safe_load(handle)
    config_payload["feeds"] = [
        {
            "name": "Tiny Buddha",
            "kind": "rss",
            "url": "https://tinybuddha.com/feed/",
            "tags": ["self-growth", "mindfulness", "resilience"],
            "trend_weight": 1.0,
        },
        {
            "name": "Greater Good",
            "kind": "rss",
            "url": "https://greatergood.berkeley.edu/rss",
            "tags": ["well-being", "relationships", "resilience"],
            "trend_weight": 1.0,
        },
    ]
    (project_root / "config" / "feeds.yaml").write_text(yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8")

    def fake_fetch(url: str) -> str:
        if url == "https://tinybuddha.com/feed/":
            return _fixture_loader("tiny_buddha.xml", request)
        if url == "https://greatergood.berkeley.edu/rss":
            return _fixture_loader("greater_good.xml", request)
        raise RuntimeError(url)

    monkeypatch.setattr("self_growth_daily_briefing.collect.fetch_url", fake_fetch)
    app = BriefingApp.from_project_root(str(project_root), llm_client=HeuristicLLMClient())
    issue = app.preview(now=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc))
    artifact = yaml.safe_load((project_root / "runs" / f"{issue.issue_date}.json").read_text(encoding="utf-8"))

    assert artifact["collection"]["window_hours"] == 72


def test_end_to_end_partial_source_failure_still_sends_email(project_root, fixed_now, monkeypatch, request):
    def fake_fetch(url: str) -> str:
        if url in FIXTURE_MAP:
            return _fixture_loader(FIXTURE_MAP[url], request)
        raise RuntimeError("temporary source failure")

    monkeypatch.setattr("self_growth_daily_briefing.collect.fetch_url", fake_fetch)
    app = BriefingApp.from_project_root(str(project_root), llm_client=HeuristicLLMClient())
    issue = app.preview(now=fixed_now)

    with DummySMTPServer() as server:
        smtp_config = SmtpConfig(
            host=server.host,
            port=server.port,
            username="user",
            password="pass",
            email_from="briefing@example.com",
            email_to="reader@example.com",
        )
        result = send_issue(issue, smtp_config, templates_dir=project_root / "templates")

    assert result.status == "sent"
    parsed = BytesParser(policy=policy.default).parsebytes(server.messages[0].data)
    assert parsed["Subject"] == issue.subject
    artifact_text = (project_root / "runs" / f"{issue.issue_date}.json").read_text(encoding="utf-8")
    assert "temporary source failure" in artifact_text


class RepeatThenDifferentLLM:
    def __init__(self) -> None:
        self.choose_calls = 0

    def choose_topic(self, clusters, recent_themes=None):
        self.choose_calls += 1
        if self.choose_calls == 1:
            selected = clusters[0]
            return TopicDecision(
                theme="重复主题",
                angle="重复角度",
                rationale="第一次故意重复",
                selected_cluster_id=selected.cluster_id,
                supporting_urls=[item.canonical_url for item in selected.items[:2]],
                supporting_titles=[item.title for item in selected.items[:2]],
                keywords=["burnout"],
            )
        selected = clusters[0]
        return TopicDecision(
            theme="替代主题",
            angle="备用角度",
            rationale="第二次换一个",
            selected_cluster_id=selected.cluster_id,
            supporting_urls=[item.canonical_url for item in selected.items[:2]],
            supporting_titles=[item.title for item in selected.items[:2]],
            keywords=["focus"],
        )

    def write_article(self, decision, cluster, issue_date, article_length, language):
        return HeuristicLLMClient().write_article(decision, cluster, issue_date, article_length, language)


def test_end_to_end_avoids_duplicate_theme_when_alternative_exists(project_root, fixed_now, monkeypatch, request):
    def fake_fetch(url: str) -> str:
        if url in FIXTURE_MAP:
            return _fixture_loader(FIXTURE_MAP[url], request)
        raise RuntimeError(f"unmapped feed: {url}")

    monkeypatch.setattr("self_growth_daily_briefing.collect.fetch_url", fake_fetch)
    app = BriefingApp.from_project_root(str(project_root), llm_client=RepeatThenDifferentLLM())
    app.storage.record_theme("2026-03-12", "重复主题")

    issue = app.preview(now=fixed_now)

    assert issue.theme == "替代主题"
