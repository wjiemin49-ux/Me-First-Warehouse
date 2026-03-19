from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from .config import FeedDefinition, Settings
from .models import SourceItem, utc_now

FetchFunction = Callable[[str], str]

DEFAULT_USER_AGENT = "self-growth-daily-briefing/0.1 (+https://local)"

KEYWORD_FAMILIES: dict[str, tuple[str, ...]] = {
    "self-growth": ("self-growth", "personal growth", "self improvement", "self-improvement"),
    "habits": ("habit", "habits", "routine", "consistency", "atomic habit"),
    "focus": ("focus", "attention", "deep work", "distraction"),
    "resilience": ("resilience", "bounce back", "adversity", "recover"),
    "confidence": ("confidence", "self-worth", "self esteem", "courage"),
    "burnout": ("burnout", "overwhelmed", "exhausted", "rest"),
    "purpose": ("purpose", "meaning", "direction", "values"),
    "discipline": ("discipline", "grit", "willpower", "commitment"),
    "loneliness": ("loneliness", "connection", "belonging", "community"),
    "mindfulness": ("mindfulness", "presence", "calm", "reflection"),
}


@dataclass(slots=True)
class CollectionResult:
    items: list[SourceItem]
    errors: list[str]
    window_hours: int


def fetch_url(url: str, timeout: int = 30) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/rss+xml, application/xml, application/json, text/xml, text/plain;q=0.8, */*;q=0.5",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean_query = {
        key: values
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}
    }
    clean_path = re.sub(r"/+$", "", parsed.path or "/")
    return urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            clean_path,
            parsed.params,
            urlencode(clean_query, doseq=True),
            "",
        )
    )


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _first_child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        if _local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    text = value.strip()
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return utc_now()


def _score_keywords(title: str, summary: str, tags: list[str]) -> tuple[list[str], float]:
    title_text = f"{title} {' '.join(tags)}".lower()
    body_text = f"{title} {summary} {' '.join(tags)}".lower()
    hits: list[str] = []
    title_hits = 0
    for family, terms in KEYWORD_FAMILIES.items():
        if any(term in body_text for term in terms):
            hits.append(family)
            if any(term in title_text for term in terms):
                title_hits += 1
    score = min(1.0, len(hits) * 0.14 + title_hits * 0.08 + min(len(tags), 3) * 0.04)
    return hits, round(score, 4)


def _make_source_item(
    definition: FeedDefinition,
    title: str,
    summary: str,
    url: str,
    published_at: datetime,
    collected_at: datetime,
    metadata: dict[str, object] | None = None,
) -> SourceItem:
    clean_title = _strip_html(title)
    clean_summary = _strip_html(summary)
    clean_url = normalize_url(url)
    keyword_hits, keyword_score = _score_keywords(clean_title, clean_summary, definition.tags)
    return SourceItem(
        source_name=definition.name,
        source_type=definition.kind,
        source_url=definition.url,
        title=clean_title,
        summary=clean_summary,
        url=url,
        canonical_url=clean_url,
        published_at=published_at,
        collected_at=collected_at,
        keyword_hits=keyword_hits,
        keyword_score=keyword_score,
        trend_bonus=definition.trend_weight,
        metadata=dict(metadata or {}),
    )


def parse_rss_content(content: str, definition: FeedDefinition, collected_at: datetime) -> list[SourceItem]:
    root = ET.fromstring(content)
    items: list[SourceItem] = []
    if _local_name(root.tag) == "feed":
        for entry in root.findall(".//{*}entry"):
            title = _first_child_text(entry, ("title",))
            summary = _first_child_text(entry, ("summary", "content"))
            link = ""
            for link_node in entry.findall(".//{*}link"):
                href = link_node.attrib.get("href")
                rel = link_node.attrib.get("rel", "alternate")
                if href and rel in {"alternate", ""}:
                    link = href
                    break
            published = _first_child_text(entry, ("published", "updated"))
            if title and link:
                items.append(
                    _make_source_item(
                        definition=definition,
                        title=title,
                        summary=summary,
                        url=link,
                        published_at=_parse_datetime(published),
                        collected_at=collected_at,
                    )
                )
        return items

    for item in root.findall(".//item"):
        title = _first_child_text(item, ("title",))
        summary = _first_child_text(item, ("description", "encoded", "content"))
        link = _first_child_text(item, ("link", "guid"))
        published = _first_child_text(item, ("pubDate", "published", "updated"))
        if title and link:
            items.append(
                _make_source_item(
                    definition=definition,
                    title=title,
                    summary=summary,
                    url=link,
                    published_at=_parse_datetime(published),
                    collected_at=collected_at,
                )
            )
    return items


def _derive_reddit_rss_url(url: str) -> str | None:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "r":
        return None
    subreddit = parts[1]
    query = parse_qs(parsed.query)
    listing = query.get("sort", ["top"])[0]
    time_filter = query.get("t", ["day"])[0]
    return f"https://www.reddit.com/r/{subreddit}/{listing}/.rss?t={time_filter}"


def parse_reddit_json(content: str, definition: FeedDefinition, collected_at: datetime) -> list[SourceItem]:
    payload = json.loads(content)
    children = payload.get("data", {}).get("children", [])
    items: list[SourceItem] = []
    for child in children:
        data = child.get("data", {})
        title = str(data.get("title", "")).strip()
        summary = str(data.get("selftext", "") or data.get("subreddit_name_prefixed", "")).strip()
        permalink = data.get("permalink")
        url = f"https://www.reddit.com{permalink}" if permalink else str(data.get("url", "")).strip()
        created_utc = data.get("created_utc")
        published_at = datetime.fromtimestamp(float(created_utc), tz=timezone.utc) if created_utc else collected_at
        if title and url:
            items.append(
                _make_source_item(
                    definition=definition,
                    title=title,
                    summary=summary,
                    url=url,
                    published_at=published_at,
                    collected_at=collected_at,
                    metadata={"score": data.get("score", 0), "num_comments": data.get("num_comments", 0)},
                )
            )
    return items


def _parse_feed(definition: FeedDefinition, content: str, collected_at: datetime) -> list[SourceItem]:
    if definition.kind == "rss":
        return parse_rss_content(content, definition, collected_at)
    if definition.kind == "reddit_json":
        return parse_reddit_json(content, definition, collected_at)
    raise ValueError(f"Unsupported feed kind: {definition.kind}")


def collect_candidates(
    feeds: list[FeedDefinition],
    settings: Settings,
    now: datetime | None = None,
    fetcher: FetchFunction | None = None,
) -> CollectionResult:
    reference_time = now.astimezone(timezone.utc) if now else utc_now()
    fetch = fetcher or fetch_url
    items: list[SourceItem] = []
    errors: list[str] = []

    for definition in feeds:
        try:
            content = fetch(definition.url)
            items.extend(_parse_feed(definition, content, reference_time))
        except HTTPError as exc:
            if definition.kind == "reddit_json" and exc.code == 403:
                fallback_url = _derive_reddit_rss_url(definition.url)
                if fallback_url:
                    try:
                        content = fetch(fallback_url)
                        fallback_definition = FeedDefinition(
                            name=definition.name,
                            kind="rss",
                            url=fallback_url,
                            tags=definition.tags,
                            trend_weight=definition.trend_weight,
                        )
                        items.extend(parse_rss_content(content, fallback_definition, reference_time))
                        continue
                    except Exception as fallback_exc:  # pragma: no cover
                        errors.append(f"{definition.name}: reddit fallback failed: {fallback_exc}")
                        continue
            errors.append(f"{definition.name}: HTTP {exc.code}")
        except Exception as exc:  # pragma: no cover
            errors.append(f"{definition.name}: {exc}")

    relevant = [item for item in items if item.keyword_score > 0]
    primary_window = timedelta(hours=settings.collection_window_hours)
    fallback_window = timedelta(hours=settings.fallback_window_hours)

    def within_window(window: timedelta) -> list[SourceItem]:
        cutoff = reference_time - window
        return [item for item in relevant if item.published_at >= cutoff]

    selected = within_window(primary_window)
    used_window = settings.collection_window_hours
    if len(selected) < settings.minimum_candidate_count and settings.fallback_window_hours > settings.collection_window_hours:
        selected = within_window(fallback_window)
        used_window = settings.fallback_window_hours

    selected.sort(key=lambda item: (item.published_at, item.keyword_score, item.trend_bonus), reverse=True)
    return CollectionResult(items=selected[: settings.max_candidates], errors=errors, window_hours=used_window)
