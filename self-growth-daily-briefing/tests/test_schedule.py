from __future__ import annotations

from pathlib import Path

import pytest

from self_growth_daily_briefing.schedule import ScheduleError, build_schtasks_command, build_task_action


def test_build_task_action_points_to_repo_script():
    action = build_task_action(Path("D:/repo/self-growth-daily-briefing"), python_executable="C:/Python/python.exe")
    assert "run-briefing.ps1" in action
    assert "C:/Python/python.exe" in action


def test_build_schtasks_command_validates_time_format():
    with pytest.raises(ScheduleError):
        build_schtasks_command(Path("D:/repo"), "9am", "TaskName")


def test_build_schtasks_command_contains_required_flags():
    command = build_schtasks_command(Path("D:/repo"), "09:00", "TaskName", python_executable="C:/Python/python.exe")
    assert command[:5] == ["schtasks", "/Create", "/SC", "DAILY", "/TN"]
    assert "09:00" in command
