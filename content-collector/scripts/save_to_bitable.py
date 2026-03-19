#!/usr/bin/env python3
"""
保存内容到飞书多维表格

解决长文本写入问题：
- 短文本字段由 LLM 输出（标题、来源、分类、链接）
- 长文本字段通过文件路径传入（原文内容）
- 跳过 LLM 输出长文本的 token 消耗
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error


DEFAULT_APP_TOKEN = os.environ.get("FEISHU_BITABLE_APP_TOKEN", "")
DEFAULT_TABLE_ID = os.environ.get("FEISHU_BITABLE_TABLE_ID", "")

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


def get_user_access_token() -> Optional[str]:
    """获取用户访问令牌"""
    token = os.environ.get("FEISHU_USER_ACCESS_TOKEN")
    if token:
        return token

    token_path = Path.home() / ".openclaw" / "tokens" / "feishu" / "default" / "user_access_token"
    if token_path.exists():
        try:
            data = json.loads(token_path.read_text())
            token = data.get("access_token") or data.get("user_access_token")
            if token:
                return token
        except (json.JSONDecodeError, KeyError):
            pass

    return None


def call_feishu_api(
    method: str,
    path: str,
    token: str,
    body: Optional[dict] = None,
) -> dict:
    """调用飞书开放平台 API"""
    url = f"{FEISHU_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    data = None
    if body:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("code") != 0:
                raise Exception(f"API error: {result.get('msg', result)}")
            return result.get("data", {})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {error_body}")


def save_to_bitable(
    app_token: str,
    table_id: str,
    token: str,
    title: str,
    source: str,
    category: str,
    url: str,
    content: str,
) -> dict:
    """保存内容到多维表格"""
    fields = {
        "标题": title,
        "来源": source,
        "分类": category,
        "原文链接": url,
        "原文内容": content,
    }

    path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    body = {
        "fields": fields,
    }

    result = call_feishu_api("POST", path, token, body)
    return result


def update_content_field(
    app_token: str,
    table_id: str,
    token: str,
    record_id: str,
    content: str,
) -> dict:
    """更新多维表格记录的"原文内容"字段"""
    fields = {
        "原文内容": content,
    }

    path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    body = {
        "fields": fields,
    }

    result = call_feishu_api("PUT", path, token, body)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="保存内容到飞书多维表格（支持文件路径传入长文本）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--record-id", help="更新已有记录（只更新原文内容字段）")
    parser.add_argument("--title", help="内容标题（创建模式必需）")
    parser.add_argument("--source", help="来源（创建模式必需）")
    parser.add_argument("--category", help="分类（创建模式必需）")
    parser.add_argument("--url", help="原文链接（创建模式必需）")
    parser.add_argument("--content-file", required=True, help="原文内容的 .md 文件路径")
    parser.add_argument("--app-token", default=DEFAULT_APP_TOKEN, help="多维表格 App Token")
    parser.add_argument("--table-id", default=DEFAULT_TABLE_ID, help="数据表 ID")
    parser.add_argument("--token", help="用户访问令牌（优先于环境变量）")

    args = parser.parse_args()

    if args.record_id:
        mode = "update"
    elif all([args.title, args.source, args.category, args.url]):
        mode = "create"
    else:
        print("错误：需要提供 --record-id（更新模式）或 --title/--source/--category/--url（创建模式）", file=sys.stderr)
        sys.exit(1)

    token = args.token or get_user_access_token()
    if not token:
        print("错误：未找到用户访问令牌", file=sys.stderr)
        print("请设置环境变量 FEISHU_USER_ACCESS_TOKEN 或使用 --token 参数", file=sys.stderr)
        sys.exit(1)

    content_path = Path(args.content_file)
    if not content_path.exists():
        print(f"错误：文件不存在: {content_path}", file=sys.stderr)
        sys.exit(1)

    content = content_path.read_text(encoding="utf-8")

    try:
        if mode == "create":
            result = save_to_bitable(
                app_token=args.app_token,
                table_id=args.table_id,
                token=token,
                title=args.title,
                source=args.source,
                category=args.category,
                url=args.url,
                content=content,
            )

            output = {
                "success": True,
                "mode": "create",
                "record_id": result.get("record", {}).get("record_id"),
                "app_token": args.app_token,
                "table_id": args.table_id,
                "title": args.title,
                "content_length": len(content),
                "message": "✅ 内容已保存到多维表格",
                "url": f"https://my.feishu.cn/base/{args.app_token}?table={args.table_id}",
            }
        else:
            result = update_content_field(
                app_token=args.app_token,
                table_id=args.table_id,
                token=token,
                record_id=args.record_id,
                content=content,
            )

            output = {
                "success": True,
                "mode": "update",
                "record_id": args.record_id,
                "content_length": len(content),
                "message": "✅ 原文内容已更新",
                "url": f"https://my.feishu.cn/base/{args.app_token}?table={args.table_id}",
            }

        print(json.dumps(output, ensure_ascii=False, indent=2))

    except Exception as e:
        output = {
            "success": False,
            "error": str(e),
            "message": f"❌ 保存失败: {e}",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
