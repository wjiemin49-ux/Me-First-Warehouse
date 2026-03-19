from __future__ import annotations

from email import policy
from email.parser import BytesParser

import pytest

from self_growth_daily_briefing.mail import MailConfigurationError, SmtpConfig, load_smtp_config, render_email_bodies, send_issue
from self_growth_daily_briefing.models import ArticleSource, DailyIssue
from tests.helpers import DummySMTPServer


def sample_issue() -> DailyIssue:
    return DailyIssue(
        issue_date="2026-03-13",
        subject="【成长晨读】2026-03-13｜把今天的成长放回日常里",
        theme="把今天的成长放回日常里",
        title="把今天的成长放回日常里",
        angle="从焦虑和节奏感之间，找到更稳定的行动方式。",
        hook="当我们太急着变好时，反而更容易失去和自己的连接。",
        why_now="因为很多人的成长目标，已经在不知不觉中变成了新的压力来源。",
        core_insight="可持续的成长，更像照顾系统，而不是压榨意志力。",
        reflections=["允许停一下，未必就是退步。", "先恢复掌控感，再谈更大的突破。"],
        action_prompts=["今天只做一个最小动作。", "给自己留 20 分钟完整注意力。", "晚上记下一个恢复瞬间。"],
        closing="愿你今天的行动，比昨天更温柔，也更稳。",
        article_markdown="# sample",
        source_links=[
            ArticleSource(
                title="Stop Measuring Your Worth by Productivity",
                url="https://tinybuddha.com/blog/stop-measuring-your-worth-by-productivity",
                source_name="Tiny Buddha",
            ),
            ArticleSource(
                title="Why We Measure Our Worth by Productivity",
                url="https://greatergood.berkeley.edu/article/item/why_we_measure_our_worth_by_productivity",
                source_name="Greater Good",
            ),
        ],
        selected_cluster_id="cluster-01",
        metadata={},
    )


def test_load_smtp_config_requires_expected_fields():
    with pytest.raises(MailConfigurationError):
        load_smtp_config({"SMTP_HOST": "smtp.example.com"})


def test_render_email_bodies_includes_sources(project_root):
    html_body, text_body = render_email_bodies(sample_issue(), project_root / "templates")
    assert "把今天的成长放回日常里" in html_body
    assert "Tiny Buddha" in text_body


def test_send_issue_retries_once_before_success(project_root):
    attempts = {"count": 0}

    class FlakySMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary failure")

    smtp_config = SmtpConfig(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        email_from="briefing@example.com",
        email_to="reader@example.com",
    )
    result = send_issue(
        sample_issue(),
        smtp_config,
        templates_dir=project_root / "templates",
        smtp_factory=FlakySMTP,
        sleep_func=lambda seconds: None,
    )
    assert result.status == "sent"
    assert result.attempts == 2


def test_send_issue_works_with_local_dummy_server(project_root):
    with DummySMTPServer() as server:
        smtp_config = SmtpConfig(
            host=server.host,
            port=server.port,
            username="user",
            password="pass",
            email_from="briefing@example.com",
            email_to="reader@example.com",
        )
        result = send_issue(sample_issue(), smtp_config, templates_dir=project_root / "templates")

    assert result.status == "sent"
    assert len(server.messages) == 1
    parsed = BytesParser(policy=policy.default).parsebytes(server.messages[0].data)
    assert parsed["Subject"] == "【成长晨读】2026-03-13｜把今天的成长放回日常里"
    assert "reader@example.com" in server.messages[0].rcpt_to[0]
