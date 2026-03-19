"""Path helpers for local development and frozen executable runtime."""

from __future__ import annotations

from pathlib import Path
import sys


def is_frozen() -> bool:
    """Return whether app is running from a frozen bundle."""
    return bool(getattr(sys, "frozen", False))


def runtime_root() -> Path:
    """
    Return writable runtime root.

    - Development: project root.
    - Frozen executable: directory containing the executable.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def bundle_root() -> Path:
    """
    Return read-only bundle root for packaged resources.

    - Development: project root.
    - Frozen executable: sys._MEIPASS when available.
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return runtime_root()


def config_dir() -> Path:
    """Return configuration directory."""
    return runtime_root() / "config"


def qss_dir() -> Path:
    """Return stylesheet directory under runtime/bundle."""
    candidates = [
        bundle_root() / "src" / "sleep_tracker" / "resources" / "qss",
        bundle_root() / "sleep_tracker" / "resources" / "qss",
        runtime_root() / "src" / "sleep_tracker" / "resources" / "qss",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]
