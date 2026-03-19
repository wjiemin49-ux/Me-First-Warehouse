from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from self_growth_daily_briefing.models import SourceItem
from self_growth_daily_briefing.rank import rank_clusters
from self_growth_daily_briefing.write import LLMResponseError, OpenAICompatibleClient, create_issue


def _make_cluster():
    items = [
        SourceItem(
            source_name="Tiny Buddha",
            source_type="rss",
            source_url="https://tinybuddha.com/feed/",
            title="Stop Measuring Your Worth by Productivity",
            summary="Burnout grows when self-worth depends on output.",
            url="https://tinybuddha.com/blog/stop-measuring-your-worth-by-productivity/",
            canonical_url="https://tinybuddha.com/blog/stop-measuring-your-worth-by-productivity",
            published_at=datetime(2026, 3, 12, 18, 30, tzinfo=timezone.utc),
            collected_at=datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc),
            keyword_hits=["burnout", "self-growth"],
            keyword_score=0.8,
            trend_bonus=1.0,
            metadata={},
        ),
        SourceItem(
            source_name="Greater Good",
            source_type="rss",
            source_url="https://greatergood.berkeley.edu/rss",
            title="Why We Measure Our Worth by Productivity",
            summary="Achievement becomes identity and raises burnout risk.",
            url="https://greatergood.berkeley.edu/article/item/why_we_measure_our_worth_by_productivity",
            canonical_url="https://greatergood.berkeley.edu/article/item/why_we_measure_our_worth_by_productivity",
            published_at=datetime(2026, 3, 12, 16, 30, tzinfo=timezone.utc),
            collected_at=datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc),
            keyword_hits=["burnout", "self-growth"],
            keyword_score=0.82,
            trend_bonus=1.0,
            metadata={},
        ),
    ]
    return rank_clusters(items, now=datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc))[0]


def test_openai_compatible_client_validates_json_contract():
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "theme": "把价值感从产出里松开",
                                "angle": "从 productivity guilt 切入",
                                "rationale": "这个主题兼具现实压力与成长价值。",
                                "selected_cluster_id": "cluster-01",
                                "supporting_urls": ["https://tinybuddha.com/blog/stop-measuring-your-worth-by-productivity"],
                                "supporting_titles": ["Stop Measuring Your Worth by Productivity"],
                                "keywords": ["burnout", "self-growth"],
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "把价值感从产出里松开",
                                "hook": "当你太久只用结果衡量自己，疲惫就会越来越像失败。",
                                "why_now": "这个主题之所以重要，是因为很多人的日常都被效率焦虑绑住了。",
                                "core_insight": "你需要的不是更严厉，而是更稳的自我支持系统。",
                                "reflections": ["先承认累，不等于放弃。", "小步也能重新恢复掌控感。"],
                                "action_prompts": ["暂停 10 分钟整理感受。", "只做一个低阻力动作。", "晚上记录今天的恢复瞬间。"],
                                "closing": "愿你把成长重新放回真实生活里。",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        },
    ]

    def transport(payload):
        return responses.pop(0)

    client = OpenAICompatibleClient(api_key="test", base_url="https://example.invalid/v1", model="test-model", transport=transport)
    cluster = _make_cluster()
    decision = client.choose_topic([cluster])
    article = client.write_article(decision, cluster, issue_date="2026-03-13", article_length="1200-1800", language="zh-CN")
    issue = create_issue("2026-03-13", decision, cluster, article)

    assert decision.theme == "把价值感从产出里松开"
    assert issue.subject.startswith("【成长晨读】2026-03-13")
    assert len(issue.action_prompts) == 3


def test_openai_compatible_client_raises_on_invalid_article_shape():
    responses = [
        {"choices": [{"message": {"content": '{"theme":"x","angle":"y","rationale":"z","selected_cluster_id":"cluster-01","supporting_urls":[],"supporting_titles":[],"keywords":[]}'}}]},
        {"choices": [{"message": {"content": '{"title":"x","hook":"h","why_now":"w","core_insight":"c","reflections":["only one"],"action_prompts":["one"],"closing":"bye"}'}}]},
    ]

    client = OpenAICompatibleClient(
        api_key="test",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=lambda payload: responses.pop(0),
    )
    cluster = _make_cluster()
    decision = client.choose_topic([cluster])
    with pytest.raises(LLMResponseError):
        client.write_article(decision, cluster, issue_date="2026-03-13", article_length="1200-1800", language="zh-CN")


def test_openai_compatible_client_flattens_structured_reflections_and_actions():
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": '{"theme":"幸福感优先","angle":"从储备感切入","rationale":"避免空耗","selected_cluster_id":"cluster-01","supporting_urls":[],"supporting_titles":[],"keywords":["burnout"]}'
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "幸福感优先",
                                "hook": "先照顾自己，不等于放纵。",
                                "why_now": "很多人的计划失败，本质是储备不足。",
                                "core_insight": "先补足身心电量，再谈持续行动。",
                                "reflections": [
                                    {
                                        "prompt": "回想一次最近的失速",
                                        "points": ["你缺的是睡眠还是情绪空间", "换个名字看问题会更温和"],
                                    },
                                    {
                                        "prompt": "休息是不是总被你推迟",
                                        "points": ["你是否只在完成任务后才允许自己停下", "微恢复也算行动的一部分"],
                                    },
                                ],
                                "action_prompts": [
                                    {
                                        "title": "每日四格检查",
                                        "steps": ["先看睡眠", "再看情绪", "最后安排一个微休息"],
                                        "output": "只补最缺的一格",
                                    },
                                    {
                                        "title": "把目标改成稳态版本",
                                        "steps": ["把标准降到能连续做两周", "只保留不断线的最小动作"],
                                    },
                                    {
                                        "title": "晚间恢复性收尾",
                                        "steps": ["睡前十分钟不做决策", "写下明天最先照顾自己的一步"],
                                    },
                                ],
                                "closing": "照顾好自己，目标才走得远。",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        },
    ]

    client = OpenAICompatibleClient(
        api_key="test",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=lambda payload: responses.pop(0),
    )
    cluster = _make_cluster()
    decision = client.choose_topic([cluster])
    article = client.write_article(decision, cluster, issue_date="2026-03-13", article_length="1200-1800", language="zh-CN")
    issue = create_issue("2026-03-13", decision, cluster, article)

    assert all(isinstance(item, str) for item in article["reflections"])
    assert all(isinstance(item, str) for item in article["action_prompts"])
    assert "{'" not in issue.article_markdown
    assert "要点：" in issue.article_markdown
    assert "步骤：" in issue.article_markdown
