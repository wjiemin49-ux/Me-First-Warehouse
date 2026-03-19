from __future__ import annotations

import argparse
import calendar
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from urllib.parse import urlparse

import feedparser
import requests


LOGGER = logging.getLogger("daily_report")


def _env(name: str, default: str | None = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_list(name: str) -> list[str]:
    raw = _env(name, "") or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_x_user_spec(spec: str) -> tuple[str, Optional[str]]:
    spec = spec.strip()
    if not spec:
        return "", None
    if "://" not in spec and "=" in spec:
        label, user_part = spec.split("=", 1)
        label = label.strip() or None
        user_part = user_part.strip()
        return user_part, label
    return spec, None


def _normalize_x_username(raw: str) -> Optional[str]:
    value = raw.strip()
    if not value:
        return None

    if "://" in value:
        try:
            parsed = urlparse(value)
            path = (parsed.path or "").strip("/")
            if path:
                value = path.split("/", 1)[0]
        except Exception:
            pass

    if value.startswith("@"):
        value = value[1:]
    if value.endswith("/rss"):
        value = value[:-4]
    if "/" in value:
        value = value.split("/", 1)[0]
    value = value.strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", value):
        return None
    return value


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _entry_datetime_utc(entry: object) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = getattr(entry, key, None)
        if value:
            try:
                return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
            except Exception:
                continue
    return None


def _request_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "daily-report/1.0 (+https://github.com/; RSS fetcher; "
                "contact: local-script)"
            )
        }
    )
    return session


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str


@dataclass(frozen=True)
class Item:
    source: str
    title: str
    url: str
    published_utc: Optional[datetime]
    link_ok: Optional[bool] = None


def fetch_rss(session: requests.Session, source: FeedSource, timeout_s: int = 20) -> feedparser.FeedParserDict:
    try:
        resp = session.get(source.url, timeout=timeout_s)
        resp.raise_for_status()
    except Exception as exc:
        LOGGER.warning("RSS 获取失败: %s (%s)", source.url, exc)
        return feedparser.FeedParserDict(entries=[], version="")

    try:
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        LOGGER.warning("RSS 解析失败: %s (%s)", source.url, exc)
        return feedparser.FeedParserDict(entries=[], version="")
    finally:
        try:
            resp.close()
        except Exception:
            pass

    if not getattr(parsed, "version", ""):
        LOGGER.warning("RSS 返回内容不是有效 Feed: %s", source.url)
        return feedparser.FeedParserDict(entries=[], version="")
    if getattr(parsed, "bozo", 0):
        exc = getattr(parsed, "bozo_exception", None)
        LOGGER.warning("RSS 解析存在异常: %s (%s)", source.url, exc)

    return parsed


def pick_recent_items(
    *,
    source_name: str,
    entries: Iterable[object],
    since_utc: datetime,
) -> list[Item]:
    results: list[Item] = []
    for entry in entries:
        title = (getattr(entry, "title", None) or "").strip() or "(无标题)"
        url = (getattr(entry, "link", None) or "").strip()
        if not url:
            continue

        published_utc = _entry_datetime_utc(entry)
        if published_utc is None:
            continue
        if published_utc < since_utc:
            continue

        results.append(
            Item(
                source=source_name,
                title=title,
                url=url,
                published_utc=published_utc,
            )
        )
    return results


def validate_links(session: requests.Session, items: list[Item], timeout_s: int = 10) -> list[Item]:
    validated: list[Item] = []
    for item in items:
        ok: Optional[bool] = None
        head: Optional[requests.Response] = None
        get: Optional[requests.Response] = None
        try:
            head = session.head(item.url, allow_redirects=True, timeout=timeout_s)
            if head.status_code == 405:
                raise requests.HTTPError("HEAD not allowed")
            ok = 200 <= head.status_code < 400
            if not ok:
                LOGGER.warning("链接可能失效: %s (HTTP %s)", item.url, head.status_code)
        except Exception as exc:
            try:
                get = session.get(
                    item.url,
                    allow_redirects=True,
                    timeout=timeout_s,
                    stream=True,
                    headers={"Range": "bytes=0-0"},
                )
                ok = 200 <= get.status_code < 400
                if not ok:
                    LOGGER.warning("链接可能失效: %s (HTTP %s)", item.url, get.status_code)
            except Exception as exc2:
                ok = False
                LOGGER.warning("链接检查失败: %s (%s; %s)", item.url, exc, exc2)
            finally:
                if get is not None:
                    try:
                        get.close()
                    except Exception:
                        pass
        finally:
            if head is not None:
                try:
                    head.close()
                except Exception:
                    pass

        validated.append(
            Item(
                source=item.source,
                title=item.title,
                url=item.url,
                published_utc=item.published_utc,
                link_ok=ok,
            )
        )
    return validated


def build_markdown(now_utc: datetime, items: list[Item]) -> str:
    def fmt_dt(dt: Optional[datetime]) -> str:
        if not dt:
            return ""
        return _as_utc(dt).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append(f"# Daily Report ({now_utc.strftime('%Y-%m-%d')})")
    lines.append("")
    lines.append(f"- 生成时间：{now_utc.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    if not items:
        lines.append("过去 24 小时内无更新。")
        lines.append("")
        return "\n".join(lines)

    items_sorted = sorted(items, key=lambda i: (i.source, i.published_utc or now_utc), reverse=True)
    grouped: dict[str, list[Item]] = {}
    for item in items_sorted:
        grouped.setdefault(item.source, []).append(item)

    for source, source_items in grouped.items():
        lines.append(f"## {source}")
        lines.append("")
        for item in sorted(source_items, key=lambda i: i.published_utc or now_utc, reverse=True):
            status = ""
            if item.link_ok is False:
                status = " (链接可能失效)"
            lines.append(f"- [{item.title}]({item.url}){status}（{fmt_dt(item.published_utc)}）")
        lines.append("")

    return "\n".join(lines)


def send_via_wecom_markdown(session: requests.Session, webhook: str, content: str, timeout_s: int = 20) -> None:
    # 企业微信机器人 markdown 单次内容长度有限，做简单分片
    max_len = 3500
    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in content.splitlines():
        add_len = len(line) + 1
        if current and current_len + add_len > max_len:
            parts.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += add_len
    if current:
        parts.append("\n".join(current))

    for idx, part in enumerate(parts, start=1):
        payload = {"msgtype": "markdown", "markdown": {"content": part}}
        resp: Optional[requests.Response] = None
        try:
            resp = session.post(webhook, json=payload, timeout=timeout_s)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode") != 0:
                raise RuntimeError(f"WeCom error: {json.dumps(data, ensure_ascii=False)}")
        except Exception as exc:
            raise RuntimeError(f"企业微信推送失败 (part {idx}/{len(parts)}): {exc}") from exc
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass


def send_via_smtp(markdown: str) -> None:
    import smtplib
    from email.message import EmailMessage

    host = _env("SMTP_HOST")
    port = int(_env("SMTP_PORT", "587") or "587")
    user = _env("SMTP_USER")
    password = _env("SMTP_PASS")
    mail_from = _env("SMTP_FROM", user or "")
    mail_to = _env("SMTP_TO", "")
    subject = _env("SMTP_SUBJECT", "Daily Report")
    use_tls = (_env("SMTP_STARTTLS", "true") or "true").lower() in {"1", "true", "yes", "y"}
    use_ssl = (_env("SMTP_SSL", "false") or "false").lower() in {"1", "true", "yes", "y"}

    if not host or not mail_from or not mail_to:
        raise RuntimeError("SMTP 配置不完整：需要 SMTP_HOST、SMTP_FROM、SMTP_TO（以及通常需要 SMTP_USER/SMTP_PASS）")

    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject
    msg.set_content(markdown, subtype="plain", charset="utf-8")

    if use_ssl:
        use_tls = False
        with smtplib.SMTP_SSL(host=host, port=port, timeout=30) as server:
            server.ehlo()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host=host, port=port, timeout=30) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            if user and password:
                server.login(user, password)
            server.send_message(msg)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Daily RSS report (X via Nitter + WeChat RSS).")
    parser.add_argument("--dry-run", action="store_true", help="仅输出 Markdown，不推送")
    parser.add_argument("--output", default=_env("REPORT_PATH", "report.md"), help="输出 Markdown 文件路径")
    parser.add_argument("--append", action="store_true", help="追加写入 output 文件（作为历史归档）")
    parser.add_argument("--no-push", action="store_true", help="只生成本地报告，不推送")
    parser.add_argument("--no-link-check", action="store_true", help="不检查条目链接可用性")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    now_utc = datetime.now(timezone.utc)
    since_utc = now_utc - timedelta(hours=24)

    session = _request_session()

    items: list[Item] = []

    # X via Nitter RSS
    x_users = _env_list("X_USERS")
    nitter_bases = _env_list("NITTER_BASE_URLS") or ["https://nitter.net"]
    for spec in x_users:
        user_raw, label = _parse_x_user_spec(spec)
        user = _normalize_x_username(user_raw)
        if not user:
            LOGGER.warning("跳过无效的 X 用户配置：%s（需要 @handle / profile URL / 显示名=handle）", spec)
            continue

        display = f"𝕏 @{user}"
        if label:
            display = f"𝕏 {label} (@{user})"

        feed: Optional[feedparser.FeedParserDict] = None
        last_error: Optional[str] = None
        for base in nitter_bases:
            url = f"{base.rstrip('/')}/{user}/rss"
            source = FeedSource(name=display, url=url)
            parsed = fetch_rss(session, source)
            if getattr(parsed, "version", ""):
                feed = parsed
                break
            last_error = url
        if feed is None:
            if last_error:
                LOGGER.warning("未获取到 𝕏 RSS：%s（可能被限流/实例不可用）", last_error)
            continue
        items.extend(pick_recent_items(source_name=display, entries=feed.entries, since_utc=since_utc))

    # WeChat RSS (3rd party)
    wechat_rss_urls = _env_list("WECHAT_RSS_URLS")
    for rss_url in wechat_rss_urls:
        source = FeedSource(name="微信 RSS", url=rss_url)
        parsed = fetch_rss(session, source)
        if not getattr(parsed, "version", ""):
            continue

        feed_title = ""
        try:
            feed_title = (getattr(parsed, "feed", {}) or {}).get("title", "") or ""
        except Exception:
            feed_title = ""

        source_name = "微信 RSS"
        feed_title = str(feed_title).strip()
        if feed_title:
            source_name = f"微信 RSS - {feed_title}"

        items.extend(pick_recent_items(source_name=source_name, entries=parsed.entries, since_utc=since_utc))

    if not args.no_link_check and items:
        items = validate_links(session, items)

    markdown = build_markdown(now_utc, items)

    if args.output:
        try:
            write_mode = "a" if args.append else "w"
            sep = "\n\n---\n\n"
            if args.append:
                try:
                    if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
                        with open(args.output, "a", encoding="utf-8") as f:
                            f.write(sep)
                except Exception:
                    pass
            with open(args.output, write_mode, encoding="utf-8") as f:
                f.write(markdown)
        except Exception as exc:
            LOGGER.warning("写入报告失败: %s (%s)", args.output, exc)

    if args.dry_run:
        print(markdown)
        return 0
    if args.no_push:
        LOGGER.info("已生成本地报告，按 --no-push 跳过推送")
        return 0

    wecom_webhook = _env("WECOM_WEBHOOK")
    smtp_host = _env("SMTP_HOST")

    if not wecom_webhook and not smtp_host:
        LOGGER.error("未配置推送渠道：请设置 WECOM_WEBHOOK 或 SMTP_HOST（或两者都设置）")
        return 2

    any_ok = False
    if wecom_webhook:
        try:
            send_via_wecom_markdown(session, wecom_webhook, markdown)
            LOGGER.info("企业微信推送成功")
            any_ok = True
        except Exception as exc:
            LOGGER.error("%s", exc)

    if smtp_host:
        try:
            send_via_smtp(markdown)
            LOGGER.info("SMTP 邮件发送成功")
            any_ok = True
        except Exception as exc:
            LOGGER.error("SMTP 邮件发送失败: %s", exc)

    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
