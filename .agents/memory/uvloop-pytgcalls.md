---
name: uvloop and PyTgCalls startup
description: Startup ordering needed when this bot uses uvloop with PyTgCalls.
---

When uvloop is enabled, install its event-loop policy and set a current loop before importing PyTgCalls. Keep that same loop for the bot's `run_until_complete` startup.

**Why:** PyTgCalls' sync wrapper calls `asyncio.get_event_loop()` during import and captures the current loop. With uvloop installed but no current loop set, startup fails on Python 3.12.

**How to apply:** Preserve the loop setup at the top of the entry point before imports that load PyTgCalls; do not switch to a different loop after those imports.
