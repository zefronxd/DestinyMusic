from pyrogram import filters
from pyrogram.types import Message

from DestinyMusic import app
from DestinyMusic.misc import SUDOERS


@app.on_message(filters.command(["vplaymode", "vplaytoggle"]) & SUDOERS)
async def vplay_mode(_, message: Message):
    return await message.reply_text("Bot abhi audio-only hai.")
