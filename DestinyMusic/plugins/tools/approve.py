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
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus
from pyrogram.types import ChatJoinRequest, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserAlreadyParticipant
from DestinyMusic import app
from DestinyMusic.core.mongo import mongodb
from DestinyMusic.misc import SUDOERS
from DestinyMusic.utils.keyboard import ikb
from DestinyMusic.utils.permissions import adminsOnly, member_permissions
from DestinyMusic.utils.database import get_assistant
from pyrogram.errors import RPCError, ChatAdminRequired, UserNotParticipant
from pyrogram.types import Message
from DestinyMusic.misc import SUDOERS
approvaldb = mongodb.autoapprove


def smallcap(text):
    trans_table = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢABCDEFGHIJKLMNOPQRSTUVWXYZ0𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
    )
    return text.translate(trans_table)


@app.on_message(filters.command("joinmode") & filters.group)
@adminsOnly("can_change_info")
async def approval_command(client, message):
    chat_id = message.chat.id
    chat = await approvaldb.find_one({"chat_id": chat_id})
    if chat:
        mode = chat.get("mode", "")
        if not mode:
            mode = "manual"
            await approvaldb.update_one(
                {"chat_id": chat_id},
                {"$set": {"mode": mode}},
                upsert=True,
            )
        if mode == "automatic":
            switch = "manual"
            mdbutton = "ᴀᴜᴛᴏᴍᴀᴛɪᴄ"
        else:
            switch = "automatic"
            mdbutton = "ᴍᴀɴɴᴜᴀʟ"
        buttons = {
            "Tᴜʀɴ ᴏғғ": "approval_off",
            f"{mdbutton}": f"approval_{switch}",
        }
        keyboard = ikb(buttons, 1)
        await message.reply(
            "**Aᴜᴛᴏᴀᴘᴘʀᴏᴠᴀʟ ғᴏʀ ᴛʜɪs ᴄʜᴀᴛ: Eɴᴀʙʟᴇᴅ.**", reply_markup=keyboard
        )
    else:
        buttons = {"Tᴜʀɴ ᴏɴ ": "approval_on"}
        keyboard = ikb(buttons, 1)
        await message.reply(
            "**Aᴜᴛᴏᴀᴘᴘʀᴏᴠᴀʟ ғᴏʀ ᴛʜɪs ᴄʜᴀᴛ: Dɪsᴀʙʟᴇᴅ.**", reply_markup=keyboard
        )


@app.on_callback_query(filters.regex("approval(.*)"))
async def approval_cb(client, cb):
    chat_id = cb.message.chat.id
    from_user = cb.from_user
    permissions = await member_permissions(chat_id, from_user.id)
    permission = "can_restrict_members"
    if permission not in permissions:
        if from_user.id not in SUDOERS:
            return await cb.answer(
                f"ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴘᴇʀᴍɪssɪᴏɴ.\n Permission: {permission}",
                show_alert=True,
            )
    command_parts = cb.data.split("_", 1)
    option = command_parts[1]
    if option == "off":
        await approvaldb.delete_one({"chat_id": chat_id})
        keyboard = ikb({"ᴛᴜʀɴ ᴏɴ": "approval_on"}, 1)
        return await cb.edit_message_text(
            "**Aᴜᴛᴏᴀᴘᴘʀᴏᴠᴀʟ ғᴏʀ ᴛʜɪs ᴄʜᴀᴛ: Dɪsᴀʙʟᴇᴅ.**",
            reply_markup=keyboard,
        )

    options = {
        "on": ("automatic", "manual"),
        "automatic": ("automatic", "manual"),
        "manual": ("manual", "automatic"),
    }
    if option not in options:
        return await cb.answer("Invalid approval option.", show_alert=True)
    mode, switch = options[option]
    await approvaldb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": mode}},
        upsert=True,
    )
    buttons = {
        "ᴛᴜʀɴ ᴏғғ": "approval_off",
        smallcap(mode): f"approval_{switch}",
    }
    keyboard = ikb(buttons, 1)
    await cb.edit_message_text(
        "**Aᴜᴛᴏᴀᴘᴘʀᴏᴠᴀʟ ғᴏʀ ᴛʜɪs ᴄʜᴀᴛ: Eɴᴀʙʟᴇᴅ.**", reply_markup=keyboard
    )

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

approval_tasks = {}

@app.on_message(filters.command("approveall") & filters.group)
@adminsOnly("can_invite_users")
async def approve_all(client, message):
    chat_id = message.chat.id
    assistant = await get_assistant(chat_id)
    member = await app.get_chat_member(chat_id, assistant.id)
    if member.status == ChatMemberStatus.ADMINISTRATOR:
        if not member.privileges.can_invite_users:
            return await message.reply_text("ɢɪᴠᴇ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ɪɴᴠɪᴛᴇ ᴜsᴇʀs ʀɪɢʜᴛ.")
    elif member.status != ChatMemberStatus.OWNER:
        try:
            await app.promote_chat_member(
                chat_id,
                assistant.id,
                privileges=ChatPrivileges(can_invite_users=True),
            )
        except Exception:
            return await message.reply_text(
                "ɢɪᴠᴇ ᴛʜᴇ ʙᴏᴛ ᴘʀᴏᴍᴏᴛᴇ ᴍᴇᴍʙᴇʀs ʀɪɢʜᴛ, ᴏʀ ᴍᴀᴋᴇ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴀɴ ᴀᴅᴍɪɴ."
            )
    pending_users = [
        request async for request in assistant.get_chat_join_requests(chat_id)
    ]
    if not pending_users:
        return await message.reply_text("ɴᴏ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs.")

    record = await approvaldb.find_one({"chat_id": chat_id})
    tracked_users = set(record.get("pending_users", [])) if record else set()
    cancel_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("ᴄᴀɴᴄᴇʟ ᴘʀᴏᴄᴇss", callback_data=f"cancel_approval:{chat_id}")]]
    )
    approval_tasks[chat_id] = True
    status = await message.reply_text(
        f"ᴀᴘᴘʀᴏᴠɪɴɢ {len(pending_users)} ᴘᴇɴᴅɪɴɢ ʀᴇǫᴜᴇsᴛs...",
        reply_markup=cancel_button,
    )
    approved = failed = 0
    for request in pending_users:
        if not approval_tasks.get(chat_id):
            break
        user_id = request.user.id
        try:
            await assistant.approve_chat_join_request(chat_id, int(user_id))
        except UserAlreadyParticipant:
            pass
        except Exception:
            failed += 1
            continue
        approved += 1
        if user_id in tracked_users:
            await approvaldb.update_one(
                {"chat_id": chat_id},
                {"$pull": {"pending_users": int(user_id)}},
            )

    cancelled = not approval_tasks.get(chat_id)
    approval_tasks.pop(chat_id, None)
    result = (
        f"ᴄᴀɴᴄᴇʟʟᴇᴅ: {approved} ᴀᴘᴘʀᴏᴠᴇᴅ."
        if cancelled
        else f"ᴅᴏɴᴇ: {approved} ᴀᴘᴘʀᴏᴠᴇᴅ, {failed} ғᴀɪʟᴇᴅ."
    )
    await status.edit_text(result)

@app.on_callback_query(filters.regex("cancel_approval"))
async def cancel_approval_callback(client, callback_query):
    chat_id = int(callback_query.data.split(":")[1])
    approval_tasks[chat_id] = False  # Cancel the approval process
    await callback_query.message.edit_text("ᴀᴘᴘʀᴏᴠᴀʟ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟᴇᴅ.")


@app.on_message(filters.command(["clearpending", "unapproveall"]) & filters.group)
@adminsOnly("can_restrict_members")
async def clear_pending_command(client, message):
    chat_id = message.chat.id
    result = await approvaldb.update_one(
        {"chat_id": chat_id},
        {"$set": {"pending_users": []}},
    )
    if result.modified_count > 0:
        await message.reply_text("ᴄʟᴇᴀʀᴇᴅ ᴘᴇɴᴅɪɴɢ ᴜsᴇʀs.")
    else:
        await message.reply_text("ɴᴏ ᴘᴇɴᴅɪɴɢ ᴜsᴇʀs ᴛᴏ ᴄʟᴇᴀʀ.")


@app.on_chat_join_request(filters.group)
async def accept(client, message: ChatJoinRequest):
    chat = message.chat
    user = message.from_user
    settings = await approvaldb.find_one({"chat_id": chat.id}) or {}
    mode = settings.get("mode")
    if mode == "automatic":
        return await app.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
    if mode != "manual":
        return

    is_new = not await approvaldb.count_documents(
        {"chat_id": chat.id, "pending_users": int(user.id)}
    )
    await approvaldb.update_one(
        {"chat_id": chat.id},
        {"$addToSet": {"pending_users": int(user.id)}},
        upsert=True,
    )
    if mode != "manual" or not is_new:
        return

    buttons = {
        "ᴀᴄᴄᴇᴘᴛ": f"manual_approve_{user.id}",
        "ᴅᴇᴄʟɪɴᴇ": f"manual_decline_{user.id}",
    }
    admin_data = [
        member
        async for member in app.get_chat_members(
            chat_id=chat.id,
            filter=ChatMembersFilter.ADMINISTRATORS,
        )
    ]
    text = f"**ᴜsᴇʀ: {user.mention} ʜᴀs sᴇɴᴛ ᴀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ɢʀᴏᴜᴘ.**"
    for admin in admin_data:
        if not admin.user.is_bot and not admin.user.is_deleted:
            text += f"[\u2063](tg://user?id={admin.user.id})"
    await app.send_message(chat.id, text, reply_markup=ikb(buttons, 2))


@app.on_callback_query(filters.regex("manual_(.*)"))
async def manual(app, cb):
    chat = cb.message.chat
    from_user = cb.from_user
    permissions = await member_permissions(chat.id, from_user.id)
    permission = "can_invite_users"
    if permission not in permissions:
        if from_user.id not in SUDOERS:
            return await cb.answer(
                f"ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴘᴇʀᴍɪssɪᴏɴ.\n ᴘᴇʀᴍɪssɪᴏɴ: {permission}",
                show_alert=True,
            )
    datas = cb.data.split("_", 2)
    dis = datas[1]
    id = datas[2]
    if dis == "approve":
        try:
            await app.approve_chat_join_request(chat_id=chat.id, user_id=id)
        except UserAlreadyParticipant:
            await cb.answer(
                "Usᴇʀ Is Aᴘᴘʀᴏᴠᴇᴅ ɪɴ Yᴏᴜʀ Gʀᴏᴜᴘ Bʏ AɴʏOɴᴇ",
                show_alert=True,
            )
            return await cb.message.delete()

    if dis == "decline":
        try:
            await app.decline_chat_join_request(chat_id=chat.id, user_id=id)
        except Exception as e:
            if "messages.HideChatJoinRequest" in str(e):
                await cb.answer(
                    "Usᴇʀ Is Aᴘᴘʀᴏᴠᴇᴅ ɪɴ Yᴏᴜʀ Gʀᴏᴜᴘ Bʏ AɴʏOɴᴇ",
                    show_alert=True,
                )

    await approvaldb.update_one(
        {"chat_id": chat.id},
        {"$pull": {"pending_users": int(id)}},
    )
    return await cb.message.delete()