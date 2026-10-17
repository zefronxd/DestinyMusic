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

import math
import random

from pyrogram.types import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup
from DestinyMusic.utils.autoplay import autoplay_button_text, is_autoplay_enabled_sync
from DestinyMusic.utils.formatters import time_to_seconds

try:
    from pyrogram.types import KeyboardButtonStyle
except ImportError:
    KeyboardButtonStyle = None


def styled_button(text, callback_data, color=None):
    """Create a randomly colored button if the library supports button styles."""

    colors = ["primary", "success", "danger"]
    color = color or random.choice(colors)

    if KeyboardButtonStyle is None:
        return InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
        )

    styles = {
        "primary": KeyboardButtonStyle(bg_primary=True),
        "success": KeyboardButtonStyle(bg_success=True),
        "danger": KeyboardButtonStyle(bg_danger=True),
    }

    try:
        return InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
            style=styles[color],
        )
    except (TypeError, ValueError):
        return InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
        )


def track_markup(_, videoid, user_id, channel, fplay):
    return [
        [
            styled_button(
                _["P_B_1"],
                f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
            ),
        ],
        [
            styled_button(
                _["CLOSE_BUTTON"],
                f"forceclose {videoid}|{user_id}",
            ),
        ],
    ]


def stream_markup_timer(_, chat_id, played, dur):
    played_sec = time_to_seconds(played)
    duration_sec = time_to_seconds(dur)

    percentage = (
        (played_sec / duration_sec) * 100
        if duration_sec > 0
        else 0
    )
    umm = max(0, min(100, math.floor(percentage)))

    if umm <= 10:
        bar = "◉—————————"
    elif umm < 20:
        bar = "—◉————————"
    elif umm < 30:
        bar = "——◉———————"
    elif umm < 40:
        bar = "———◉——————"
    elif umm < 50:
        bar = "————◉—————"
    elif umm < 60:
        bar = "—————◉————"
    elif umm < 70:
        bar = "——————◉———"
    elif umm < 80:
        bar = "———————◉——"
    elif umm < 95:
        bar = "————————◉—"
    else:
        bar = "—————————◉"

    return [
        [
            styled_button(
                f"{played} {bar} {dur}",
                "GetTimer",
            ),
        ],
        [
            styled_button("▷", f"ADMIN Resume|{chat_id}"),
            styled_button("II", f"ADMIN Pause|{chat_id}"),
            styled_button("↻", f"ADMIN Replay|{chat_id}"),
            styled_button("‣‣I", f"ADMIN Skip|{chat_id}"),
            styled_button("▢", f"ADMIN Stop|{chat_id}"),
        ],
        [
            styled_button("< - 𝟤𝟢 s", "seek_backward_20"),
            styled_button("sᴛᴀᴛᴜs", "api_status"),
            styled_button("𝟤𝟢 s + >", "seek_forward_20"),
        ],
        [
            styled_button(
                autoplay_button_text(chat_id, _),
                f"ADMIN AutoPlay|{chat_id}",
                "success" if is_autoplay_enabled_sync(chat_id) else "danger",
            ),
            styled_button(_["CLOSE_BUTTON"], "close"),
        ],
    ]


def stream_markup(_, chat_id):
    return [
        [
            styled_button("▷", f"ADMIN Resume|{chat_id}"),
            styled_button("II", f"ADMIN Pause|{chat_id}"),
            styled_button("↻", f"ADMIN Replay|{chat_id}"),
            styled_button("‣‣I", f"ADMIN Skip|{chat_id}"),
            styled_button("▢", f"ADMIN Stop|{chat_id}"),
        ],
        [
            styled_button("< - 𝟤𝟢 s", "seek_backward_20"),
            styled_button("sᴛᴀᴛᴜs", "api_status"),
            styled_button("𝟤𝟢 s + >", "seek_forward_20"),
        ],
        [
            styled_button(
                autoplay_button_text(chat_id, _),
                f"ADMIN AutoPlay|{chat_id}",
                "success" if is_autoplay_enabled_sync(chat_id) else "danger",
            ),
            styled_button(_["CLOSE_BUTTON"], "close"),
        ],
    ]


def update_autoplay_markup(_, chat_id, current_markup):
    """Change only the autoplay button and keep timer/player rows intact."""
    if not current_markup:
        return InlineKeyboardMarkup(stream_markup(_, chat_id))

    callback_data = f"ADMIN AutoPlay|{chat_id}"
    enabled = is_autoplay_enabled_sync(chat_id)
    updated_rows = []
    found = False
    for row in current_markup.inline_keyboard:
        updated_row = []
        for button in row:
            if button.callback_data == callback_data:
                button = styled_button(
                    autoplay_button_text(chat_id, _),
                    callback_data,
                    "success" if enabled else "danger",
                )
                found = True
            updated_row.append(button)
        updated_rows.append(updated_row)

    if not found:
        return InlineKeyboardMarkup(stream_markup(_, chat_id))
    return InlineKeyboardMarkup(updated_rows)


def playlist_markup(_, videoid, user_id, ptype, channel, fplay):
    return [
        [
            styled_button(
                _["P_B_1"],
                f"AarumiPlaylists {videoid}|{user_id}|{ptype}|a|{channel}|{fplay}",
            ),
        ],
        [
            styled_button(
                _["CLOSE_BUTTON"],
                f"forceclose {videoid}|{user_id}",
            ),
        ],
    ]


def livestream_markup(_, videoid, user_id, mode, channel, fplay):
    return [
        [
            styled_button(
                _["P_B_3"],
                f"LiveStream {videoid}|{user_id}|{mode}|{channel}|{fplay}",
            ),
        ],
        [
            styled_button(
                _["CLOSE_BUTTON"],
                f"forceclose {videoid}|{user_id}",
            ),
        ],
    ]


def slider_markup(_, videoid, user_id, query, query_type, channel, fplay):
    query = str(query)[:20]

    return [
        [
            styled_button(
                _["P_B_1"],
                f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
            ),
        ],
        [
            styled_button(
                "◁",
                f"slider B|{query_type}|{query}|{user_id}|{channel}|{fplay}",
            ),
            styled_button(
                _["CLOSE_BUTTON"],
                f"forceclose {query}|{user_id}",
            ),
            styled_button(
                "▷",
                f"slider F|{query_type}|{query}|{user_id}|{channel}|{fplay}",
            ),
        ],
    ]
