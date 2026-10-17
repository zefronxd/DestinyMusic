# -----------------------------------------------
# 🔸 DestinyMusic Project
# 🔹 Developed & Maintained by: Zefron (https://github.com/zefronxd)
# 📅 Copyright © 2025 – All Rights Reserved
#
# 📖 License:
# This source code is open for educational and non-commercial use ONLY.
# You are required to retain this credit in all copies or substantial portions of this file.
# Commercial use, redistribution, or removal of this notice is strictly prohibited
# without prior written permission from the author.
#
# ❤️ Made with dedication and love by Zefron
# -----------------------------------------------


import os
from config import autoclean
from DestinyMusic.misc import db


def queued_file_paths():
    try:
        paths = set()
        for tracks in db.values():
            for track in tracks or []:
                if not isinstance(track, dict):
                    continue
                for key in ("file", "speed_path"):
                    value = track.get(key)
                    if value and isinstance(value, (str, os.PathLike)):
                        paths.add(os.path.realpath(os.fspath(value)))
        return paths
    except Exception:
        return None


def _same_file(first, second):
    try:
        return os.path.realpath(os.fspath(first)) == os.path.realpath(os.fspath(second))
    except (TypeError, ValueError):
        return False


def _file_is_queued(file_path):
    paths = queued_file_paths()
    return paths is None or os.path.realpath(os.fspath(file_path)) in paths


async def auto_clean(popped, delete=True):
    try:
        paths = []
        for key in ("file", "speed_path"):
            path = popped.get(key) if isinstance(popped, dict) else None
            if path and path not in paths:
                paths.append(path)

        for rem in paths:
            for queued_file in list(autoclean):
                if _same_file(queued_file, rem):
                    autoclean.remove(queued_file)
                    break
            if not delete or any(_same_file(queued_file, rem) for queued_file in autoclean):
                continue
            if _file_is_queued(rem):
                continue
            try:
                if os.path.isfile(rem):
                    os.remove(rem)
            except OSError:
                pass
    except Exception:
        pass
