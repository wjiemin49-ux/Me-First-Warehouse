#!/usr/bin/env python3
"""
Content Extractor - 检测平台并输出提取指引

设计原则：
- 不硬编码任何外部路径
- 不直接调用其他 skill 的脚本（由 Agent 在运行时通过 skill 调用）
- 只做：平台检测 + 输出推荐的 skill/tool 和提取方式
"""

import sys
import json
from urllib.parse import urlparse


PLATFORM_RULES = {
    "twitter": {
        "domains": ["x.com", "twitter.com", "mobile.twitter.com"],
        "label": "X/Twitter",
        "skill": "x-tweet-fetcher",
        "fallback_skills": [],
        "note": "使用 x-tweet-fetcher skill 提取推文/文章内容",
    },
    "weixin": {
        "domains": ["mp.weixin.qq.com"],
        "label": "微信公众号",
        "skill": "web-content-fetcher",
        "fallback_skills": ["defuddle"],
        "note": "使用 web-content-fetcher (Scrapling) 提取正文，完美绕过微信反爬",
        "scrapling_command": 'python3 ~/.openclaw/workspace/skills/web-content-fetcher/scripts/fetch.py "{url}" 50000',
        "selectors": {
            "title": "#activity-name, .rich_media_title",
            "author": "#js_name, .profile_nickname",
            "content": "#js_content, .rich_media_content",
            "publish_time": "#publish_time, em#publish_time",
        },
    },
    "jike": {
        "domains": ["okjike.com", "jike.cn", "m.okjike.com", "web.okjike.com"],
        "label": "即刻",
        "skill": "defuddle",
        "fallback_skills": ["baoyu-url-to-markdown"],
        "note": "即刻网页版可能需要登录，优先 defuddle，fallback 到 baoyu-url-to-markdown",
        "selectors": {
            "author": 'meta[property="og:title"], .user-name',
            "content": 'meta[property="og:description"], .content',
            "time": "time, .time",
        },
    },
    "reddit": {
        "domains": ["reddit.com", "www.reddit.com", "old.reddit.com"],
        "label": "Reddit",
        "skill": "defuddle",
        "fallback_skills": ["baoyu-url-to-markdown"],
        "note": "Reddit 支持 JSON API（URL 末尾加 .json），也可用 defuddle",
        "json_api": True,
    },
    "hackernews": {
        "domains": ["news.ycombinator.com"],
        "label": "Hacker News",
        "skill": "defuddle",
        "fallback_skills": [],
        "note": "HN 支持 Firebase API: https://hacker-news.firebaseio.com/v0/item/{id}.json",
    },
    "zhihu": {
        "domains": ["zhihu.com", "www.zhihu.com", "zhuanlan.zhihu.com"],
        "label": "知乎",
        "skill": "defuddle",
        "fallback_skills": ["baoyu-url-to-markdown"],
        "note": "知乎部分内容需要登录，使用 defuddle 或 baoyu-url-to-markdown",
    },
    "bilibili": {
        "domains": ["bilibili.com", "www.bilibili.com", "b23.tv"],
        "label": "Bilibili",
        "skill": "defuddle",
        "fallback_skills": ["baoyu-url-to-markdown"],
        "note": "视频类内容仅能提取标题和描述",
    },
}


def detect_platform(url: str) -> dict:
    """
    检测链接来源平台，返回平台信息和推荐的提取方式。
    """
    domain = urlparse(url).netloc.lower()
    bare_domain = domain.lstrip("www.")

    for platform_id, rule in PLATFORM_RULES.items():
        for d in rule["domains"]:
            if d in domain or d in bare_domain:
                return {
                    "platform_id": platform_id,
                    "platform_label": rule["label"],
                    "url": url,
                    "skill": rule["skill"],
                    "fallback_skills": rule.get("fallback_skills", []),
                    "note": rule["note"],
                    "selectors": rule.get("selectors"),
                    "json_api": rule.get("json_api", False),
                }

    return {
        "platform_id": "generic",
        "platform_label": "Web",
        "url": url,
        "skill": "defuddle",
        "fallback_skills": ["baoyu-url-to-markdown"],
        "note": "未知平台，使用 defuddle 通用提取，fallback 到 baoyu-url-to-markdown",
        "selectors": None,
        "json_api": False,
    }


def main():
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "error": "Usage: python3 extract_content.py [--url] <url>",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    if sys.argv[1] == "--url" and len(sys.argv) >= 3:
        url = sys.argv[2]
    else:
        url = sys.argv[1]

    result = detect_platform(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
