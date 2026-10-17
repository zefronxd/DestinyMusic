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
import sys

if sys.platform != "win32":
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import importlib
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall
import config
from DestinyMusic import LOGGER, app, userbot
from DestinyMusic.core.call import Aarumi
from DestinyMusic.core.mongo import verify_mongo_connection
from DestinyMusic.misc import sudo
from DestinyMusic.plugins import ALL_MODULES
from DestinyMusic.utils.database import get_banned_users, get_gbanned
from DestinyMusic.utils.autoplay import load_autoplay_cache
from DestinyMusic.utils.watchdog import resource_watchdog
from config import BANNED_USERS


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()
    await verify_mongo_connection()
    await sudo()
    await load_autoplay_cache()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module("DestinyMusic.plugins" + all_module)
    LOGGER("DestinyMusic.plugins").info("sᴜᴄᴄᴇssғᴜʟʟʏ ɪᴍᴘᴏʀᴛᴇᴅ ᴀʟʟ ᴍᴏᴅᴜʟᴇs...")
    await userbot.start()
    await Aarumi.start()
    try:
        await Aarumi.stream_call("https://te.legra.ph/file/39b302c93da5c457a87e3.mp4")
    except NoActiveGroupCall:
        LOGGER("DestinyMusic").error(
            "ʙsᴅᴋ ᴠᴄ ᴛᴏ ᴏɴ ᴋᴀʀʟᴇ  ʟᴏɢ ɢʀᴏᴜᴘ\ᴄʜᴀɴɴᴇʟ ᴋɪ.\n\n ᴏɴ ᴋᴀʀᴋᴇ ᴀᴀ ᴛᴀʙ ᴛᴀᴋ ʙᴏᴛ ʙᴀɴᴅ ᴋᴀʀ ʀʜᴀ ʜᴏᴏɴ..."
        )
        exit()
    except:
        pass
    await Aarumi.decorators()
    watchdog_task = asyncio.create_task(resource_watchdog())
    LOGGER("DestinyMusic").info(
        "Music bot started successfully. Follow updates: https://t.me/destiny_bots"
    )
    await idle()
    watchdog_task.cancel()
    try:
        await watchdog_task
    except asyncio.CancelledError:
        pass
    await app.stop()
    await userbot.stop()
    LOGGER("DestinyMusic").info("ᴍᴀᴀ ᴄʜᴜᴅᴀ ᴍᴀɪɴ ʙᴏᴛ ʙᴀɴᴅ ᴋᴀʀ ʀʜᴀ Zᴇғʀᴏɴ Mᴜsɪᴄ Bᴏᴛ...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())