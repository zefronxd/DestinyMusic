---
name: PCM producer cleanup
description: Lifecycle rule for the bounded PCM producer/consumer pipeline.
---

When a PCM consumer exits, cancel and await its producer before closing the decoder. The producer may be waiting on a full bounded queue or decoding in a worker thread after `send_frame` fails.

**Why:** Advancing the queue without stopping the failed session can leave a producer task blocked indefinitely and retain its decoder resources.

**How to apply:** Preserve this cleanup in any changes to `PCMStreamManager` error, EOF, pause, or stop handling.
