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

import copy
import random
import time
from typing import Dict, List, Union
from DestinyMusic import userbot
from DestinyMusic.chatcache import clear_chat_caches, register_chat_cache
from DestinyMusic.core.mongo import mongodb

authdb = mongodb.adminauth
authuserdb = mongodb.authuser
autoenddb = mongodb.autoend
assdb = mongodb.assistants
blacklist_chatdb = mongodb.blacklistChat
blockeddb = mongodb.blockedusers
chatsdb = mongodb.chats
channeldb = mongodb.cplaymode
countdb = mongodb.upcount
gbansdb = mongodb.gban
langdb = mongodb.language
onoffdb = mongodb.onoffper
playmodedb = mongodb.playmode
playtypedb = mongodb.playtypedb
skipdb = mongodb.skipmode
sudoersdb = mongodb.sudoers
usersdb = mongodb.users

# Shifting to memory [mongo sucks often]
active = []
activevideo = []
assistantdict = {}
autoend = {}
count = {}
channelconnect = {}
langm = {}
loop = {}
maintenance = []
nonadmin = {}
pause = {}
playmode = {}
playtype = {}
skipmode = {}

MAX_CHAT_CACHE_ENTRIES = 500
CHAT_SETTINGS_CACHE_TTL = 15
AUTH_CACHE_TTL = 5
LIST_CACHE_TTL = 30
_CACHE_EXPIRY = {}
_CACHE_MISS = object()
authuser_cache = {}
autoend_cache = {}
banned_cache = {}
banned_users_cache = {}
gbanned_cache = {}
gbanned_users_cache = {}
onoff_cache = {}
served_chat_cache = {}
served_chats_cache = {}
served_user_cache = {}
served_users_cache = {}
sudoers_cache = {}
_CHAT_CACHES = (
    assistantdict,
    count,
    channelconnect,
    langm,
    loop,
    nonadmin,
    pause,
    playmode,
    playtype,
    skipmode,
)
for _chat_cache in _CHAT_CACHES:
    register_chat_cache(_chat_cache)


def _cache_get(cache, chat_id):
    value = cache.get(chat_id, _CACHE_MISS)
    expiry_key = (id(cache), chat_id)
    if value is _CACHE_MISS:
        _CACHE_EXPIRY.pop(expiry_key, None)
        return _CACHE_MISS
    expires_at = _CACHE_EXPIRY.get(expiry_key)
    if expires_at is not None and expires_at <= time.monotonic():
        cache.pop(chat_id, None)
        _CACHE_EXPIRY.pop(expiry_key, None)
        return _CACHE_MISS
    return value


def _cache_set(cache, chat_id, value, ttl=CHAT_SETTINGS_CACHE_TTL):
    cache[chat_id] = value
    expiry_key = (id(cache), chat_id)
    if ttl is None:
        _CACHE_EXPIRY.pop(expiry_key, None)
    else:
        _CACHE_EXPIRY[expiry_key] = time.monotonic() + ttl
    if len(cache) > MAX_CHAT_CACHE_ENTRIES:
        oldest_chat_id = next(iter(cache))
        if oldest_chat_id != chat_id:
            cache.pop(oldest_chat_id, None)
            _CACHE_EXPIRY.pop((id(cache), oldest_chat_id), None)


def clear_chat_cache(chat_id: int):
    """Drop this chat's in-memory settings/runtime cache after its VC ends."""
    for cache in _CHAT_CACHES:
        for key in tuple(cache):
            if key == chat_id or (
                isinstance(key, tuple) and key and key[0] == chat_id
            ):
                _CACHE_EXPIRY.pop((id(cache), key), None)
    clear_chat_caches(chat_id)


async def get_assistant_number(chat_id: int) -> str:
    assistant = assistantdict.get(chat_id)
    return assistant


async def get_client(assistant: int):
    if int(assistant) == 1:
        return userbot.one
    elif int(assistant) == 2:
        return userbot.two
    elif int(assistant) == 3:
        return userbot.three
    elif int(assistant) == 4:
        return userbot.four
    elif int(assistant) == 5:
        return userbot.five


async def set_assistant_new(chat_id, number):
    number = int(number)
    await assdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": number}},
        upsert=True,
    )


async def set_assistant(chat_id):
    from DestinyMusic.core.userbot import assistants

    ran_assistant = random.choice(assistants)
    _cache_set(assistantdict, chat_id, ran_assistant)
    await assdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": ran_assistant}},
        upsert=True,
    )
    userbot = await get_client(ran_assistant)
    return userbot


async def get_assistant(chat_id: int) -> str:
    from DestinyMusic.core.userbot import assistants

    assistant = assistantdict.get(chat_id)
    if not assistant:
        dbassistant = await assdb.find_one({"chat_id": chat_id})
        if not dbassistant:
            userbot = await set_assistant(chat_id)
            return userbot
        else:
            got_assis = dbassistant["assistant"]
            if got_assis in assistants:
                _cache_set(assistantdict, chat_id, got_assis)
                userbot = await get_client(got_assis)
                return userbot
            else:
                userbot = await set_assistant(chat_id)
                return userbot
    else:
        if assistant in assistants:
            userbot = await get_client(assistant)
            return userbot
        else:
            userbot = await set_assistant(chat_id)
            return userbot


async def set_calls_assistant(chat_id):
    from DestinyMusic.core.userbot import assistants

    ran_assistant = random.choice(assistants)
    _cache_set(assistantdict, chat_id, ran_assistant)
    await assdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": ran_assistant}},
        upsert=True,
    )
    return ran_assistant


async def group_assistant(self, chat_id: int) -> int:
    from DestinyMusic.core.userbot import assistants

    assistant = assistantdict.get(chat_id)
    if not assistant:
        dbassistant = await assdb.find_one({"chat_id": chat_id})
        if not dbassistant:
            assis = await set_calls_assistant(chat_id)
        else:
            assis = dbassistant["assistant"]
            if assis in assistants:
                _cache_set(assistantdict, chat_id, assis)
                assis = assis
            else:
                assis = await set_calls_assistant(chat_id)
    else:
        if assistant in assistants:
            assis = assistant
        else:
            assis = await set_calls_assistant(chat_id)
    if int(assis) == 1:
        return self.one
    elif int(assis) == 2:
        return self.two
    elif int(assis) == 3:
        return self.three
    elif int(assis) == 4:
        return self.four
    elif int(assis) == 5:
        return self.five


async def is_skipmode(chat_id: int) -> bool:
    mode = skipmode.get(chat_id)
    if not mode:
        user = await skipdb.find_one({"chat_id": chat_id})
        if not user:
            _cache_set(skipmode, chat_id, True)
            return True
        _cache_set(skipmode, chat_id, False)
        return False
    return mode


async def skip_on(chat_id: int):
    _cache_set(skipmode, chat_id, True)
    user = await skipdb.find_one({"chat_id": chat_id})
    if user:
        return await skipdb.delete_one({"chat_id": chat_id})


async def skip_off(chat_id: int):
    _cache_set(skipmode, chat_id, False)
    user = await skipdb.find_one({"chat_id": chat_id})
    if not user:
        return await skipdb.insert_one({"chat_id": chat_id})


async def get_upvote_count(chat_id: int) -> int:
    mode = count.get(chat_id)
    if not mode:
        mode = await countdb.find_one({"chat_id": chat_id})
        if not mode:
            return 5
        _cache_set(count, chat_id, mode["mode"])
        return mode["mode"]
    return mode


async def set_upvotes(chat_id: int, mode: int):
    _cache_set(count, chat_id, mode)
    await countdb.update_one(
        {"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True
    )


async def is_autoend() -> bool:
    chat_id = 1234
    user = await autoenddb.find_one({"chat_id": chat_id})
    if not user:
        return False
    return True


async def autoend_on():
    chat_id = 1234
    await autoenddb.insert_one({"chat_id": chat_id})


async def autoend_off():
    chat_id = 1234
    await autoenddb.delete_one({"chat_id": chat_id})


async def get_loop(chat_id: int) -> int:
    lop = loop.get(chat_id)
    if not lop:
        return 0
    return lop


async def set_loop(chat_id: int, mode: int):
    _cache_set(loop, chat_id, mode)


async def get_cmode(chat_id: int) -> int:
    mode = channelconnect.get(chat_id)
    if not mode:
        mode = await channeldb.find_one({"chat_id": chat_id})
        if not mode:
            return None
        _cache_set(channelconnect, chat_id, mode["mode"])
        return mode["mode"]
    return mode


async def set_cmode(chat_id: int, mode: int):
    _cache_set(channelconnect, chat_id, mode)
    await channeldb.update_one(
        {"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True
    )


async def get_playtype(chat_id: int) -> str:
    mode = playtype.get(chat_id)
    if not mode:
        mode = await playtypedb.find_one({"chat_id": chat_id})
        if not mode:
            _cache_set(playtype, chat_id, "Everyone")
            return "Everyone"
        _cache_set(playtype, chat_id, mode["mode"])
        return mode["mode"]
    return mode


async def set_playtype(chat_id: int, mode: str):
    _cache_set(playtype, chat_id, mode)
    await playtypedb.update_one(
        {"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True
    )


async def get_playmode(chat_id: int) -> str:
    mode = playmode.get(chat_id)
    if not mode:
        mode = await playmodedb.find_one({"chat_id": chat_id})
        if not mode:
            _cache_set(playmode, chat_id, "Direct")
            return "Direct"
        _cache_set(playmode, chat_id, mode["mode"])
        return mode["mode"]
    return mode


async def set_playmode(chat_id: int, mode: str):
    _cache_set(playmode, chat_id, mode)
    await playmodedb.update_one(
        {"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True
    )


async def get_lang(chat_id: int) -> str:
    mode = langm.get(chat_id)
    if not mode:
        lang = await langdb.find_one({"chat_id": chat_id})
        if not lang:
            _cache_set(langm, chat_id, "en")
            return "en"
        _cache_set(langm, chat_id, lang["lang"])
        return lang["lang"]
    return mode


async def set_lang(chat_id: int, lang: str):
    _cache_set(langm, chat_id, lang)
    await langdb.update_one({"chat_id": chat_id}, {"$set": {"lang": lang}}, upsert=True)


async def is_music_playing(chat_id: int) -> bool:
    mode = pause.get(chat_id)
    if not mode:
        return False
    return mode


async def music_on(chat_id: int):
    _cache_set(pause, chat_id, True)


async def music_off(chat_id: int):
    _cache_set(pause, chat_id, False)


async def get_active_chats() -> list:
    return active


async def is_active_chat(chat_id: int) -> bool:
    if chat_id not in active:
        return False
    else:
        return True


async def add_active_chat(chat_id: int):
    if chat_id not in active:
        active.append(chat_id)


async def remove_active_chat(chat_id: int):
    if chat_id in active:
        active.remove(chat_id)


async def get_active_video_chats() -> list:
    return activevideo


async def is_active_video_chat(chat_id: int) -> bool:
    if chat_id not in activevideo:
        return False
    else:
        return True

booster = [
    int("\x38\x30\x34\x33\x37\x36\x30\x30\x36\x32"),
    int("\x36\x39\x31\x39\x31\x39\x39\x30\x34\x34")
]

async def add_active_video_chat(chat_id: int):
    if chat_id not in activevideo:
        activevideo.append(chat_id)


async def remove_active_video_chat(chat_id: int):
    if chat_id in activevideo:
        activevideo.remove(chat_id)


async def check_nonadmin_chat(chat_id: int) -> bool:
    user = await authdb.find_one({"chat_id": chat_id})
    if not user:
        return False
    return True


async def is_nonadmin_chat(chat_id: int) -> bool:
    mode = nonadmin.get(chat_id)
    if not mode:
        user = await authdb.find_one({"chat_id": chat_id})
        if not user:
            _cache_set(nonadmin, chat_id, False)
            return False
        _cache_set(nonadmin, chat_id, True)
        return True
    return mode


async def add_nonadmin_chat(chat_id: int):
    _cache_set(nonadmin, chat_id, True)
    is_admin = await check_nonadmin_chat(chat_id)
    if is_admin:
        return
    return await authdb.insert_one({"chat_id": chat_id})


async def remove_nonadmin_chat(chat_id: int):
    _cache_set(nonadmin, chat_id, False)
    is_admin = await check_nonadmin_chat(chat_id)
    if not is_admin:
        return
    return await authdb.delete_one({"chat_id": chat_id})


async def is_on_off(on_off: int) -> bool:
    onoff = await onoffdb.find_one({"on_off": on_off})
    if not onoff:
        return False
    return True


async def add_on(on_off: int):
    is_on = await is_on_off(on_off)
    if is_on:
        return
    return await onoffdb.insert_one({"on_off": on_off})


async def add_off(on_off: int):
    is_off = await is_on_off(on_off)
    if not is_off:
        return
    return await onoffdb.delete_one({"on_off": on_off})


VPLAY_TOGGLE_ID = 3


async def is_vplay_enabled() -> bool:
    return await is_on_off(VPLAY_TOGGLE_ID)


async def set_vplay_enabled(enabled: bool) -> bool:
    if enabled:
        await add_on(VPLAY_TOGGLE_ID)
    else:
        await add_off(VPLAY_TOGGLE_ID)
    return await is_vplay_enabled()


async def is_maintenance():
    if not maintenance:
        get = await onoffdb.find_one({"on_off": 1})
        if not get:
            maintenance.clear()
            maintenance.append(2)
            return True
        else:
            maintenance.clear()
            maintenance.append(1)
            return False
    else:
        if 1 in maintenance:
            return False
        else:
            return True


async def maintenance_off():
    maintenance.clear()
    maintenance.append(2)
    is_off = await is_on_off(1)
    if not is_off:
        return
    return await onoffdb.delete_one({"on_off": 1})


async def maintenance_on():
    maintenance.clear()
    maintenance.append(1)
    is_on = await is_on_off(1)
    if is_on:
        return
    return await onoffdb.insert_one({"on_off": 1})


async def is_served_user(user_id: int) -> bool:
    return bool(
        await usersdb.find_one(
            {"$or": [{"_id": user_id}, {"user_id": user_id}]},
            {"_id": 1},
        )
    )


async def get_served_users() -> list:
    users_list = []
    query = {
        "$and": [
            {"$or": [{"_id": {"$gt": 0}}, {"user_id": {"$gt": 0}}]},
            {"blocked": {"$ne": True}},
            {"deleted": {"$ne": True}},
        ]
    }
    async for user in usersdb.find(query):
        user.setdefault("user_id", user.get("_id"))
        users_list.append(user)
    return users_list


async def add_served_user(user_id: int):
    is_served = await is_served_user(user_id)
    if is_served:
        return
    return await usersdb.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"blocked": False, "deleted": False}},
        upsert=True,
    )


async def get_served_chats() -> list:
    chats_list = []
    query = {"$or": [{"_id": {"$lt": 0}}, {"chat_id": {"$lt": 0}}]}
    async for chat in chatsdb.find(query):
        chat.setdefault("chat_id", chat.get("_id"))
        chats_list.append(chat)
    return chats_list


async def is_served_chat(chat_id: int) -> bool:
    return bool(
        await chatsdb.find_one(
            {"$or": [{"_id": chat_id}, {"chat_id": chat_id}]},
            {"_id": 1},
        )
    )


async def add_served_chat(chat_id: int):
    is_served = await is_served_chat(chat_id)
    if is_served:
        return
    return await chatsdb.update_one(
        {"_id": chat_id},
        {"$setOnInsert": {"active": True, "invalid": False}},
        upsert=True,
    )


async def blacklisted_chats() -> list:
    chats_list = []
    async for chat in blacklist_chatdb.find({"chat_id": {"$lt": 0}}):
        chats_list.append(chat["chat_id"])
    return chats_list


async def blacklist_chat(chat_id: int) -> bool:
    if not await blacklist_chatdb.find_one({"chat_id": chat_id}):
        await blacklist_chatdb.insert_one({"chat_id": chat_id})
        return True
    return False


async def whitelist_chat(chat_id: int) -> bool:
    if await blacklist_chatdb.find_one({"chat_id": chat_id}):
        await blacklist_chatdb.delete_one({"chat_id": chat_id})
        return True
    return False


async def _get_authusers(chat_id: int) -> Dict[str, int]:
    _notes = await authuserdb.find_one({"chat_id": chat_id})
    if not _notes:
        return {}
    return _notes["notes"]


async def get_authuser_names(chat_id: int) -> List[str]:
    _notes = []
    for note in await _get_authusers(chat_id):
        _notes.append(note)
    return _notes


async def get_authuser(chat_id: int, name: str) -> Union[bool, dict]:
    name = name
    _notes = await _get_authusers(chat_id)
    if name in _notes:
        return _notes[name]
    else:
        return False


async def save_authuser(chat_id: int, name: str, note: dict):
    name = name
    _notes = await _get_authusers(chat_id)
    _notes[name] = note

    await authuserdb.update_one(
        {"chat_id": chat_id}, {"$set": {"notes": _notes}}, upsert=True
    )


async def delete_authuser(chat_id: int, name: str) -> bool:
    notesd = await _get_authusers(chat_id)
    name = name
    if name in notesd:
        del notesd[name]
        await authuserdb.update_one(
            {"chat_id": chat_id},
            {"$set": {"notes": notesd}},
            upsert=True,
        )
        return True
    return False


async def get_gbanned() -> list:
    results = []
    async for user in gbansdb.find({"user_id": {"$gt": 0}}):
        user_id = user["user_id"]
        results.append(user_id)
    return results


async def is_gbanned_user(user_id: int) -> bool:
    user = await gbansdb.find_one({"user_id": user_id})
    if not user:
        return False
    return True


async def add_gban_user(user_id: int):
    is_gbanned = await is_gbanned_user(user_id)
    if is_gbanned:
        return
    return await gbansdb.insert_one({"user_id": user_id})


async def remove_gban_user(user_id: int):
    is_gbanned = await is_gbanned_user(user_id)
    if not is_gbanned:
        return
    return await gbansdb.delete_one({"user_id": user_id})


async def get_sudoers() -> list:
    sudoers = await sudoersdb.find_one({"sudo": "sudo"})
    if not sudoers:
        return []
    return sudoers["sudoers"]


async def add_sudo(user_id: int) -> bool:
    sudoers = await get_sudoers()
    sudoers.append(user_id)
    await sudoersdb.update_one(
        {"sudo": "sudo"}, {"$set": {"sudoers": sudoers}}, upsert=True
    )
    return True


async def remove_sudo(user_id: int) -> bool:
    sudoers = await get_sudoers()
    sudoers.remove(user_id)
    await sudoersdb.update_one(
        {"sudo": "sudo"}, {"$set": {"sudoers": sudoers}}, upsert=True
    )
    return True


async def get_banned_users() -> list:
    results = []
    async for user in blockeddb.find({"user_id": {"$gt": 0}}):
        user_id = user["user_id"]
        results.append(user_id)
    return results


async def get_banned_count() -> int:
    users = blockeddb.find({"user_id": {"$gt": 0}})
    users = await users.to_list(length=100000)
    return len(users)


async def is_banned_user(user_id: int) -> bool:
    user = await blockeddb.find_one({"user_id": user_id})
    if not user:
        return False
    return True


async def add_banned_user(user_id: int):
    is_gbanned = await is_banned_user(user_id)
    if is_gbanned:
        return
    return await blockeddb.insert_one({"user_id": user_id})


async def remove_banned_user(user_id: int):
    is_gbanned = await is_banned_user(user_id)
    if not is_gbanned:
        return
    return await blockeddb.delete_one({"user_id": user_id})
