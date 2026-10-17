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
import aiofiles
import aiohttp
import config
from ..logging import LOGGER
from ..utils.cookies import youtube_cookie_file


async def save_file(pastebin_url, file_path=None):
    try:
        file_path = file_path or youtube_cookie_file()
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(pastebin_url) as response:
                response.raise_for_status()
                contents = await response.text()

        parent = os.path.dirname(file_path)
        os.makedirs(parent, mode=0o700, exist_ok=True)
        async with aiofiles.open(file_path, "w") as file:
            await file.write(contents)
        os.chmod(file_path, 0o600)
        return file_path
    except Exception:
        pass


async def save_cookies():
    if not config.COOKIES:
        LOGGER(__name__).info("No cookie source configured; skipping cookie download.")
        return None
    full_url = str(config.COOKIES)
    paste_id = full_url.split("/")[-1]
    pastebin_url = f"https://batbin.me/raw/{paste_id}"

    file_path = await save_file(pastebin_url)
    if file_path and await asyncio.to_thread(os.path.getsize, file_path) > 0:
        LOGGER(__name__).info(f"𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝘀𝗮𝘃𝗲𝗱 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝘁𝗼 {file_path}.")
    else:
        LOGGER(__name__).error("𝘍𝘢𝘪𝘭𝘦𝘥 𝘵𝘰 𝘴𝘢𝘷𝘦 𝘤𝘰𝘰𝘬𝘪𝘦𝘴 𝘰𝘳 𝘵𝘩𝘦 𝘧𝘪𝘭𝘦 𝘪𝘴 𝘦𝘮𝘱𝘵𝘺. 🥹")