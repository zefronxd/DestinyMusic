"""Private storage location for yt-dlp cookies."""

import os


def youtube_cookie_file() -> str:
    configured_path = os.getenv("YOUTUBE_COOKIES_FILE")
    if configured_path:
        return os.path.abspath(os.path.expanduser(configured_path))
    return os.path.join(
        os.path.expanduser("~"),
        ".config",
        "destinymusic",
        "cookies.txt",
    )
