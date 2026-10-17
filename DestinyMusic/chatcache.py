"""Small registry for in-memory state that belongs to a voice chat."""

_CHAT_CACHES = []


def register_chat_cache(cache):
    if cache not in _CHAT_CACHES:
        _CHAT_CACHES.append(cache)


def clear_chat_caches(chat_id):
    for cache in tuple(_CHAT_CACHES):
        for key in tuple(cache):
            if key == chat_id or (
                isinstance(key, tuple) and key and key[0] == chat_id
            ):
                cache.pop(key, None)
