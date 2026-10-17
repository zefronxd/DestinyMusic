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


import logging

from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultPhoto,
)
from youtubesearchpython.__future__ import VideosSearch

from DestinyMusic import app
from DestinyMusic.utils.inlinequery import answer
from config import BANNED_USERS


LOGGER = logging.getLogger(__name__)


@app.on_inline_query(~BANNED_USERS)
async def inline_query_handler(client, query):
    try:
        text = query.query.strip().lower()
        if not text:
            await client.answer_inline_query(query.id, results=answer, cache_time=10)
            return

        search = VideosSearch(text, limit=20)
        response = await search.next()
        results = response.get("result", []) if isinstance(response, dict) else []
        answers = []

        for item in results[:15]:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            link = item.get("link")
            thumbnails = item.get("thumbnails") or []
            thumbnail = (
                thumbnails[0].get("url")
                if thumbnails and isinstance(thumbnails[0], dict)
                else None
            )
            if not title or not link or not thumbnail:
                continue

            title = str(title).title()
            duration = item.get("duration") or "Unknown"
            view_count = item.get("viewCount") or {}
            views = view_count.get("short", "Unknown") if isinstance(view_count, dict) else "Unknown"
            channel_info = item.get("channel") or {}
            channellink = channel_info.get("link") if isinstance(channel_info, dict) else None
            channel = channel_info.get("name", "Unknown") if isinstance(channel_info, dict) else "Unknown"
            published = item.get("publishedTime") or "Unknown"
            thumbnail = thumbnail.split("?")[0]
            description = f"{views} | {duration} ᴍɪɴᴜᴛᴇs | {channel}  | {published}"
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="ʏᴏᴜᴛᴜʙᴇ 🎄",
                            url=link,
                        )
                    ],
                ]
            )
            searched_text = f"""
❄ <b>ᴛɪᴛʟᴇ :</b> <a href={link}>{title}</a>

⏳ <b>ᴅᴜʀᴀᴛɪᴏɴ :</b> {duration} ᴍɪɴᴜᴛᴇs
👀 <b>ᴠɪᴇᴡs :</b> <code>{views}</code>
🎥 <b>ᴄʜᴀɴɴᴇʟ :</b> {f'<a href={channellink}>{channel}</a>' if channellink else channel}
⏰ <b>ᴘᴜʙʟɪsʜᴇᴅ ᴏɴ :</b> {published}


<u><b>➻ ɪɴʟɪɴᴇ sᴇᴀʀᴄʜ ᴍᴏᴅᴇ ʙʏ {app.name}</b></u>"""
            answers.append(
                InlineQueryResultPhoto(
                    photo_url=thumbnail,
                    title=title,
                    thumb_url=thumbnail,
                    description=description,
                    caption=searched_text,
                    reply_markup=buttons,
                )
            )

        return await client.answer_inline_query(query.id, results=answers)
    except Exception:
        LOGGER.exception("Inline YouTube search failed")
        try:
            return await client.answer_inline_query(query.id, results=[], cache_time=0)
        except Exception:
            LOGGER.exception("Failed to return an empty inline-query response")
