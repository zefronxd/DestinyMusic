"""Small resource watchdog for the bot's own download and thumbnail folders."""

import asyncio
import gc
import math
import os
import time
from pathlib import Path

from DestinyMusic.misc import db

try:
    import psutil
except Exception as error:
    psutil = None
    _PSUTIL_IMPORT_ERROR = error


def _env_number(name: str, default: int | float, cast):
    try:
        value = cast(os.getenv(name, str(default)))
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


WATCHDOG_THRESHOLD = _env_number("RESOURCE_WATCHDOG_THRESHOLD", 70, float)
WATCHDOG_INTERVAL = max(
    1, int(_env_number("RESOURCE_WATCHDOG_INTERVAL", 30, int))
)
WATCHDOG_MIN_FILE_AGE = max(
    0, int(_env_number("RESOURCE_WATCHDOG_MIN_FILE_AGE", 600, int))
)
MEMORY_LIMIT_MB = max(1, int(_env_number("MEMORY_LIMIT_MB", 512, int)))

BOT_ROOT = Path.cwd().resolve()
BOT_FOLDERS = (BOT_ROOT / "downloads", BOT_ROOT / "cache")


def _queued_file_paths() -> set[Path] | None:
    """Return media paths used by the active track and every queued track."""
    try:
        protected = set()
        for tracks in db.values():
            for track in tracks or []:
                if not isinstance(track, dict):
                    continue
                for key in ("file", "speed_path"):
                    value = track.get(key)
                    if not value or not isinstance(value, (str, os.PathLike)):
                        continue
                    path = Path(value)
                    if not path.is_absolute():
                        path = BOT_ROOT / path
                    protected.add(path.resolve())
        return protected
    except Exception as error:
        print(f"[ResourceWatchdog] Queue check failed; skipping cleanup: {error}")
        return None


def _delete_stale_files() -> int:
    """Delete old regular files only from the bot's downloads and cache folders."""
    protected = _queued_file_paths()
    if protected is None:
        return 0

    deleted = 0
    now = time.time()
    for folder in BOT_FOLDERS:
        try:
            if folder.is_symlink() or not folder.is_dir():
                continue
            safe_folder = folder.resolve()
            with os.scandir(safe_folder) as entries:
                for entry in entries:
                    try:
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        if entry.name.endswith(".part"):
                            continue
                        path = Path(entry.path).resolve()
                        if path.parent != safe_folder or path in protected:
                            continue
                        if now - entry.stat(follow_symlinks=False).st_mtime < WATCHDOG_MIN_FILE_AGE:
                            continue
                        path.unlink()
                        deleted += 1
                    except Exception:
                        continue
        except Exception:
            continue
    return deleted


async def resource_watchdog() -> None:
    """Check resource usage every 30 seconds and clean only safe, stale files."""
    while True:
        try:
            await asyncio.sleep(WATCHDOG_INTERVAL)
            if psutil is None:
                raise RuntimeError(f"psutil is unavailable: {_PSUTIL_IMPORT_ERROR}")
            if "DYNO" in os.environ:
                rss_bytes = psutil.Process().memory_info().rss
                ram_percent = rss_bytes / (MEMORY_LIMIT_MB * 1024 * 1024) * 100
            else:
                ram_percent = psutil.virtual_memory().percent

            cpu_percent = await asyncio.to_thread(psutil.cpu_percent, 1)
            disk_percent = psutil.disk_usage(str(BOT_ROOT)).percent

            if max(ram_percent, cpu_percent, disk_percent) >= WATCHDOG_THRESHOLD:
                try:
                    gc.collect()
                except Exception:
                    pass
                deleted = _delete_stale_files()
                print(
                    f"[ResourceWatchdog] RAM={ram_percent:.1f}% "
                    f"CPU={cpu_percent:.1f}% DISK={disk_percent:.1f}% "
                    f"deleted={deleted} file(s)"
                )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"[ResourceWatchdog] Check failed: {error}")
