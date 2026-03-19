"""Feed 源配置"""

# 稳定的 RSS 源列表
FEED_SOURCES = [
    {
        "name": "Google DeepMind",
        "url": "https://deepmind.google/blog/feed/",
        "type": "rss",
        "enabled": True,
        "priority_boost": 2,
        "description": "Google DeepMind 官方博客"
    },
    {
        "name": "Google AI Research",
        "url": "https://research.google/blog/feed/",
        "type": "rss",
        "enabled": True,
        "priority_boost": 2,
        "description": "Google AI 研究博客"
    },
    {
        "name": "Microsoft Azure AI",
        "url": "https://azure.microsoft.com/en-us/blog/tag/ai/feed/",
        "type": "rss",
        "enabled": True,
        "priority_boost": 2,
        "description": "Microsoft Azure AI 博客"
    },
    {
        "name": "NVIDIA AI",
        "url": "https://blogs.nvidia.com/blog/category/generative-ai/feed/",
        "type": "rss",
        "enabled": True,
        "priority_boost": 2,
        "description": "NVIDIA 生成式 AI 博客"
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/tag/ai/feed/",
        "type": "rss",
        "enabled": True,
        "priority_boost": 1,
        "description": "TechCrunch AI 标签"
    },
    {
        "name": "VentureBeat",
        "url": "https://feeds.venturebeat.com/venturebeat/feed",
        "type": "rss",
        "enabled": True,
        "priority_boost": 1,
        "description": "VentureBeat 科技新闻"
    },
]


def get_enabled_sources() -> list[dict]:
    """获取启用的源"""
    return [s for s in FEED_SOURCES if s.get('enabled', True)]


def get_source_config_map() -> dict[str, dict]:
    """获取源配置映射"""
    return {s['name']: s for s in FEED_SOURCES}
