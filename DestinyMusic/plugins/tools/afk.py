import re
from html import escape

from pyrogram import filters
from pyrogram.enums import MessageEntityType, ParseMode

from config import BANNED_USERS, COMMAND_HANDLER
from DestinyMusic import app

AFK_USERS = {}
AFK_USERNAMES = {}


def _mention(user_id, name):
    return f'<a href="tg://user?id={user_id}">{escape(name or "User")}</a>'


def _clear_afk(user_id):
    afk = AFK_USERS.pop(user_id, None)
    if afk and afk["username"]:
        AFK_USERNAMES.pop(afk["username"], None)
    return afk


@app.on_message(
    filters.command(["afk", "bye"], prefixes=COMMAND_HANDLER)
    & filters.group
    & ~BANNED_USERS
)
async def set_afk(_, message):
    user = message.from_user
    if not user:
        return

    old_afk = AFK_USERS.get(user.id)
    if old_afk and old_afk["username"]:
        AFK_USERNAMES.pop(old_afk["username"], None)

    parts = (message.text or "").split(maxsplit=1)
    reason = parts[1].strip() if len(parts) > 1 else ""
    username = user.username.lower() if user.username else ""
    AFK_USERS[user.id] = {
        "name": user.first_name or "User",
        "reason": reason,
        "username": username,
    }
    if username:
        AFK_USERNAMES[username] = user.id

    suffix = f"\nReason: {escape(reason)}" if reason else ""
    await message.reply_text(
        f"{_mention(user.id, user.first_name)} is now AFK.{suffix}",
        parse_mode=ParseMode.HTML,
    )


@app.on_message(
    filters.group
    & filters.text
    & ~filters.command(["afk", "bye"], prefixes=COMMAND_HANDLER),
    group=1,
)
async def watch_afk(_, message):
    user = message.from_user
    if not user or user.is_self:
        return

    afk = _clear_afk(user.id)
    if afk:
        await message.reply_text(
            f"Welcome back, {_mention(user.id, user.first_name)}. Your AFK status is cleared.",
            parse_mode=ParseMode.HTML,
        )
        return

    targets = set()
    reply_user = message.reply_to_message.from_user if message.reply_to_message else None
    if reply_user:
        targets.add(reply_user.id)

    for entity in message.entities or []:
        if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
            targets.add(entity.user.id)

    text = message.text or ""
    for username in re.findall(r"(?<![\w@])@([A-Za-z0-9_]{5,32})", text):
        user_id = AFK_USERNAMES.get(username.lower())
        if user_id:
            targets.add(user_id)

    for user_id in targets:
        afk = AFK_USERS.get(user_id)
        if not afk:
            continue
        suffix = f"\nReason: {escape(afk['reason'])}" if afk["reason"] else ""
        await message.reply_text(
            f"{_mention(user_id, afk['name'])} is AFK.{suffix}",
            parse_mode=ParseMode.HTML,
        )
