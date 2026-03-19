#!/usr/bin/env python3
"""
Deduplication - 检查链接是否已存在
支持：飞书多维表格检查、本地缓存检查
"""

import json
import re
import os
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

DOMAIN_ALIASES = {
    "twitter.com": "x.com",
    "www.twitter.com": "x.com",
    "mobile.twitter.com": "x.com",
    "www.x.com": "x.com",
    "m.okjike.com": "okjike.com",
    "web.okjike.com": "okjike.com",
    "www.okjike.com": "okjike.com",
    "old.reddit.com": "reddit.com",
    "www.reddit.com": "reddit.com",
    "np.reddit.com": "reddit.com",
    "i.reddit.com": "reddit.com",
    "amp.reddit.com": "reddit.com",
    "www.weixin.qq.com": "mp.weixin.qq.com",
}

SHORT_URL_DOMAINS = {"t.co", "bit.ly", "tinyurl.com", "goo.gl", "ow.ly", "is.gd", "buff.ly"}

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", ".cache", "collected_urls.json")

BITABLE_APP_TOKEN = os.environ.get("FEISHU_BITABLE_APP_TOKEN") or os.environ.get("BITABLE_APP_TOKEN", "")
BITABLE_TABLE_ID = os.environ.get("FEISHU_BITABLE_TABLE_ID") or os.environ.get("BITABLE_TABLE_ID", "")

CACHE_TTL_DAYS = 30
CACHE_MAX_ENTRIES = 1000


def ensure_cache_dir():
    """确保缓存目录存在"""
    cache_dir = os.path.dirname(CACHE_FILE)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)


def load_cache():
    """加载已收藏的 URL 缓存"""
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        return _cleanup_cache(cache)
    return {}


def _cleanup_cache(cache: dict) -> dict:
    now = datetime.now()
    cutoff = now - timedelta(days=CACHE_TTL_DAYS)

    active = {}
    for url, entry in cache.items():
        entry_date = entry.get("date", "")
        try:
            dt = datetime.fromisoformat(entry_date)
            if dt >= cutoff:
                active[url] = entry
        except (ValueError, TypeError):
            active[url] = entry

    if len(active) > CACHE_MAX_ENTRIES:
        sorted_entries = sorted(active.items(), key=lambda x: x[1].get("date", ""), reverse=True)
        active = dict(sorted_entries[:CACHE_MAX_ENTRIES])

    return active


def save_cache(cache: dict):
    """保存 URL 缓存"""
    ensure_cache_dir()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _resolve_short_url(url: str, timeout: int = 5) -> str:
    """短链接展开：通过 HEAD 请求跟随重定向获取最终 URL"""
    parsed = urlparse(url)
    if parsed.netloc.lower() not in SHORT_URL_DOMAINS:
        return url
    try:
        req = Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urlopen(req, timeout=timeout) as resp:
            return resp.url
    except (URLError, OSError, ValueError) as e:
        logger.debug(f"短链接展开失败 {url}: {e}")
        return url


def normalize_url(url: str) -> str:
    url = _resolve_short_url(url)

    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "source",
    }

    parsed = urlparse(url)

    netloc = parsed.netloc.lower()
    netloc = DOMAIN_ALIASES.get(netloc, netloc)

    path = parsed.path.rstrip("/")

    query_params = parse_qs(parsed.query)
    filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}

    base_url = f"{parsed.scheme}://{netloc}{path}"
    if filtered_params:
        query_string = urlencode(filtered_params, doseq=True)
        return f"{base_url}?{query_string}"
    return base_url


def extract_url_from_text(text: str) -> list:
    """从文本中提取所有 URL"""
    url_pattern = r'https?://[^\s<>"\')\]]+(?:\([^\s]*\))?'
    urls = re.findall(url_pattern, text)
    return [normalize_url(url) for url in urls]


def is_duplicate(url: str, doc_content: Optional[str] = None) -> dict:
    """
    检查 URL 是否已存在

    Returns:
        {
            'is_duplicate': bool,
            'source': str,  # 'cache' | 'document' | 'none'
            'normalized_url': str,
            'message': str
        }
    """
    normalized = normalize_url(url)

    cache = load_cache()
    if normalized in cache:
        return {
            "is_duplicate": True,
            "source": "cache",
            "normalized_url": normalized,
            "message": f'链接已在缓存中 (收藏于 {cache[normalized].get("date", "未知时间")})',
        }

    if doc_content:
        existing_urls = extract_url_from_text(doc_content)
        if normalized in existing_urls or url in existing_urls:
            return {
                "is_duplicate": True,
                "source": "document",
                "normalized_url": normalized,
                "message": "链接已在飞书文档中",
            }

    return {
        "is_duplicate": False,
        "source": "none",
        "normalized_url": normalized,
        "message": "新链接，可以收藏",
    }


def add_to_cache(url: str, metadata: Optional[dict] = None):
    """添加 URL 到缓存"""
    cache = load_cache()
    normalized = normalize_url(url)

    cache[normalized] = {
        "original_url": url,
        "date": datetime.now().isoformat(),
        "metadata": metadata or {},
    }
    save_cache(cache)


def main():
    """命令行入口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage:", file=sys.stderr)
        print("  python3 deduplicate.py <url>              # 检查是否重复", file=sys.stderr)
        print("  python3 deduplicate.py --add <url>        # 添加到缓存", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--add":
        if len(sys.argv) < 3:
            print("Error: --add requires a URL", file=sys.stderr)
            sys.exit(1)
        url = sys.argv[2]
        add_to_cache(url)
        print(json.dumps({"success": True, "message": f"已添加到缓存: {url}"}, ensure_ascii=False))
        return

    url = sys.argv[1]
    doc_content = None

    if len(sys.argv) > 2:
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            doc_content = f.read()

    result = is_duplicate(url, doc_content)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
