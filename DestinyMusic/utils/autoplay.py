"""Persistent per-chat autoplay state and YouTube Music recommendations."""

import asyncio
import re

from ytmusicapi import YTMusic

import config
from DestinyMusic.core.mongo import mongodb
from DestinyMusic.logging import LOGGER
from DestinyMusic.misc import db
from DestinyMusic.utils.formatters import seconds_to_min, time_to_seconds
from DestinyMusic.utils.stream.queue import put_queue

logger = LOGGER(__name__)
autoplay_db = mongodb.autoplay

MAX_AUTOPLAY_TRACKS = 5
_state: dict[int, bool] = {}
_progress: dict[int, int] = {}
_locks: dict[int, asyncio.Lock] = {}
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def is_autoplay_enabled_sync(chat_id: int) -> bool:
    return _state.get(int(chat_id), False)


def autoplay_button_text(chat_id: int, strings: dict) -> str:
    key = "autoplay_on" if is_autoplay_enabled_sync(chat_id) else "autoplay_off"
    return strings[key]


def _chat_lock(chat_id: int) -> asyncio.Lock:
    return _locks.setdefault(int(chat_id), asyncio.Lock())


async def load_autoplay_cache() -> None:
    """Warm saved chat settings before the bot builds player keyboards."""
    try:
        async for document in autoplay_db.find({}):
            if "chat_id" not in document:
                continue
            chat_id = int(document["chat_id"])
            _state[chat_id] = bool(document.get("enabled", False))
            _progress[chat_id] = max(0, int(document.get("autoplay_played", 0)))
    except Exception as error:
        logger.warning(f"Could not preload autoplay settings: {error}")


async def get_autoplay(chat_id: int) -> bool:
    chat_id = int(chat_id)
    if chat_id not in _state:
        document = await autoplay_db.find_one({"chat_id": chat_id})
        _state[chat_id] = bool(document.get("enabled", False)) if document else False
        _progress[chat_id] = (
            max(0, int(document.get("autoplay_played", 0))) if document else 0
        )
    return _state[chat_id]


async def toggle_autoplay(chat_id: int) -> bool:
    chat_id = int(chat_id)
    async with _chat_lock(chat_id):
        enabled = not await get_autoplay(chat_id)
        await autoplay_db.update_one(
            {"chat_id": chat_id},
            {"$set": {"chat_id": chat_id, "enabled": enabled, "autoplay_played": 0}},
            upsert=True,
        )
        _state[chat_id] = enabled
        _progress[chat_id] = 0
        return enabled


def _fetch_recommendations(video_id: str, limit: int) -> list[dict]:
    response = YTMusic().get_watch_playlist(
        videoId=video_id,
        limit=limit,
        radio=True,
    )
    return response.get("tracks") or []


async def append_autoplay_tracks(chat_id: int, ended_track: dict) -> int:
    """Append up to five related YouTube tracks when the queue is empty."""
    chat_id = int(chat_id)
    async with _chat_lock(chat_id):
        if not await get_autoplay(chat_id):
            return 0

        played = _progress.get(chat_id, 0)
        remaining = MAX_AUTOPLAY_TRACKS - played
        if remaining <= 0:
            return 0

        video_id = str(ended_track.get("vidid") or "")
        if not _YOUTUBE_ID.fullmatch(video_id):
            return 0

        recommendations = await asyncio.to_thread(
            _fetch_recommendations, video_id, min(25, remaining * 3)
        )

        # A user may have queued a song while recommendations were loading.
        if db.get(chat_id):
            return 0

        original_chat_id = int(ended_track.get("chat_id", chat_id))
        added = 0
        seen = {video_id}
        for track in recommendations:
            if added >= remaining:
                break
            recommended_id = str(track.get("videoId") or "")
            if (
                not _YOUTUBE_ID.fullmatch(recommended_id)
                or recommended_id in seen
                or track.get("isAvailable") is False
            ):
                continue
            seen.add(recommended_id)

            duration = track.get("length") or track.get("duration")
            duration_seconds = track.get("duration_seconds")
            if not duration and duration_seconds is not None:
                duration = seconds_to_min(duration_seconds)
            if not duration:
                continue
            try:
                duration_seconds = time_to_seconds(duration)
            except (TypeError, ValueError):
                continue
            if duration_seconds <= 0 or duration_seconds > config.DURATION_LIMIT:
                continue

            title = str(track.get("title") or "").strip()
            if not title:
                continue
            artists = track.get("artists") or []
            artist_names = [artist.get("name") for artist in artists if artist.get("name")]
            if artist_names:
                title = f"{title} - {', '.join(artist_names)}"

            queued = await put_queue(
                chat_id,
                original_chat_id,
                f"vid_{recommended_id}",
                title,
                duration,
                "Autoplay",
                recommended_id,
                0,
                "audio",
            )
            if not queued:
                break
            added += 1

        if added:
            _progress[chat_id] = played + added
            await autoplay_db.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "chat_id": chat_id,
                        "enabled": True,
                        "autoplay_played": _progress[chat_id],
                    }
                },
                upsert=True,
            )
        return added
