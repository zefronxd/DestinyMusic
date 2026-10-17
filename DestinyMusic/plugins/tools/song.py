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
import re
import yt_dlp
from pykeyboard import InlineKeyboard
from pyrogram import enums, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    Message,
)

from config import BANNED_USERS, SONG_DOWNLOAD_DURATION, SONG_DOWNLOAD_DURATION_LIMIT
from DestinyMusic import YouTube, app
from DestinyMusic.utils.decorators.language import language, languageCB
from DestinyMusic.utils.cookies import youtube_cookie_file
from DestinyMusic.utils.formatters import convert_bytes
from DestinyMusic.utils.inline.song import song_markup

def _extract_song_info(url):
    options = {"quiet": True}
    cookie_file = youtube_cookie_file()
    if os.path.isfile(cookie_file):
        options["cookiefile"] = cookie_file
    with yt_dlp.YoutubeDL(options) as ytdl:
        return ytdl.extract_info(url, download=False)

@app.on_message(filters.command(["song"]) & filters.group & ~BANNED_USERS)
@language
async def song_commad_group(client, message: Message, _):

    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["SG_B_1"],
                    url=f"https://t.me/{app.username}?start=song",
                ),
            ]
        ]
    )

    await message.reply_text(_["song_1"], reply_markup=upl)

@app.on_message(filters.command(["song"]) & filters.private & ~BANNED_USERS)
@language
async def song_commad_private(client, message: Message, _):

    await message.delete()

    url = await YouTube.url(message)

    if url:

        if not await YouTube.exists(url):

            return await message.reply_text(_["song_5"])

        mystic = await message.reply_text(_["play_1"])

        (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        ) = await YouTube.details(url)

        if str(duration_min) == "None":

            return await mystic.edit_text(_["song_3"])

        if int(duration_sec) > SONG_DOWNLOAD_DURATION_LIMIT:

            return await mystic.edit_text(
                _["play_4"].format(SONG_DOWNLOAD_DURATION, duration_min)
            )

        buttons = song_markup(_, vidid)

        await mystic.delete()

        return await message.reply_photo(
            thumbnail,
            caption=_["song_4"].format(title),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    else:

        if len(message.command) < 2:

            return await message.reply_text(_["song_2"])

    mystic = await message.reply_text(_["play_1"])

    query = message.text.split(None, 1)[1]

    try:

        (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        ) = await YouTube.details(query)

    except:

        return await mystic.edit_text(_["play_3"])

    if str(duration_min) == "None":

        return await mystic.edit_text(_["song_3"])

    if int(duration_sec) > SONG_DOWNLOAD_DURATION_LIMIT:

        return await mystic.edit_text(
            _["play_6"].format(SONG_DOWNLOAD_DURATION, duration_min)
        )

    buttons = song_markup(_, vidid)

    await mystic.delete()

    return await message.reply_photo(
        thumbnail,
        caption=_["song_4"].format(title),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@app.on_callback_query(filters.regex(pattern=r"song_back") & ~BANNED_USERS)
@languageCB
async def songs_back_helper(client, CallbackQuery, _):

    callback_data = CallbackQuery.data.strip()

    callback_request = callback_data.split(None, 1)[1]

    stype, vidid = callback_request.split("|")

    buttons = song_markup(_, vidid)

    return await CallbackQuery.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(pattern=r"song_helper") & ~BANNED_USERS)
@languageCB
async def song_helper_cb(client, CallbackQuery, _):

    callback_data = CallbackQuery.data.strip()

    callback_request = callback_data.split(None, 1)[1]

    stype, vidid = callback_request.split("|")

    if stype != "audio":
        return await CallbackQuery.answer(
            "Bot abhi audio-only hai.", show_alert=True
        )

    try:

        await CallbackQuery.answer(_["song_6"], show_alert=True)

    except:

        pass

    if stype == "audio":

        try:

            formats_available, link = await YouTube.formats(vidid, True)

        except:

            return await CallbackQuery.edit_message_text(_["song_7"])

        keyboard = InlineKeyboard()

        done = []

        for x in formats_available:

            check = x["format"]

            if "audio" in check:

                if x["filesize"] is None:

                    continue

                form = x["format_note"].title()

                if form not in done:

                    done.append(form)

                else:

                    continue

                sz = convert_bytes(x["filesize"])

                fom = x["format_id"]

                keyboard.row(
                    InlineKeyboardButton(
                        text=f"{form} Quality Audio = {sz}",
                        callback_data=f"song_download {stype}|{fom}|{vidid}",
                    ),
                )

        keyboard.row(
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data=f"song_back {stype}|{vidid}",
            ),
            InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data=f"close"),
        )

        return await CallbackQuery.edit_message_reply_markup(reply_markup=keyboard)

    else:

        try:

            formats_available, link = await YouTube.formats(vidid, True)

        except Exception as e:

            print(e)

            return await CallbackQuery.edit_message_text(_["song_7"])

        keyboard = InlineKeyboard()

        done = [160, 133, 134, 135, 136, 137, 298, 299, 264, 304, 266]

        for x in formats_available:

            check = x["format"]

            if x["filesize"] is None:

                continue

            if int(x["format_id"]) not in done:

                continue

            sz = convert_bytes(x["filesize"])

            ap = check.split("-")[1]

            to = f"{ap} = {sz}"

            keyboard.row(
                InlineKeyboardButton(
                    text=to,
                    callback_data=f"song_download {stype}|{x['format_id']}|{vidid}",
                )
            )

        keyboard.row(
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data=f"song_back {stype}|{vidid}",
            ),
            InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data=f"close"),
        )

        return await CallbackQuery.edit_message_reply_markup(reply_markup=keyboard)

@app.on_callback_query(filters.regex(pattern=r"song_download") & ~BANNED_USERS)
@languageCB
async def song_download_cb(client, CallbackQuery, _):

    try:

        await CallbackQuery.answer("ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...")

    except:

        pass

    callback_data = CallbackQuery.data.strip()

    callback_request = callback_data.split(None, 1)[1]

    stype, format_id, vidid = callback_request.split("|")

    mystic = await CallbackQuery.edit_message_text(_["song_8"])
    if stype != "audio":
        return await mystic.edit_text("Bot abhi audio-only hai.")

    yturl = f"https://www.youtube.com/watch?v={vidid}"

    x = await asyncio.to_thread(_extract_song_info, yturl)

    title = (x["title"]).title()

    title = re.sub(r"\W+", " ", title)

    thumb_image_path = await CallbackQuery.message.download()

    duration = x["duration"]

    if stype == "audio":

        try:

            filename, direct = await YouTube.download(
                yturl,
                mystic,
                songaudio=True,
                format_id=format_id,
                title=title,
            )

        except Exception as e:

            return await mystic.edit_text(_["song_9"].format(e))

        med = InputMediaAudio(
            media=filename,
            caption=title,
            thumb=thumb_image_path,
            title=title,
            performer=x["uploader"],
        )

        await mystic.edit_text(_["song_11"])

        await app.send_chat_action(
            chat_id=CallbackQuery.message.chat.id,
            action=enums.ChatAction.UPLOAD_AUDIO,
        )

        try:

            await CallbackQuery.edit_message_media(media=med)

        except Exception as e:

            print(e)

            return await mystic.edit_text(_["song_10"])

        await asyncio.to_thread(os.remove, filename)