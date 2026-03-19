from __future__ import annotations

import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from string import Template
from typing import Callable

from .models import DailyIssue, SendResult

SmtpFactory = Callable[..., smtplib.SMTP]
SleepFunction = Callable[[float], None]


class MailConfigurationError(RuntimeError):
    """Raised when SMTP configuration is incomplete."""


@dataclass(slots=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    email_from: str
    email_to: str


def load_smtp_config(env: dict[str, str]) -> SmtpConfig:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise MailConfigurationError(f"Missing SMTP configuration: {', '.join(missing)}")
    return SmtpConfig(
        host=env["SMTP_HOST"],
        port=int(env["SMTP_PORT"]),
        username=env["SMTP_USERNAME"],
        password=env["SMTP_PASSWORD"],
        email_from=env["EMAIL_FROM"],
        email_to=env["EMAIL_TO"],
    )


def _render_html_sources(issue: DailyIssue) -> str:
    return "\n".join(
        f'<li><a href="{source.url}">{source.source_name}</a> - {source.title}</li>' for source in issue.source_links
    )


def _render_text_sources(issue: DailyIssue) -> str:
    return "\n".join(f"- [{source.source_name}] {source.title}: {source.url}" for source in issue.source_links)


def _render_html_reflections(issue: DailyIssue) -> str:
    return "\n".join(f"<li>{item}</li>" for item in issue.reflections)


def _render_html_actions(issue: DailyIssue) -> str:
    return "\n".join(f"<li>{item}</li>" for item in issue.action_prompts)


def _render_text_reflections(issue: DailyIssue) -> str:
    return "\n".join(f"- {item}" for item in issue.reflections)


def _render_text_actions(issue: DailyIssue) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(issue.action_prompts, start=1))


def render_email_bodies(issue: DailyIssue, templates_dir: Path) -> tuple[str, str]:
    html_template = Template((templates_dir / "email.html").read_text(encoding="utf-8"))
    text_template = Template((templates_dir / "email.txt").read_text(encoding="utf-8"))
    html_body = html_template.safe_substitute(
        subject=issue.subject,
        theme=issue.theme,
        title=issue.title,
        angle=issue.angle,
        hook=issue.hook,
        why_now=issue.why_now,
        core_insight=issue.core_insight,
        reflections_html=_render_html_reflections(issue),
        actions_html=_render_html_actions(issue),
        closing=issue.closing,
        sources_html=_render_html_sources(issue),
        issue_date=issue.issue_date,
    )
    text_body = text_template.safe_substitute(
        subject=issue.subject,
        theme=issue.theme,
        title=issue.title,
        angle=issue.angle,
        hook=issue.hook,
        why_now=issue.why_now,
        core_insight=issue.core_insight,
        reflections_text=_render_text_reflections(issue),
        actions_text=_render_text_actions(issue),
        closing=issue.closing,
        sources_text=_render_text_sources(issue),
        issue_date=issue.issue_date,
    )
    return html_body, text_body


def _send_message(smtp_config: SmtpConfig, message: EmailMessage, smtp_factory: SmtpFactory | None = None) -> None:
    factory = smtp_factory or smtplib.SMTP
    is_local = smtp_config.host in {"127.0.0.1", "localhost"}
    with factory(smtp_config.host, smtp_config.port, timeout=30) as client:
        try:
            client.starttls()
        except smtplib.SMTPNotSupportedError:
            if not is_local:
                raise
        try:
            client.login(smtp_config.username, smtp_config.password)
        except smtplib.SMTPNotSupportedError:
            if not is_local:
                raise
        client.send_message(message)


def send_issue(
    issue: DailyIssue,
    smtp_config: SmtpConfig,
    templates_dir: Path,
    smtp_factory: SmtpFactory | None = None,
    sleep_func: SleepFunction | None = None,
    retry_delay_seconds: int = 600,
) -> SendResult:
    html_body, text_body = render_email_bodies(issue, templates_dir)
    message = EmailMessage()
    message["Subject"] = issue.subject
    message["From"] = smtp_config.email_from
    message["To"] = smtp_config.email_to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    delay = sleep_func or time.sleep
    attempts = 0
    last_error: str | None = None
    for attempt in range(1, 3):
        attempts = attempt
        try:
            _send_message(smtp_config, message, smtp_factory=smtp_factory)
            return SendResult(status="sent", attempts=attempts, recipient=smtp_config.email_to, subject=issue.subject)
        except Exception as exc:  # pragma: no cover
            last_error = str(exc)
            if attempt == 1:
                delay(retry_delay_seconds)
            else:
                break
    return SendResult(
        status="failed",
        attempts=attempts,
        recipient=smtp_config.email_to,
        subject=issue.subject,
        error=last_error,
    )


def send_test_email(smtp_config: SmtpConfig, smtp_factory: SmtpFactory | None = None) -> SendResult:
    message = EmailMessage()
    message["Subject"] = "Self Growth Daily Briefing SMTP Test"
    message["From"] = smtp_config.email_from
    message["To"] = smtp_config.email_to
    message.set_content("SMTP test OK. Your self-growth daily briefing pipeline can send email.")
    _send_message(smtp_config, message, smtp_factory=smtp_factory)
    return SendResult(status="sent", attempts=1, recipient=smtp_config.email_to, subject=message["Subject"])
