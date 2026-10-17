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


import asyncio
import os
import time
from DestinyMusic.downloads import DOWNLOAD_SEMAPHORE
from typing import Union
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Voice,
)

import config
from DestinyMusic import app
from DestinyMusic.utils.formatters import (
    check_duration,
    convert_bytes,
    get_readable_time,
    seconds_to_min,
)


class TeleAPI:
    def __init__(self):
        self.chars_limit = 4096
        self.sleep = 5

    async def send_split_text(self, message, string):
        n = self.chars_limit
        out = [(string[i : i + n]) for i in range(0, len(string), n)]
        j = 0
        for x in out:
            if j <= 2:
                j += 1
                await message.reply_text(
                    x,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
        return True

    async def get_link(self, message):
        return message.link

    async def get_filename(self, file, audio: Union[bool, str] = None):
        try:
            file_name = file.file_name
            if file_name is None:
                file_name = "ᴛᴇʟᴇɢʀᴀᴍ ᴀᴜᴅɪᴏ"
        except:
            file_name = "ᴛᴇʟᴇɢʀᴀᴍ ᴀᴜᴅɪᴏ"
        return file_name

    async def get_duration(self, file):
        try:
            dur = seconds_to_min(file.duration)
        except:
            dur = "Unknown"
        return dur

    async def get_duration(self, filex, file_path):
        try:
            dur = seconds_to_min(filex.duration)
        except:
            try:
                dur = await asyncio.to_thread(check_duration, file_path)
                dur = seconds_to_min(dur)
            except:
                return "Unknown"
        return dur

    async def get_filepath(
        self,
        audio: Union[bool, str] = None,
        video: Union[bool, str] = None,
    ):
        if video:
            raise ValueError("Bot abhi audio-only hai.")
        if not audio:
            raise ValueError("An audio file is required.")
        try:
            extension = (
                audio.file_name.split(".")[-1]
                if not isinstance(audio, Voice)
                else "ogg"
            )
        except Exception:
            extension = "ogg"
        return os.path.join(
            os.path.realpath("downloads"),
            f"{audio.file_unique_id}.{extension}",
        )

    async def download(self, _, message, mystic, fname):
        async with DOWNLOAD_SEMAPHORE:
            return await self._download_unlimited(_, message, mystic, fname)

    async def _download_unlimited(self, _, message, mystic, fname):
        lower = [0, 8, 17, 38, 64, 77, 96]
        higher = [5, 10, 20, 40, 66, 80, 99]
        checker = [5, 10, 20, 40, 66, 80, 99]
        speed_counter = {}
        if os.path.exists(fname):
            return True

        async def down_load():
            async def progress(current, total):
                if current == total:
                    return
                current_time = time.time()
                start_time = speed_counter.get(message.id)
                check_time = current_time - start_time
                upl = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="ᴄᴀɴᴄᴇʟ",
                                callback_data="stop_downloading",
                            ),
                        ]
                    ]
                )
                percentage = current * 100 / total
                percentage = str(round(percentage, 2))
                speed = current / check_time
                eta = int((total - current) / speed)
                eta = get_readable_time(eta)
                if not eta:
                    eta = "0 sᴇᴄᴏɴᴅs"
                total_size = convert_bytes(total)
                completed_size = convert_bytes(current)
                speed = convert_bytes(speed)
                percentage = int((percentage.split("."))[0])
                for counter in range(7):
                    low = int(lower[counter])
                    high = int(higher[counter])
                    check = int(checker[counter])
                    if low < percentage <= high:
                        if high == check:
                            try:
                                await mystic.edit_text(
                                    text=_["tg_1"].format(
                                        app.mention,
                                        total_size,
                                        completed_size,
                                        percentage[:5],
                                        speed,
                                        eta,
                                    ),
                                    reply_markup=upl,
                                )
                                checker[counter] = 100
                            except:
                                pass

            speed_counter[message.id] = time.time()
            try:
                await app.download_media(
                    message.reply_to_message,
                    file_name=fname,
                    progress=progress,
                )
                try:
                    elapsed = get_readable_time(
                        int(int(time.time()) - int(speed_counter[message.id]))
                    )
                except:
                    elapsed = "0 sᴇᴄᴏɴᴅs"
                await mystic.edit_text(_["tg_2"].format(elapsed))
            except:
                await mystic.edit_text(_["tg_3"])

        task = asyncio.create_task(down_load())
        config.lyrical[mystic.id] = task
        await task
        verify = config.lyrical.get(mystic.id)
        if not verify:
            return False
        config.lyrical.pop(mystic.id)
        return True
