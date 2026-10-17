"""Shared concurrency limit for media downloads."""

import asyncio
import os

_default_limit = 2 if "DYNO" in os.environ else 4
try:
    MAX_CONCURRENT_DOWNLOADS = max(
        1, int(os.getenv("MAX_CONCURRENT_DOWNLOADS", str(_default_limit)))
    )
except ValueError:
    MAX_CONCURRENT_DOWNLOADS = _default_limit

DOWNLOAD_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
