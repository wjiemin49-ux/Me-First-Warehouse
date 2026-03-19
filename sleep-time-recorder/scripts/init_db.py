"""Initialize SQLite schema for Sleep Time Recorder."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def bootstrap_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return root


def main() -> int:
    root = bootstrap_path()

    parser = argparse.ArgumentParser(description="Initialize sleep tracker database.")
    parser.add_argument(
        "--db",
        dest="db_path",
        default="sleep_records.db",
        help="SQLite db file path. Relative paths are based on project root.",
    )
    args = parser.parse_args()

    from sleep_tracker.data import DatabaseManager

    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = root / db_path

    manager = DatabaseManager(db_path=db_path)
    manager.initialize_schema()
    print(f"Database initialized: {manager.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
