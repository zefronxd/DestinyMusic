# -----------------------------------------------
# 🔸 DestinyMusic - Catbox Uploader Plugin (Fixed)
# -----------------------------------------------

import os
import asyncio
import aiofiles
import aiohttp
from aiohttp import payload
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from DestinyMusic import app


async def _file_chunks(file_path: str):
    async with aiofiles.open(file_path, "rb") as source:
        while chunk := await source.read(1024 * 1024):
            yield chunk


# =========================================
# 🔹 Upload Function (Async)
# =========================================
async def upload_to_catbox(file_path: str):
    url = "https://catbox.moe/user/api.php"

    try:
        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")
        data.add_field(
            "fileToUpload",
            payload.AsyncIterablePayload(
                _file_chunks(file_path),
                content_type="application/octet-stream",
            ),
            filename=os.path.basename(file_path),
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                text = await resp.text()

                if resp.status == 200 and "http" in text:
                    return True, text.strip()
                else:
                    return False, text

    except Exception as e:
        return False, str(e)


# =========================================
# 🔹 Command Handler
# =========================================
@app.on_message(filters.command(["tgm", "tm", "telegraph", "tl"]))
async def telegraph_uploader(client, message):

    if not message.reply_to_message:
        return await message.reply_text(
            "⚠️ Reply to a media file (photo/video/document)."
        )

    media = message.reply_to_message
    file_size = 0
    local_path = None

    # ---------------------------
    # Get file size
    # ---------------------------
    if media.photo:
        file_size = media.photo.file_size
    elif media.video:
        file_size = media.video.file_size
    elif media.document:
        file_size = media.document.file_size

    if file_size == 0:
        return await message.reply_text("❌ No downloadable media found.")

    if file_size > 200 * 1024 * 1024:
        return await message.reply_text("❌ File must be under 200MB.")

    msg = await message.reply("🔄 Processing...")

    # ---------------------------
    # Progress control
    # ---------------------------
    last_percent = 0

    async def progress(current, total):
        nonlocal last_percent
        percent = int(current * 100 / total)

        if percent - last_percent >= 10:
            last_percent = percent
            try:
                await msg.edit_text(f"📥 Downloading... {percent}%")
            except:
                pass

    try:
        # ---------------------------
        # Download
        # ---------------------------
        local_path = await media.download(progress=progress)

        if not local_path or not os.path.exists(local_path):
            return await msg.edit_text("❌ Download failed.")

        await msg.edit_text("📤 Uploading to Catbox...")

        # ---------------------------
        # Upload
        # ---------------------------
        success, result = await upload_to_catbox(local_path)

        if success:
            await message.reply_photo(
                local_path,
                caption=f"✨ {message.from_user.mention()} Your file is uploaded!",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔗 Open Link", url=result
                            )
                        ]
                    ]
                ),
            )
            await msg.delete()

        else:
            await msg.edit_text(f"❌ Upload failed!\n{result}")

    except Exception as e:
        await msg.edit_text(f"❌ Error:\n{e}")

    finally:
        # ---------------------------
        # Cleanup
        # ---------------------------
        try:
            if local_path and os.path.exists(local_path):
                await asyncio.to_thread(os.remove, local_path)
        except:
            pass
