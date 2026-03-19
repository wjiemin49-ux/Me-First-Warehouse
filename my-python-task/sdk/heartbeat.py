import json
import pathlib
from datetime import datetime, timezone


def write_heartbeat(root: str | pathlib.Path, status: str = "alive", extra: dict | None = None) -> None:
    root_path = pathlib.Path(root)
    heartbeat_file = root_path / "runtime" / "heartbeat.json"
    heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
    }
    if extra:
        payload.update(extra)
    heartbeat_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
