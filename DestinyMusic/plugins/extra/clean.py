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
from pathlib import Path
from pyrogram import filters
from DestinyMusic import app
from DestinyMusic.downloads import DOWNLOAD_SEMAPHORE
from DestinyMusic.misc import SUDOERS
from DestinyMusic.utils.stream.autoclear import queued_file_paths


def _delete_unqueued_downloads(protected):
    deleted = 0
    for folder in (Path.cwd() / "downloads", Path.cwd() / "cache"):
        try:
            if folder.is_symlink() or not folder.is_dir():
                continue
            root = folder.resolve()
            with os.scandir(root) as entries:
                for entry in entries:
                    try:
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        if entry.name.endswith(".part"):
                            continue
                        file_path = Path(entry.path).resolve()
                        if file_path.parent != root or str(file_path) in protected:
                            continue
                        file_path.unlink()
                        deleted += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return deleted


@app.on_message(filters.command("clean") & SUDOERS)
async def clean(_, message):
    A = await message.reply_text("ᴄʟᴇᴀɴɪɴɢ ᴛᴇᴍᴘ ᴅɪʀᴇᴄᴛᴏʀɪᴇs...")
    async with DOWNLOAD_SEMAPHORE:
        protected = queued_file_paths()
        deleted = (
            await asyncio.to_thread(_delete_unqueued_downloads, protected)
            if protected is not None
            else 0
        )
    await A.edit(f"ᴜɴǫᴜᴇᴜᴇᴅ ᴛᴇᴍᴘ ғɪʟᴇs ᴄʟᴇᴀɴᴇᴅ: {deleted}")
