from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.request import Request, urlopen

from .models import ArticleSource, DailyIssue, TopicCluster, TopicDecision

Transport = Callable[[dict[str, Any]], dict[str, Any]]


class LLMConfigurationError(RuntimeError):
    """Raised when LLM configuration is missing."""


class LLMResponseError(RuntimeError):
    """Raised when the model returns invalid content."""


def _json_from_text(content: str) -> dict[str, Any]:
    text = content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMResponseError("Model response did not contain JSON")
        return json.loads(text[start : end + 1])


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not choices:
        raise LLMResponseError("Model response did not contain choices")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        return "\n".join(part for part in parts if part)
    raise LLMResponseError("Unsupported content type returned by model")


def _clean_text(value: str) -> str:
    return " ".join(str(value).replace("\r", "\n").split()).strip()


def _flatten_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, (int, float, bool)):
        return _clean_text(str(value))
    if isinstance(value, list):
        parts = [_flatten_value(item) for item in value]
        parts = [part for part in parts if part]
        return "；".join(parts)
    if isinstance(value, dict):
        lead = _flatten_value(
            value.get("title")
            or value.get("prompt")
            or value.get("summary")
            or value.get("theme")
            or value.get("name")
        )
        sections: list[str] = []
        points = _flatten_value(value.get("points"))
        if points:
            sections.append(f"要点：{points}")
        steps = _flatten_value(value.get("steps"))
        if steps:
            sections.append(f"步骤：{steps}")
        output = _flatten_value(value.get("output"))
        if output:
            sections.append(f"落地结果：{output}")
        for key in ("action", "example", "note"):
            extra = _flatten_value(value.get(key))
            if extra:
                sections.append(extra)
        remaining_sections = []
        for key, item in value.items():
            if key in {"title", "prompt", "summary", "theme", "name", "points", "steps", "output", "action", "example", "note"}:
                continue
            extra = _flatten_value(item)
            if extra:
                remaining_sections.append(f"{key}：{extra}")
        sections.extend(remaining_sections)
        if lead and sections:
            return f"{lead}。{'；'.join(sections)}"
        if lead:
            return lead
        return "；".join(sections)
    return _clean_text(str(value))


def _normalize_string_field(payload: dict[str, Any], key: str, fallback: str) -> str:
    value = _flatten_value(payload.get(key))
    return value or fallback


def _normalize_string_list(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> list[str]:
    raw_value = payload.get(key, [])
    candidates = raw_value if isinstance(raw_value, list) else [raw_value]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        text = _flatten_value(item)
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    if len(cleaned) < minimum:
        raise LLMResponseError(f"Model response did not contain enough {key}")
    return cleaned[:maximum]


def _normalize_article_payload(payload: dict[str, Any], decision: TopicDecision) -> dict[str, Any]:
    return {
        "title": _normalize_string_field(payload, "title", decision.theme),
        "hook": _normalize_string_field(payload, "hook", decision.angle),
        "why_now": _normalize_string_field(payload, "why_now", decision.rationale),
        "core_insight": _normalize_string_field(payload, "core_insight", decision.angle),
        "reflections": _normalize_string_list(payload, "reflections", minimum=2, maximum=3),
        "action_prompts": _normalize_string_list(payload, "action_prompts", minimum=3, maximum=3),
        "closing": _normalize_string_field(payload, "closing", "愿今天的成长提醒，能变成你真正用得上的一步。"),
    }


def compose_article_markdown(
    title: str,
    hook: str,
    why_now: str,
    core_insight: str,
    reflections: list[str],
    action_prompts: list[str],
    closing: str,
    source_links: list[ArticleSource],
) -> str:
    lines = [
        f"# {title}",
        "",
        hook,
        "",
        "## 为什么这个主题值得今天认真看一眼",
        why_now,
        "",
        "## 核心洞察",
        core_insight,
        "",
        "## 成长体会",
    ]
    for item in reflections:
        lines.append(f"- {item}")
    lines.extend(["", "## 今天就能开始的 3 个动作"])
    for index, prompt in enumerate(action_prompts, start=1):
        lines.append(f"{index}. {prompt}")
    lines.extend(["", "## 结尾", closing, "", "## 参考来源"])
    for source in source_links:
        lines.append(f"- [{source.source_name}] {source.title}: {source.url}")
    return "\n".join(lines).strip()


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        transport: Transport | None = None,
        timeout: int = 90,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport
        self.timeout = timeout

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.transport:
            return self.transport(payload)
        if not self.api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured")
        url = f"{self.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = self._post(payload)
        return _json_from_text(_extract_message_content(response))

    def choose_topic(self, clusters: list[TopicCluster], recent_themes: list[str] | None = None) -> TopicDecision:
        recent_themes = recent_themes or []
        cluster_payload = [
            {
                "cluster_id": cluster.cluster_id,
                "representative_title": cluster.representative_title,
                "score": cluster.score,
                "source_names": cluster.source_names,
                "keyword_hits": sorted({hit for item in cluster.items for hit in item.keyword_hits}),
                "items": [
                    {"title": item.title, "url": item.canonical_url, "source_name": item.source_name}
                    for item in cluster.items[:4]
                ],
            }
            for cluster in clusters[:5]
        ]
        response = self._chat_json(
            system_prompt=(
                "You are an editorial strategist. Choose one topic for a Chinese daily self-growth email. "
                "Prefer a single emotionally resonant theme that is timely, practical, and not repetitive."
            ),
            user_prompt=(
                "Choose exactly one theme from the candidate clusters.\n"
                f"Recent themes to avoid if possible: {recent_themes or '[]'}\n"
                "Return JSON only with keys: theme, angle, rationale, selected_cluster_id, supporting_urls, supporting_titles, keywords.\n"
                f"Clusters:\n{json.dumps(cluster_payload, ensure_ascii=False, indent=2)}"
            ),
        )
        selected_cluster_id = str(response.get("selected_cluster_id", clusters[0].cluster_id))
        cluster_map = {cluster.cluster_id: cluster for cluster in clusters}
        selected_cluster = cluster_map.get(selected_cluster_id, clusters[0])
        supporting_urls = [str(url) for url in response.get("supporting_urls", []) if str(url).strip()]
        supporting_titles = [str(title) for title in response.get("supporting_titles", []) if str(title).strip()]
        if not supporting_urls:
            supporting_urls = [item.canonical_url for item in selected_cluster.items[:3]]
        if not supporting_titles:
            supporting_titles = [item.title for item in selected_cluster.items[:3]]
        keywords = [str(keyword) for keyword in response.get("keywords", []) if str(keyword).strip()]
        return TopicDecision(
            theme=str(response.get("theme", selected_cluster.representative_title)).strip(),
            angle=str(response.get("angle", "从今天最值得关心的变化里，找到一个更温柔但更有效的行动切口。")).strip(),
            rationale=str(response.get("rationale", "这个主题兼具现实压力与成长价值，适合作为今天的核心提醒。")).strip(),
            selected_cluster_id=selected_cluster.cluster_id,
            supporting_urls=supporting_urls,
            supporting_titles=supporting_titles,
            keywords=keywords or sorted({hit for item in selected_cluster.items for hit in item.keyword_hits})[:4],
        )

    def write_article(
        self,
        decision: TopicDecision,
        cluster: TopicCluster,
        issue_date: str,
        article_length: str,
        language: str,
    ) -> dict[str, Any]:
        source_context = [
            {"title": item.title, "source_name": item.source_name, "summary": item.summary[:360], "url": item.canonical_url}
            for item in cluster.items[:5]
        ]
        response = self._chat_json(
            system_prompt=(
                "You are a compassionate Chinese columnist writing a daily growth letter. "
                "Write with emotional clarity, grounded hope, and practical action. Avoid cliches."
            ),
            user_prompt=(
                "Write a Chinese article outline as JSON only.\n"
                f"Target language: {language}\n"
                f"Length target: {article_length} Chinese characters\n"
                f"Issue date: {issue_date}\n"
                f"Theme: {decision.theme}\n"
                f"Angle: {decision.angle}\n"
                f"Rationale: {decision.rationale}\n"
                "Return JSON with keys: title, hook, why_now, core_insight, reflections, action_prompts, closing.\n"
                "Requirements:\n"
                "- reflections must contain 2 or 3 items\n"
                "- action_prompts must contain exactly 3 items\n"
                "- keep the tone warm, sincere, and concrete\n"
                f"Source context:\n{json.dumps(source_context, ensure_ascii=False, indent=2)}"
            ),
            temperature=0.55,
        )
        return _normalize_article_payload(response, decision)


@dataclass(slots=True)
class HeuristicLLMClient:
    """Deterministic fallback used by tests and dry runs without external APIs."""

    source_hint: str = "heuristic"

    def choose_topic(self, clusters: list[TopicCluster], recent_themes: list[str] | None = None) -> TopicDecision:
        recent_themes = recent_themes or []
        selected = clusters[0]
        for candidate in clusters:
            normalized = candidate.representative_title.lower()
            if not any(theme.lower() in normalized for theme in recent_themes):
                selected = candidate
                break
        keywords = sorted({hit for item in selected.items for hit in item.keyword_hits})[:4]
        theme_map = {
            "burnout": "当成长开始让人疲惫时，怎样把节奏找回来",
            "focus": "注意力分散的时代，为什么我们更需要温柔的专注",
            "discipline": "真正能持续下去的自律，往往不是硬撑出来的",
            "purpose": "当方向感变弱时，先把意义感找回来",
            "habits": "比起一次性爆发，稳定的小习惯更能托住自己",
        }
        theme = next((theme_map[keyword] for keyword in keywords if keyword in theme_map), "把今天的成长，重新放回可实践的日常里")
        return TopicDecision(
            theme=theme,
            angle="从今天最集中的外部信号里，找到一个更适合普通人真实生活的成长切口。",
            rationale="它同时回应了外部趋势和个体情绪，既不空泛，也不会让人产生额外负担。",
            selected_cluster_id=selected.cluster_id,
            supporting_urls=[item.canonical_url for item in selected.items[:3]],
            supporting_titles=[item.title for item in selected.items[:3]],
            keywords=keywords,
        )

    def write_article(
        self,
        decision: TopicDecision,
        cluster: TopicCluster,
        issue_date: str,
        article_length: str,
        language: str,
    ) -> dict[str, Any]:
        sources = [item.title for item in cluster.items[:3]]
        return {
            "title": decision.theme,
            "hook": f"很多人以为成长一定要靠更狠的要求自己，但今天的信号更像是在提醒我们：真正可持续的改变，往往从承认自己的状态开始。{sources[0]} 之所以被反复讨论，不只是因为它新，而是因为它戳中了很多人正在经历的现实。",
            "why_now": f"在 {issue_date} 这一天，这个主题值得被拿出来，是因为我们正在同时面对注意力被切碎、情绪被拉扯、目标感又容易摇晃的环境。与其继续追求完美执行，不如先看清楚什么动作真的能帮自己稳下来。",
            "core_insight": "成长不是一场只靠意志力赢下来的战斗，它更像是一套可被照顾、可被调整、也可被重复的小系统。先让自己回到能行动的状态，比强迫自己立刻变得更厉害更重要。",
            "reflections": [
                "我们常常把停顿误解成退步，但很多时候，停下来是在给自己重新校准方向的空间。",
                "当一个建议只在高能量状态下有效，它就很难陪你走长线；真正好的方法，应该在疲惫时也能执行一点点。",
                "如果今天只能做一件小事，选那个最能减少内耗、最能恢复掌控感的动作，而不是最看起来厉害的动作。",
            ],
            "action_prompts": [
                "写下此刻最消耗你的一个念头，并把它改写成一个今天就能做的小动作。",
                "为今天设一个 20 分钟的低阻力专注块，只处理一件真正重要的小事。",
                "在睡前回看：什么行为让你更安定，什么行为让你更分散，把这个观察留给明天的自己。",
            ],
            "closing": f"成长从来不是为了证明你够不够好，而是为了让你越来越能陪自己走下去。愿今天的这封信，不是给你额外的压力，而是给你一点更温柔也更稳的力量。来源信号包括：{'；'.join(sources)}。",
        }


def create_issue(
    issue_date: str,
    decision: TopicDecision,
    cluster: TopicCluster,
    article_payload: dict[str, Any],
) -> DailyIssue:
    source_links = [
        ArticleSource(title=item.title, url=item.canonical_url, source_name=item.source_name)
        for item in cluster.items[:4]
    ]
    article_markdown = compose_article_markdown(
        title=article_payload["title"],
        hook=article_payload["hook"],
        why_now=article_payload["why_now"],
        core_insight=article_payload["core_insight"],
        reflections=article_payload["reflections"],
        action_prompts=article_payload["action_prompts"],
        closing=article_payload["closing"],
        source_links=source_links,
    )
    subject = f"【成长晨读】{issue_date}｜{decision.theme}"
    return DailyIssue(
        issue_date=issue_date,
        subject=subject,
        theme=decision.theme,
        title=article_payload["title"],
        angle=decision.angle,
        hook=article_payload["hook"],
        why_now=article_payload["why_now"],
        core_insight=article_payload["core_insight"],
        reflections=list(article_payload["reflections"]),
        action_prompts=list(article_payload["action_prompts"]),
        closing=article_payload["closing"],
        article_markdown=article_markdown,
        source_links=source_links,
        selected_cluster_id=decision.selected_cluster_id,
        metadata={
            "rationale": decision.rationale,
            "supporting_urls": decision.supporting_urls,
            "supporting_titles": decision.supporting_titles,
            "keywords": decision.keywords,
        },
    )
