# -----------------------------------------------
# 🔸 StrangerMusic Project
# 🔹 Developed & Maintained by: Shashank Shukla (https://github.com/itzshukla)
# 📅 Copyright © 2022 – All Rights Reserved
#
# 📖 License:
# This source code is open for educational and non-commercial use ONLY.
# You are required to retain this credit in all copies or substantial portions of this file.
# Commercial use, redistribution, or removal of this notice is strictly prohibited
# without prior written permission from the author.
#
# ❤️ Made with dedication and love by ItzShukla
# -----------------------------------------------
import asyncio
from datetime import datetime, timedelta
from typing import Union
from ntgcalls import ConnectionNotFound, TelegramServerError
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, LinkPreviewOptions
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession
import config
from DestinyMusic import LOGGER, YouTube, app
from DestinyMusic.misc import db
from DestinyMusic.utils.database import (
    add_active_chat,
    clear_chat_cache,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from DestinyMusic.utils.autoplay import append_autoplay_tracks
from DestinyMusic.core.pcm_stream import PCMStreamManager
from DestinyMusic.utils.exceptions import AssistantErr
from DestinyMusic.utils.inline.play import stream_markup
from DestinyMusic.utils.stream.autoclear import auto_clean
from DestinyMusic.utils.thumbnails import get_thumb as gen_thumb
from strings import get_string

autoend = {}
counter = {}
pcm_streams = PCMStreamManager()

async def _clear_(chat_id: int, delete_files: bool = True):
    tracks = db.pop(chat_id, []) or []
    for track in tracks:
        await auto_clean(track, delete=delete_files)
    autoend.pop(chat_id, None)
    counter.pop(chat_id, None)
    clear_chat_cache(chat_id)
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)

class Call(PyTgCalls):
    def __init__(self):
        PyTgCallsSession.notice_displayed = True

        self.userbot1 = Client(
            name="AarumiAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        self.one = PyTgCalls(self.userbot1, cache_duration=100)

        self.userbot2 = Client(
            name="AarumiAss2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
        )
        self.two = PyTgCalls(self.userbot2, cache_duration=100)

        self.userbot3 = Client(
            name="AarumiAss3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
        )
        self.three = PyTgCalls(self.userbot3, cache_duration=100)

        self.userbot4 = Client(
            name="AarumiAss4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
        )
        self.four = PyTgCalls(self.userbot4, cache_duration=100)

        self.userbot5 = Client(
            name="AarumiAss5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
        )
        self.five = PyTgCalls(self.userbot5, cache_duration=100)

    def _build_stream(self) -> types.MediaStream:
        return types.MediaStream(
            types.ExternalMedia.AUDIO,
            audio_parameters=types.AudioQuality.HIGH,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=types.MediaStream.Flags.IGNORE,
        )

    async def _play_on_assistant(
        self,
        client: PyTgCalls,
        chat_id: int,
        source: str,
        start_seconds: float = 0,
        handle_end: bool = True,
    ):
        def update_position(position: float):
            tracks = db.get(chat_id) or []
            if tracks and tracks[0].get("streamtype") != "video":
                tracks[0]["played"] = int(position)

        return await pcm_streams.start(
            client=client,
            chat_id=chat_id,
            source=source,
            stream=self._build_stream(),
            on_end=(
                (lambda error: self._pcm_stream_finished(client, chat_id, error))
                if handle_end
                else None
            ),
            on_progress=update_position,
            start_seconds=start_seconds,
        )

    async def _pcm_stream_finished(
        self, client: PyTgCalls, chat_id: int, error: Exception | None
    ):
        # join_call() returns before its caller appends the initial queue item.
        # Give that short hand-off time to finish before handling an early EOF.
        for _ in range(40):
            if db.get(chat_id):
                break
            await asyncio.sleep(0.05)
        if not db.get(chat_id):
            return
        if error is not None:
            LOGGER(__name__).error(
                "Audio playback failed in voice chat %s; advancing: %s",
                chat_id,
                error,
            )
            tracks = db.get(chat_id) or []
            if tracks:
                failed_track = tracks[0]
                if await get_loop(chat_id) != 0:
                    tracks.pop(0)
                    await auto_clean(failed_track)
                try:
                    await app.send_message(
                        failed_track["chat_id"],
                        "Audio playback failed; skipping to the next track.",
                    )
                except Exception:
                    LOGGER(__name__).warning(
                        "Could not notify chat %s about an audio playback error",
                        chat_id,
                    )
        await self.change_stream(client, chat_id)

    async def _skip_failed_track(
        self, client: PyTgCalls, chat_id: int, track: dict, error: Exception
    ):
        LOGGER(__name__).error(
            "Could not start audio track in voice chat %s; skipping: %s",
            chat_id,
            error,
        )
        try:
            await app.send_message(
                track["chat_id"],
                "Audio playback failed; skipping to the next track.",
            )
        except Exception:
            LOGGER(__name__).warning(
                "Could not notify chat %s about a failed audio track", chat_id
            )
        tracks = db.get(chat_id) or []
        if tracks and tracks[0] is track:
            await auto_clean(tracks.pop(0))
        return await self.change_stream(client, chat_id)

    async def pause_stream(self, chat_id: int):
        pcm_streams.pause(chat_id)

    async def resume_stream(self, chat_id: int):
        pcm_streams.resume(chat_id)

    async def stop_stream(self, chat_id: int):
        await pcm_streams.stop(chat_id)
        assistant = await group_assistant(self, chat_id)
        stopped = False
        try:
            await assistant.leave_call(chat_id, close=False)
            stopped = True
        except Exception:
            pass
        await _clear_(chat_id, delete_files=stopped)

    async def stop_stream_force(self, chat_id: int):
        await pcm_streams.stop(chat_id)
        stopped = False
        for string, client in [
            (config.STRING1, self.one),
            (config.STRING2, self.two),
            (config.STRING3, self.three),
            (config.STRING4, self.four),
            (config.STRING5, self.five),
        ]:
            if not string:
                continue
            try:
                await client.leave_call(chat_id, close=False)
                stopped = True
            except Exception:
                pass
        try:
            await _clear_(chat_id, delete_files=stopped)
        except Exception:
            pass

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        raise AssistantErr("Speed abhi available nahi hai.")

    async def force_stop_stream(self, chat_id: int):
        await pcm_streams.stop(chat_id)
        assistant = await group_assistant(self, chat_id)
        popped = None
        try:
            check = db.get(chat_id)
            if check:
                popped = check.pop(0)
        except Exception:
            pass
        stopped = False
        try:
            await assistant.leave_call(chat_id, close=False)
            stopped = True
        except Exception:
            pass
        if popped:
            await auto_clean(popped, delete=stopped)
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)

    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
        old_tracks: list[dict] | None = None,
    ):
        if video:
            raise AssistantErr("Bot abhi audio-only hai.")
        assistant = await group_assistant(self, chat_id)
        try:
            await self._play_on_assistant(assistant, chat_id, link)
        except Exception as error:
            for track in old_tracks or []:
                await auto_clean(track)
            tracks = db.get(chat_id) or []
            if tracks:
                await self._skip_failed_track(assistant, chat_id, tracks[0], error)
            raise AssistantErr("Audio playback failed; skipping to the next track.")
        for track in old_tracks or []:
            await auto_clean(track)

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        if str(mode).lower() == "video":
            raise AssistantErr("Bot abhi audio-only hai.")
        assistant = await group_assistant(self, chat_id)
        try:
            await self._play_on_assistant(
                assistant,
                chat_id,
                file_path,
                start_seconds=config.time_to_seconds(to_seek),
            )
        except Exception as error:
            tracks = db.get(chat_id) or []
            if tracks:
                await self._skip_failed_track(assistant, chat_id, tracks[0], error)
            raise AssistantErr("Audio playback failed; skipping to the next track.")

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOG_GROUP_ID)
        await self._play_on_assistant(
            assistant, config.LOG_GROUP_ID, link, handle_end=False
        )
        await asyncio.sleep(0.2)
        try:
            await pcm_streams.stop(config.LOG_GROUP_ID)
            await assistant.leave_call(config.LOG_GROUP_ID, close=False)
        except Exception:
            pass

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        if video:
            raise AssistantErr("Bot abhi audio-only hai.")
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = get_string(language)
        try:
            await self._play_on_assistant(assistant, chat_id, link)
        except exceptions.NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except exceptions.NoAudioSourceFound:
            raise AssistantErr(_["call_10"])
        except (ConnectionNotFound, TelegramServerError):
            raise AssistantErr(_["call_10"])
        except Exception:
            raise AssistantErr(_["call_10"])
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def change_stream(self, client: PyTgCalls, chat_id: int):
        check = db.get(chat_id) or []
        popped = None
        loop = await get_loop(chat_id)
        try:
            popped = None
            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            if popped:
                await auto_clean(popped)
            if not check:
                if popped:
                    try:
                        await append_autoplay_tracks(chat_id, popped)
                    except Exception as error:
                        LOGGER(__name__).warning(
                            f"Could not get autoplay recommendations for {chat_id}: {error}"
                        )
                check = db.get(chat_id) or []
                if not check:
                    await _clear_(chat_id)
                    return await client.leave_call(chat_id, close=False)
        except Exception:
            stopped = False
            try:
                await client.leave_call(chat_id, close=False)
                stopped = True
            except Exception:
                pass
            await _clear_(chat_id, delete_files=stopped)
            return
        while check and str(check[0].get("streamtype")) == "video":
            unsupported = check.pop(0)
            await auto_clean(unsupported)
            try:
                await app.send_message(
                    unsupported["chat_id"], "Bot abhi audio-only hai."
                )
            except Exception:
                LOGGER(__name__).warning(
                    "Could not notify chat %s about a rejected video track",
                    chat_id,
                )
        if not check:
            await _clear_(chat_id)
            return await client.leave_call(chat_id, close=False)
        queued = check[0]["file"]
        language = await get_lang(chat_id)
        _ = get_string(language)
        title = (check[0]["title"]).title()
        user = check[0]["by"]
        original_chat_id = check[0]["chat_id"]
        streamtype = check[0]["streamtype"]
        videoid = check[0]["vidid"]
        db[chat_id][0]["played"] = 0
        if str(streamtype) == "video":
            return await self._skip_failed_track(
                client, chat_id, check[0], AssistantErr("Bot abhi audio-only hai.")
            )

        source = videoid if "index_" in queued else queued
        if "live_" in queued or "vid_" in queued:
            mystic = await app.send_message(original_chat_id, _["call_7"])
            try:
                file_path, direct = await YouTube.download(
                    videoid, mystic, videoid=True
                )
                if not file_path:
                    raise ValueError("The audio download provider returned no file.")
            except Exception as error:
                try:
                    await mystic.delete()
                except Exception:
                    pass
                return await self._skip_failed_track(
                    client, chat_id, check[0], error
                )
            source = file_path
            check[0]["file"] = file_path
            if file_path not in config.autoclean:
                config.autoclean.append(file_path)
            try:
                await mystic.delete()
            except Exception:
                pass

        try:
            await self._play_on_assistant(client, chat_id, source)
        except Exception as error:
            return await self._skip_failed_track(client, chat_id, check[0], error)

        button = stream_markup(_, chat_id)
        if "index_" in queued:
            run = await app.send_photo(
                chat_id=original_chat_id,
                photo=config.STREAM_IMG_URL,
                caption=_["stream_2"].format(user),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        elif videoid == "telegram":
            run = await app.send_photo(
                chat_id=original_chat_id,
                photo=config.TELEGRAM_AUDIO_URL,
                caption=_["stream_1"].format(
                    config.SUPPORT_GROUP, title[:23], check[0]["dur"], user
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        elif videoid == "soundcloud":
            run = await app.send_photo(
                chat_id=original_chat_id,
                photo=config.SOUNCLOUD_IMG_URL,
                caption=_["stream_1"].format(
                    config.SUPPORT_GROUP, title[:23], check[0]["dur"], user
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        else:
            img = await gen_thumb(videoid)
            run = await app.send_photo(
                chat_id=original_chat_id,
                photo=img,
                caption=_["stream_1"].format(
                    f"https://t.me/{app.username}?start=info_{videoid}",
                    title[:23],
                    check[0]["dur"],
                    user,
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"

    async def ping(self):
        pings = []
        if config.STRING1:
            pings.append(self.one.ping)
        if config.STRING2:
            pings.append(self.two.ping)
        if config.STRING3:
            pings.append(self.three.ping)
        if config.STRING4:
            pings.append(self.four.ping)
        if config.STRING5:
            pings.append(self.five.ping)
        return str(round(sum(pings) / len(pings), 3)) if pings else "0"

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client...\n")
        if config.STRING1:
            await self.one.start()
        if config.STRING2:
            await self.two.start()
        if config.STRING3:
            await self.three.start()
        if config.STRING4:
            await self.four.start()
        if config.STRING5:
            await self.five.start()

    async def decorators(self):
        for string, client in [
            (config.STRING1, self.one),
            (config.STRING2, self.two),
            (config.STRING3, self.three),
            (config.STRING4, self.four),
            (config.STRING5, self.five),
        ]:
            if not string:
                continue
            @client.on_update()
            async def _update_handler(_, update: types.Update, _client=client):
                if isinstance(update, types.StreamEnded):
                    # PCM producer EOF calls change_stream directly. Handling
                    # PyTgCalls' external-stream end as well can advance twice.
                    return
                if isinstance(update, types.ChatUpdate) and update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop_stream(update.chat_id)

Aarumi = Call()
