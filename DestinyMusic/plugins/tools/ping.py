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

from datetime import datetime
import random

from pyrogram import filters
from pyrogram.types import Message

from DestinyMusic import app
from DestinyMusic.core.call import Aarumi
from DestinyMusic.utils import bot_sys_stats
from DestinyMusic.utils.decorators.language import language
from DestinyMusic.utils.inline import supp_markup
from config import BANNED_USERS, PING_IMG_URL

PING_IMAGES = [
    "https://files.catbox.moe/fh7vw7.jpg",
    "https://files.catbox.moe/lckxh6.jpg",
    "https://files.catbox.moe/smteo6.jpg",
    "https://files.catbox.moe/7enu2i.jpg",
    "https://files.catbox.moe/n6hkvd.jpg",
    "https://files.catbox.moe/ej1p7t.jpg",
]


@app.on_message(filters.command(["ping", "alive"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()

    # single spoiler image 
    wait_msg = await message.reply_photo(
        photo=random.choice(PING_IMAGES),
        caption=_["ping_1"].format(app.mention),
        has_spoiler=True
    )

    # Stats
    pytgping = await Aarumi.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000

    # old msg dlt
    await wait_msg.delete()

    await message.reply_photo(
        photo=random.choice(PING_IMAGES),
        caption=_["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping),
        has_spoiler=True,
        reply_markup=supp_markup(_),
    )
