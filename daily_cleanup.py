from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


LOGGER = logging.getLogger("daily_cleanup")


def _env(name: str, default: str | None = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_resolve(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except Exception:
        return path.expanduser().absolute()


def _is_drive_root(path: Path) -> bool:
    resolved = _safe_resolve(path)
    return resolved.parent == resolved


@dataclass(frozen=True)
class Target:
    path: Path
    patterns: list[str]
    older_than_hours: Optional[float]
    recursive: bool = True


def _load_config(config_path: Path) -> list[Target]:
    resolved = _safe_resolve(config_path)
    if not resolved.exists():
        raise FileNotFoundError(f"配置文件不存在: {resolved}")

    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"配置文件解析失败（需要 JSON）: {resolved} ({exc})") from exc

    if not isinstance(data, dict):
        raise ValueError("配置根节点必须是对象（dict）")

    targets_raw = data.get("targets", [])
    if not isinstance(targets_raw, list):
        raise ValueError("配置字段 targets 必须是数组（list）")

    targets: list[Target] = []
    for idx, t in enumerate(targets_raw, start=1):
        if not isinstance(t, dict):
            raise ValueError(f"targets[{idx}] 必须是对象（dict）")
        path_raw = t.get("path")
        if not isinstance(path_raw, str) or not path_raw.strip():
            raise ValueError(f"targets[{idx}].path 必须是非空字符串")
        patterns_raw = t.get("patterns", ["*"])
        if isinstance(patterns_raw, str):
            patterns = [patterns_raw]
        elif isinstance(patterns_raw, list) and all(isinstance(p, str) for p in patterns_raw):
            patterns = [p for p in patterns_raw if p.strip()]
        else:
            raise ValueError(f"targets[{idx}].patterns 必须是字符串或字符串数组")
        older_than_hours = t.get("older_than_hours")
        older_than_days = t.get("older_than_days")
        hours: Optional[float] = None
        if older_than_hours is not None:
            try:
                hours = float(older_than_hours)
            except Exception as exc:
                raise ValueError(f"targets[{idx}].older_than_hours 必须是数字") from exc
        elif older_than_days is not None:
            try:
                hours = float(older_than_days) * 24.0
            except Exception as exc:
                raise ValueError(f"targets[{idx}].older_than_days 必须是数字") from exc

        recursive = bool(t.get("recursive", True))
        targets.append(Target(path=Path(path_raw), patterns=patterns, older_than_hours=hours, recursive=recursive))

    return targets


def _iter_matches(base: Path, pattern: str, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from base.rglob(pattern)
    else:
        yield from base.glob(pattern)


def _mtime_utc(path: Path) -> datetime:
    stat = path.stat()
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _should_delete(path: Path, now_utc: datetime, older_than_hours: Optional[float]) -> bool:
    if older_than_hours is None:
        return True
    cutoff = now_utc - timedelta(hours=float(older_than_hours))
    try:
        return _mtime_utc(path) < cutoff
    except Exception:
        return False


def _delete_path(path: Path) -> None:
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()


def cleanup_targets(
    *,
    targets: list[Target],
    now_utc: datetime,
    apply: bool,
    allow_outside_cwd: bool,
    delete_empty_dirs: bool,
    max_delete: int,
) -> int:
    cwd = _safe_resolve(Path.cwd())
    deleted_count = 0
    error_count = 0
    scanned_count = 0

    for target in targets:
        base = _safe_resolve(target.path)

        if _is_drive_root(base):
            LOGGER.error("拒绝清理磁盘根目录: %s", base)
            error_count += 1
            continue

        if not allow_outside_cwd:
            try:
                base.relative_to(cwd)
            except Exception:
                LOGGER.error("目标路径不在当前目录内（需要 --allow-outside-cwd 才允许）: %s", base)
                error_count += 1
                continue

        if not base.exists():
            LOGGER.warning("目标路径不存在，跳过: %s", base)
            continue

        LOGGER.info("开始清理: %s (patterns=%s, recursive=%s, older_than_hours=%s)", base, target.patterns, target.recursive, target.older_than_hours)

        for pattern in target.patterns:
            for p in _iter_matches(base, pattern, target.recursive):
                scanned_count += 1
                try:
                    if p.is_symlink():
                        continue
                    if p.is_dir():
                        continue
                    if not _should_delete(p, now_utc, target.older_than_hours):
                        continue
                except Exception as exc:
                    LOGGER.warning("检查失败，跳过: %s (%s)", p, exc)
                    continue

                if max_delete > 0 and deleted_count >= max_delete:
                    LOGGER.error("达到最大删除数量限制（max_delete=%s），停止", max_delete)
                    return 1

                if apply:
                    try:
                        _delete_path(p)
                        deleted_count += 1
                    except Exception as exc:
                        error_count += 1
                        LOGGER.warning("删除失败: %s (%s)", p, exc)
                else:
                    LOGGER.info("[dry-run] 将删除: %s", p)

        if delete_empty_dirs:
            # 从深到浅尝试删除空目录
            for d in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda x: len(str(x)), reverse=True):
                try:
                    if d.is_symlink():
                        continue
                    if any(d.iterdir()):
                        continue
                    if apply:
                        _delete_path(d)
                    else:
                        LOGGER.info("[dry-run] 将删除空目录: %s", d)
                except Exception:
                    continue

    LOGGER.info("清理完成: scanned=%s deleted=%s errors=%s", scanned_count, deleted_count, error_count)
    return 0 if error_count == 0 else 1


def cleanup_pycache(*, now_utc: datetime, apply: bool, max_delete: int) -> int:
    deleted_count = 0
    error_count = 0

    for path in sorted(Path.cwd().rglob("__pycache__"), key=lambda p: len(str(p)), reverse=True):
        if max_delete > 0 and deleted_count >= max_delete:
            LOGGER.error("达到最大删除数量限制（max_delete=%s），停止", max_delete)
            return 1
        try:
            if path.is_symlink():
                continue
            if apply:
                for child in path.rglob("*"):
                    try:
                        if child.is_file() and not child.is_symlink():
                            child.unlink()
                    except Exception:
                        pass
                for d in sorted((p for p in path.rglob("*") if p.is_dir()), key=lambda p: len(str(p)), reverse=True):
                    try:
                        d.rmdir()
                    except Exception:
                        pass
                path.rmdir()
                deleted_count += 1
            else:
                LOGGER.info("[dry-run] 将删除目录: %s", path)
        except Exception as exc:
            error_count += 1
            LOGGER.warning("清理 __pycache__ 失败: %s (%s)", path, exc)

    LOGGER.info("__pycache__ 清理完成: deleted=%s errors=%s", deleted_count, error_count)
    return 0 if error_count == 0 else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Daily cleanup script (safe by default).")
    parser.add_argument("--config", default=_env("CLEANUP_CONFIG", "cleanup_config.json"), help="JSON 配置文件路径")
    parser.add_argument("--apply", action="store_true", help="真正执行删除（默认 dry-run）")
    parser.add_argument("--allow-outside-cwd", action="store_true", help="允许清理当前目录之外的路径（更危险）")
    parser.add_argument("--delete-empty-dirs", action="store_true", help="尝试删除清理后产生的空目录")
    parser.add_argument("--max-delete", type=int, default=int(_env("CLEANUP_MAX_DELETE", "500") or "500"), help="最大删除数量，0 表示不限制")
    parser.add_argument("--pycache-only", action="store_true", help="仅清理 __pycache__（忽略配置文件）")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    now_utc = datetime.now(timezone.utc)

    if args.pycache_only:
        return cleanup_pycache(now_utc=now_utc, apply=args.apply, max_delete=args.max_delete)

    config_path = Path(args.config)
    targets: list[Target] = []
    if config_path.exists():
        try:
            targets = _load_config(config_path)
        except Exception as exc:
            LOGGER.error("%s", exc)
            return 2
    else:
        LOGGER.warning("未找到配置文件 %s，将仅清理当前目录下的 __pycache__（可用 --config 指定）", config_path)
        return cleanup_pycache(now_utc=now_utc, apply=args.apply, max_delete=args.max_delete)

    if not targets:
        LOGGER.error("配置文件 targets 为空：%s", _safe_resolve(config_path))
        return 2

    return cleanup_targets(
        targets=targets,
        now_utc=now_utc,
        apply=args.apply,
        allow_outside_cwd=args.allow_outside_cwd,
        delete_empty_dirs=args.delete_empty_dirs,
        max_delete=args.max_delete,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

