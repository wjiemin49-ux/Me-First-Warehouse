from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    """Raised when configuration is invalid."""


@dataclass(slots=True)
class Settings:
    timezone: str
    send_time: str
    output_language: str
    article_length: str
    max_candidates: int
    fallback_window_hours: int
    dedupe_days: int
    collection_window_hours: int = 48
    minimum_candidate_count: int = 5
    task_name: str = "SelfGrowthDailyBriefing"


@dataclass(slots=True)
class FeedDefinition:
    name: str
    kind: str
    url: str
    tags: list[str]
    trend_weight: float = 1.0


@dataclass(slots=True)
class AppConfig:
    project_root: Path
    settings: Settings
    feeds: list[FeedDefinition]
    env: dict[str, str]

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def runs_dir(self) -> Path:
        return self.project_root / "runs"

    @property
    def templates_dir(self) -> Path:
        return self.project_root / "templates"

    @property
    def state_db_path(self) -> Path:
        return self.data_dir / "state.sqlite3"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing configuration file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigError(f"Configuration file must contain a mapping: {path}")
    return payload


def resolve_project_root(project_root: str | os.PathLike[str] | None = None) -> Path:
    if project_root:
        root = Path(project_root).expanduser().resolve()
    else:
        root = Path.cwd().resolve()
    return root


def ensure_runtime_dirs(config: AppConfig) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.runs_dir.mkdir(parents=True, exist_ok=True)


def load_config(project_root: str | os.PathLike[str] | None = None) -> AppConfig:
    root = resolve_project_root(project_root)
    env_from_file = _parse_env_file(root / ".env")
    merged_env = dict(env_from_file)
    for key, value in os.environ.items():
        if key in env_from_file or key.startswith("OPENAI_") or key.startswith("SMTP_") or key.startswith("EMAIL_"):
            merged_env[key] = value

    settings_payload = _load_yaml(root / "config" / "settings.yaml")
    feeds_payload = _load_yaml(root / "config" / "feeds.yaml")

    settings = Settings(
        timezone=str(settings_payload.get("timezone", "Asia/Shanghai")),
        send_time=str(settings_payload.get("send_time", "09:00")),
        output_language=str(settings_payload.get("output_language", "zh-CN")),
        article_length=str(settings_payload.get("article_length", "1200-1800")),
        max_candidates=int(settings_payload.get("max_candidates", 12)),
        fallback_window_hours=int(settings_payload.get("fallback_window_hours", 72)),
        dedupe_days=int(settings_payload.get("dedupe_days", 7)),
        collection_window_hours=int(settings_payload.get("collection_window_hours", 48)),
        minimum_candidate_count=int(settings_payload.get("minimum_candidate_count", 5)),
        task_name=str(settings_payload.get("task_name", "SelfGrowthDailyBriefing")),
    )

    feeds_raw = feeds_payload.get("feeds", [])
    if not isinstance(feeds_raw, list) or not feeds_raw:
        raise ConfigError("config/feeds.yaml must define a non-empty 'feeds' list")

    feeds = [
        FeedDefinition(
            name=str(item["name"]),
            kind=str(item["kind"]),
            url=str(item["url"]),
            tags=[str(tag) for tag in item.get("tags", [])],
            trend_weight=float(item.get("trend_weight", 1.0)),
        )
        for item in feeds_raw
    ]

    config = AppConfig(project_root=root, settings=settings, feeds=feeds, env=merged_env)
    ensure_runtime_dirs(config)
    return config
