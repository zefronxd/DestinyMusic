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


from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from DestinyMusic import app
from DestinyMusic.utils import AdminRightsCheck
from config import BANNED_USERS


@app.on_message(
    filters.command(["cspeed", "speed", "cslow", "slow", "playback", "cplayback"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def playback(cli, message: Message, _, chat_id):
    return await message.reply_text("Speed abhi available nahi hai.")


@app.on_callback_query(filters.regex("SpeedUP") & ~BANNED_USERS)
async def speed_unavailable(client, callback_query: CallbackQuery):
    return await callback_query.answer(
        "Speed abhi available nahi hai.", show_alert=True
    )
