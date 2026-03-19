"""Top-level launcher for Sleep Time Recorder."""

from pathlib import Path
import sys


def bootstrap_path() -> None:
    """Ensure src directory is importable for local runs."""
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    bootstrap_path()
    from sleep_tracker.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
