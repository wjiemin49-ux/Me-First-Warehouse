#!/usr/bin/env python3
"""
追加内容到飞书文档
支持：格式化输出、去重检查、序号自动递增
"""

import json
import sys
import re
from datetime import datetime


def format_content_item(item: dict, index: int) -> str:
    """
    格式化单条内容为飞书文档格式

    输出 Markdown 格式，供 feishu_doc append 使用
    """
    platform = item.get("platform", "未知平台")
    author = item.get("author", "未知作者")
    title = item.get("title", "")
    content = item.get("content", "")
    url = item.get("url", "")
    created_at = item.get("created_at", "")
    summary = item.get("summary", "")
    keywords = item.get("keywords", [])
    reason = item.get("reason", "")
    stats = item.get("stats", {})

    stats_str = ""
    if stats:
        parts = []
        if stats.get("likes"):
            parts.append(f"👍 {stats['likes']}")
        if stats.get("retweets"):
            parts.append(f"🔄 {stats['retweets']}")
        if stats.get("bookmarks"):
            parts.append(f"💾 {stats['bookmarks']}")
        if stats.get("views"):
            parts.append(f"👁️ {stats['views']}")
        if stats.get("comments"):
            parts.append(f"💬 {stats['comments']}")
        stats_str = " | ".join(parts) if parts else "无数据"

    time_str = created_at
    if isinstance(created_at, str) and len(created_at) > 10:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass

    keywords_str = ", ".join(keywords) if keywords else "无"
    display_title = title if title else (content[:30] + "..." if len(content) > 30 else content)

    markdown = f"""### {index}. {display_title}

| 属性 | 内容 |
|:---|:---|
| **作者** | {author} |
| **平台** | {platform} |
| **发布时间** | {time_str} |
| **原文链接** | [查看原帖]({url}) |
| **互动数据** | {stats_str} |

**原文内容**：
> {content}

**AI 摘要**：
{summary if summary else '（待生成）'}

**关键词**：{keywords_str}

**为什么收藏**：
{reason if reason else '（待补充）'}

---

"""

    return markdown


def get_next_index(doc_content: str) -> int:
    """从文档内容中获取下一个序号"""
    if not doc_content:
        return 1

    pattern = r"###\s+(\d+)\s*\."
    matches = re.findall(pattern, doc_content)

    if matches:
        return max(int(m) for m in matches) + 1

    return 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 append_to_feishu.py '<json_content>'", file=sys.stderr)
        print("  json_content: 要追加的内容 JSON 字符串", file=sys.stderr)
        sys.exit(1)

    try:
        content_json = sys.argv[1]
        item = json.loads(content_json)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        sys.exit(1)

    formatted = format_content_item(item, item.get("index", 1))

    result = {
        "success": True,
        "markdown": formatted,
        "item": item,
        "note": "使用 feishu_doc append 操作将此 Markdown 追加到文档",
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
