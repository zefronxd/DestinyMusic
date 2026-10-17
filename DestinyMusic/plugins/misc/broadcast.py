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
import re
from datetime import datetime, timezone
from uuid import uuid4

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait

from DestinyMusic import LOGGER, app
from DestinyMusic.core.mongo import mongodb
from DestinyMusic.misc import SUDOERS
from DestinyMusic.utils.database import (
    get_active_chats,
    get_authuser_names,
    get_client,
    get_served_chats,
    get_served_users,
)
from DestinyMusic.utils.decorators.language import language
from DestinyMusic.utils.formatters import alpha_to_int
from config import adminlist

IS_BROADCASTING = False
broadcast_messages = mongodb.broadcast_messages
BROADCAST_FLAG_PATTERN = re.compile(
    r"(?<!\S)(-pinloud|-pin|-nobot|-assistant|-useronly|-user)(?!\S)"
)
BROADCAST_HISTORY_BATCH_SIZE = 100


def _parse_broadcast_command(text):
    if not text:
        return set(), ""

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return set(), ""

    first_line, line_separator, remaining_lines = parts[1].partition("\n")
    flags = set(BROADCAST_FLAG_PATTERN.findall(first_line))
    first_line = BROADCAST_FLAG_PATTERN.sub("", first_line).strip()
    query = f"{first_line}{line_separator}{remaining_lines}".strip()
    return flags, query


def _sent_message_ids(sent_messages):
    if sent_messages is None:
        return []
    messages = (
        sent_messages
        if isinstance(sent_messages, (list, tuple))
        else [sent_messages]
    )
    return [
        int(sent_message.id)
        for sent_message in messages
        if getattr(sent_message, "id", None) is not None
    ]


async def _flush_broadcast_history(broadcast_id, pending_records):
    if not pending_records:
        return True

    batch = [
        {**record, "broadcast_id": broadcast_id}
        for record in pending_records
    ]
    try:
        await broadcast_messages.insert_many(batch, ordered=False)
        await broadcast_messages.update_one(
            {"_id": "last", "broadcast_id": broadcast_id},
            {"$inc": {"message_count": len(batch)}},
        )
    except Exception as error:
        LOGGER(__name__).error(
            "Could not save broadcast deletion history (%s).",
            type(error).__name__,
        )
        pending_records.clear()
        return False

    pending_records.clear()
    return True


async def _delete_broadcast_message(client, chat_id, message_id):
    try:
        await client.delete_messages(chat_id, message_id)
        return True
    except FloodWait as fw:
        if fw.value > 200:
            return False
        await asyncio.sleep(fw.value + 1)
        try:
            await client.delete_messages(chat_id, message_id)
            return True
        except Exception:
            return False
    except Exception:
        return False


@app.on_message(filters.command("broadcast") & SUDOERS)
@language
async def broadcast_message(client, message, _):
    global IS_BROADCASTING
    command_text = message.text or message.caption or ""
    flag_set, query = _parse_broadcast_command(command_text)
    source_message = message.reply_to_message
    if not source_message and not query:
        return await message.reply_text(_["broad_2"])
    if IS_BROADCASTING:
        return await message.reply_text("A broadcast is already running.")

    chats = []
    users = []
    if "-nobot" not in flag_set and "-useronly" not in flag_set:
        chats = [
            int(chat["chat_id"])
            for chat in await get_served_chats()
        ]
    if "-user" in flag_set or "-useronly" in flag_set:
        users = [
            int(user["user_id"])
            for user in await get_served_users()
        ]

    assistant_numbers = []
    if "-assistant" in flag_set and "-useronly" not in flag_set:
        from DestinyMusic.core.userbot import assistants

        assistant_numbers = list(assistants)
    if not chats and not users and not assistant_numbers:
        return await message.reply_text("❌ No recipients found for this broadcast.")

    IS_BROADCASTING = True
    broadcast_id = uuid4().hex
    pending_records = []
    history_failed = False
    pin_count = 0
    group_count = 0
    user_count = 0

    try:
        try:
            await broadcast_messages.update_one(
                {"_id": "last"},
                {
                    "$set": {
                        "broadcast_id": broadcast_id,
                        "status": "in_progress",
                        "message_count": 0,
                        "created_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
        except Exception as error:
            LOGGER(__name__).error(
                "Could not start broadcast history (%s).",
                type(error).__name__,
            )
            return await message.reply_text(
                "Broadcast was not sent because deletion history could not be saved."
            )

        await message.reply_text(_["broad_1"])
        pin_mode = (
            "loud"
            if "-pinloud" in flag_set
            else "silent"
            if "-pin" in flag_set
            else None
        )

        for recipient_type, recipients in (("chats", chats), ("users", users)):
            recipient_count = 0
            for chat_id in recipients:
                try:
                    sent_message = (
                        await app.forward_messages(
                            chat_id, source_message.chat.id, source_message.id
                        )
                        if source_message
                        else await app.send_message(chat_id, text=query)
                    )
                    for message_id in _sent_message_ids(sent_message):
                        pending_records.append(
                            {
                                "recipient_type": recipient_type,
                                "target_id": chat_id,
                                "message_id": message_id,
                            }
                        )
                    if len(pending_records) >= BROADCAST_HISTORY_BATCH_SIZE:
                        if not await _flush_broadcast_history(
                            broadcast_id, pending_records
                        ):
                            history_failed = True

                    if recipient_type == "chats" and pin_mode and sent_message:
                        pin_message = (
                            sent_message[0]
                            if isinstance(sent_message, (list, tuple))
                            else sent_message
                        )
                        try:
                            await pin_message.pin(
                                disable_notification=(pin_mode == "silent")
                            )
                            pin_count += 1
                        except Exception:
                            pass

                    recipient_count += 1
                    await asyncio.sleep(0.2)
                except FloodWait as fw:
                    if fw.value <= 200:
                        await asyncio.sleep(fw.value + 1)
                except Exception:
                    continue

            if recipient_type == "chats":
                group_count = recipient_count
            else:
                user_count = recipient_count

        if chats:
            try:
                await message.reply_text(
                    _["broad_3"].format(group_count, pin_count)
                )
            except Exception:
                pass
        if users:
            try:
                await message.reply_text(_["broad_4"].format(user_count))
            except Exception:
                pass

        if assistant_numbers:
            assistant_status = await message.reply_text(_["broad_5"])
            assistant_summary = _["broad_6"]
            for assistant_number in assistant_numbers:
                assistant_count = 0
                assistant = await get_client(assistant_number)
                async for dialog in assistant.get_dialogs():
                    chat_id = dialog.chat.id
                    try:
                        sent_message = (
                            await assistant.forward_messages(
                                chat_id,
                                source_message.chat.id,
                                source_message.id,
                            )
                            if source_message
                            else await assistant.send_message(
                                chat_id, text=query
                            )
                        )
                        for message_id in _sent_message_ids(sent_message):
                            pending_records.append(
                                {
                                    "recipient_type": "assistant",
                                    "target_id": chat_id,
                                    "message_id": message_id,
                                    "assistant_number": assistant_number,
                                }
                            )
                        if len(pending_records) >= BROADCAST_HISTORY_BATCH_SIZE:
                            if not await _flush_broadcast_history(
                                broadcast_id, pending_records
                            ):
                                history_failed = True
                        assistant_count += 1
                        await asyncio.sleep(3)
                    except FloodWait as fw:
                        if fw.value <= 200:
                            await asyncio.sleep(fw.value + 1)
                    except Exception:
                        continue
                assistant_summary += _["broad_7"].format(
                    assistant_number, assistant_count
                )
            try:
                await assistant_status.edit_text(assistant_summary)
            except Exception:
                pass

        if not await _flush_broadcast_history(broadcast_id, pending_records):
            history_failed = True
        stored_count = await broadcast_messages.count_documents(
            {"broadcast_id": broadcast_id}
        )
        await broadcast_messages.update_one(
            {"_id": "last", "broadcast_id": broadcast_id},
            {
                "$set": {
                    "status": "history_incomplete" if history_failed else "complete",
                    "message_count": stored_count,
                }
            },
        )
        await broadcast_messages.delete_many(
            {"broadcast_id": {"$exists": True, "$ne": broadcast_id}}
        )
        if history_failed:
            await message.reply_text(
                "⚠️ Broadcast sent, but some deletion history could not be saved."
            )
    finally:
        if pending_records:
            try:
                await _flush_broadcast_history(broadcast_id, pending_records)
                stored_count = await broadcast_messages.count_documents(
                    {"broadcast_id": broadcast_id}
                )
                await broadcast_messages.update_one(
                    {"_id": "last", "broadcast_id": broadcast_id},
                    {
                        "$set": {
                            "status": "history_incomplete",
                            "message_count": stored_count,
                        }
                    },
                )
            except Exception as error:
                LOGGER(__name__).error(
                    "Could not finalize broadcast history (%s).",
                    type(error).__name__,
                )
        IS_BROADCASTING = False


@app.on_message(filters.command("dbroadcast") & SUDOERS)
@language
async def delete_last_broadcast(client, message, _):
    global IS_BROADCASTING
    if IS_BROADCASTING:
        return await message.reply_text("A broadcast is already running.")

    IS_BROADCASTING = True
    try:
        last_broadcast = await broadcast_messages.find_one({"_id": "last"})
        broadcast_id = (
            last_broadcast.get("broadcast_id") if last_broadcast else None
        )
        if not broadcast_id:
            return await message.reply_text(
                "There are no saved messages from the last broadcast."
            )

        total = await broadcast_messages.count_documents(
            {"broadcast_id": broadcast_id}
        )
        if not total:
            return await message.reply_text(
                "There are no saved messages from the last broadcast."
            )

        status = await message.reply_text(
            "Deleting messages from the last broadcast..."
        )
        deleted = {"chats": 0, "users": 0, "assistant": 0}
        successful_ids = []
        assistant_clients = {}

        async for record in broadcast_messages.find(
            {"broadcast_id": broadcast_id}
        ):
            recipient_type = record["recipient_type"]
            target_id = int(record["target_id"])
            message_id = int(record["message_id"])
            target_client = app
            if recipient_type == "assistant":
                assistant_number = int(record["assistant_number"])
                if assistant_number not in assistant_clients:
                    assistant_clients[assistant_number] = await get_client(
                        assistant_number
                    )
                target_client = assistant_clients[assistant_number]

            removed = await _delete_broadcast_message(
                target_client, target_id, message_id
            )
            if removed:
                deleted[recipient_type] += 1
                successful_ids.append(record["_id"])
                if len(successful_ids) >= BROADCAST_HISTORY_BATCH_SIZE:
                    await broadcast_messages.delete_many(
                        {"_id": {"$in": successful_ids}}
                    )
                    successful_ids.clear()
            await asyncio.sleep(0.1)

        if successful_ids:
            await broadcast_messages.delete_many(
                {"_id": {"$in": successful_ids}}
            )

        remaining = await broadcast_messages.count_documents(
            {"broadcast_id": broadcast_id}
        )
        await broadcast_messages.update_one(
            {"_id": "last", "broadcast_id": broadcast_id},
            {
                "$set": {
                    "status": "partial" if remaining else "deleted",
                    "message_count": remaining,
                }
            },
        )
        try:
            await status.edit_text(
                "Last broadcast cleanup finished.\n\n"
                f"Groups: {deleted['chats']}\n"
                f"Users: {deleted['users']}\n"
                f"Assistant dialogs: {deleted['assistant']}\n"
                f"Messages still pending: {remaining}"
            )
        except Exception:
            pass
    except Exception as error:
        LOGGER(__name__).error(
            "Could not delete the last broadcast (%s).",
            type(error).__name__,
        )
        await message.reply_text(
            "Broadcast deletion stopped. Run /dbroadcast again to retry remaining messages."
        )
    finally:
        IS_BROADCASTING = False


async def auto_clean():
    while not await asyncio.sleep(10):
        try:
            served_chats = await get_active_chats()
            for chat_id in served_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(
                        chat_id, filter=ChatMembersFilter.ADMINISTRATORS
                    ):
                        if user.privileges.can_manage_video_chats:
                            adminlist[chat_id].append(user.user.id)
                    authusers = await get_authuser_names(chat_id)
                    for user in authusers:
                        user_id = await alpha_to_int(user)
                        adminlist[chat_id].append(user_id)
        except:
            continue


asyncio.create_task(auto_clean())
