from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fixture_text(name: str) -> str:
    return (PROJECT_ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8")


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    shutil.copytree(PROJECT_ROOT / "config", root / "config")
    shutil.copytree(PROJECT_ROOT / "templates", root / "templates")
    (root / "data").mkdir()
    (root / "runs").mkdir()
    (root / ".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=test-key",
                "OPENAI_BASE_URL=https://example.invalid/v1",
                "OPENAI_MODEL=test-model",
                "SMTP_HOST=localhost",
                "SMTP_PORT=2525",
                "SMTP_USERNAME=test-user",
                "SMTP_PASSWORD=test-pass",
                "EMAIL_FROM=briefing@example.com",
                "EMAIL_TO=reader@example.com",
            ]
        ),
        encoding="utf-8",
    )
    return root
