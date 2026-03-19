from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


class ScheduleError(RuntimeError):
    """Raised when Windows Task Scheduler configuration is invalid."""


TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def build_task_action(project_root: Path, python_executable: str | None = None) -> str:
    script_path = project_root / "scripts" / "run-briefing.ps1"
    executable = python_executable or sys.executable
    return (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{script_path}" '
        f'-ProjectRoot "{project_root}" -PythonExecutable "{executable}"'
    )


def build_schtasks_command(
    project_root: Path,
    time_text: str,
    task_name: str,
    python_executable: str | None = None,
) -> list[str]:
    if not TIME_PATTERN.match(time_text):
        raise ScheduleError("Scheduled task time must use HH:MM format")
    return [
        "schtasks",
        "/Create",
        "/SC",
        "DAILY",
        "/TN",
        task_name,
        "/TR",
        build_task_action(project_root=project_root, python_executable=python_executable),
        "/ST",
        time_text,
        "/F",
    ]


def install_daily_task(
    project_root: Path,
    time_text: str,
    task_name: str,
    python_executable: str | None = None,
    runner=subprocess.run,
) -> Sequence[str]:
    command = build_schtasks_command(
        project_root=project_root,
        time_text=time_text,
        task_name=task_name,
        python_executable=python_executable,
    )
    runner(command, check=True)
    return command
