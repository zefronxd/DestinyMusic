"""Audio-only PCM decoding and paced voice-chat streaming."""

from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import av
import numpy as np
from pytgcalls import types


SAMPLE_RATE = 48_000
CHANNELS = 2
SAMPLE_WIDTH = 2
FRAME_SECONDS = 0.01
FRAME_BYTES = int(SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_SECONDS)
QUEUE_SECONDS = 2.5
QUEUE_FRAMES = int(QUEUE_SECONDS / FRAME_SECONDS)

_EOF = object()
_LOGGER = logging.getLogger(__name__)


class PCMDecoder:
    """Decode one audio source into exact 10 ms, s16le stereo frames."""

    def __init__(self, source: str, start_seconds: float = 0):
        self.source = str(source)
        self.start_seconds = max(0.0, float(start_seconds))
        self.duration: float | None = None
        self._lock = threading.RLock()
        self._container = None
        self._audio_stream = None
        self._resampler = None
        self._frames = None
        self._pending = bytearray()
        self._seek_target: float | None = (
            self.start_seconds if self.start_seconds > 0 else None
        )
        self._eof = False
        self._flush_done = False
        self._closed = False

    def open(self) -> None:
        with self._lock:
            if self._container is not None:
                return
            container = av.open(self.source, mode="r", timeout=(5.0, 20.0))
            try:
                audio_stream = next(iter(container.streams.audio), None)
                if audio_stream is None:
                    raise ValueError("The source has no audio stream.")

                if audio_stream.duration and audio_stream.time_base:
                    self.duration = float(
                        audio_stream.duration * audio_stream.time_base
                    )
                elif container.duration:
                    self.duration = float(container.duration / av.time_base)

                self._container = container
                self._audio_stream = audio_stream
                self._resampler = av.AudioResampler(
                    format="s16", layout="stereo", rate=SAMPLE_RATE
                )
                if self.start_seconds > 0:
                    if audio_stream.time_base:
                        offset = int(
                            self.start_seconds / float(audio_stream.time_base)
                        )
                        container.seek(offset, stream=audio_stream, backward=True)
                    else:
                        container.seek(
                            int(self.start_seconds * av.time_base), backward=True
                        )
                    audio_stream.codec_context.flush_buffers()
                self._frames = iter(container.decode(audio_stream))
            except Exception:
                container.close()
                self._container = None
                raise

    def _append_resampled(self, frames) -> None:
        for frame in frames or ():
            data = frame.to_ndarray().astype(np.dtype("<i2"), copy=False).tobytes()
            if self._seek_target is not None:
                frame_time = frame.time
                if frame_time is not None:
                    frame_time = float(frame_time)
                    if frame_time + frame.samples / SAMPLE_RATE <= self._seek_target:
                        continue
                    trim_samples = max(
                        0, math.ceil((self._seek_target - frame_time) * SAMPLE_RATE)
                    )
                    data = data[min(trim_samples * CHANNELS * SAMPLE_WIDTH, len(data)) :]
                self._seek_target = None
            self._pending.extend(data)

    def read_chunk(self) -> bytes | None:
        """Return the next exact-size PCM frame, or None after decoder EOF."""
        with self._lock:
            if self._closed or self._container is None:
                raise RuntimeError("The PCM decoder is not open.")

            while len(self._pending) < FRAME_BYTES and not self._eof:
                try:
                    frame = next(self._frames)
                except StopIteration:
                    self._eof = True
                    if not self._flush_done:
                        self._flush_done = True
                        self._append_resampled(self._resampler.resample(None))
                    break
                self._append_resampled(self._resampler.resample(frame))

            if len(self._pending) >= FRAME_BYTES:
                chunk = bytes(self._pending[:FRAME_BYTES])
                del self._pending[:FRAME_BYTES]
                return chunk
            if self._pending:
                chunk = bytes(self._pending)
                self._pending.clear()
                return chunk.ljust(FRAME_BYTES, b"\0")
            return None

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._frames = None
            container = self._container
            self._container = None
            self._audio_stream = None
            self._resampler = None
            if container is not None:
                container.close()


@dataclass
class PCMPlayback:
    chat_id: int
    client: object
    decoder: PCMDecoder
    on_end: Callable[[Exception | None], Awaitable[None]] | None
    on_progress: Callable[[float], None] | None
    position_seconds: float
    queue: asyncio.Queue = field(
        default_factory=lambda: asyncio.Queue(maxsize=QUEUE_FRAMES)
    )
    resumed: asyncio.Event = field(default_factory=asyncio.Event)
    stopping: bool = False
    finished: bool = False
    producer_task: asyncio.Task | None = None
    consumer_task: asyncio.Task | None = None

    def __post_init__(self):
        self.resumed.set()


class PCMStreamManager:
    """Own one bounded decoder/producer/consumer pipeline per voice chat."""

    def __init__(self):
        self.sessions: dict[int, PCMPlayback] = {}
        self._finishing: set[int] = set()

    def is_active(self, chat_id: int) -> bool:
        return chat_id in self.sessions or chat_id in self._finishing

    async def start(
        self,
        client,
        chat_id: int,
        source: str,
        stream: types.MediaStream,
        on_end: Callable[[Exception | None], Awaitable[None]] | None = None,
        on_progress: Callable[[float], None] | None = None,
        start_seconds: float = 0,
    ) -> PCMPlayback:
        await self.stop(chat_id)
        decoder = PCMDecoder(source, start_seconds)
        try:
            await asyncio.to_thread(decoder.open)
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
        except Exception:
            _LOGGER.exception("Could not start PCM stream in voice chat %s", chat_id)
            try:
                await asyncio.to_thread(decoder.close)
            except Exception:
                _LOGGER.exception("Could not close failed decoder for chat %s", chat_id)
            raise

        session = PCMPlayback(
            chat_id=chat_id,
            client=client,
            decoder=decoder,
            on_end=on_end,
            on_progress=on_progress,
            position_seconds=max(0.0, float(start_seconds)),
        )
        self.sessions[chat_id] = session
        session.producer_task = asyncio.create_task(self._produce(session))
        session.consumer_task = asyncio.create_task(self._consume(session))
        return session

    async def _produce(self, session: PCMPlayback) -> None:
        try:
            while not session.stopping:
                chunk = await asyncio.to_thread(session.decoder.read_chunk)
                if chunk is None:
                    await session.queue.put(_EOF)
                    return
                await session.queue.put(chunk)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            _LOGGER.exception("PCM decode failed in voice chat %s", session.chat_id)
            await session.queue.put(error)

    async def _consume(self, session: PCMPlayback) -> None:
        error = None
        next_deadline = time.monotonic()
        try:
            while not session.stopping:
                await session.resumed.wait()
                delay = next_deadline - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                    await session.resumed.wait()

                item = await session.queue.get()
                await session.resumed.wait()
                if session.stopping:
                    break
                if item is _EOF:
                    break
                if isinstance(item, Exception):
                    error = item
                    break

                await session.client.send_frame(
                    session.chat_id, types.Device.MICROPHONE, item
                )
                session.position_seconds += FRAME_SECONDS
                if session.on_progress:
                    try:
                        session.on_progress(session.position_seconds)
                    except Exception:
                        _LOGGER.exception(
                            "Could not update playback position in voice chat %s",
                            session.chat_id,
                        )

                next_deadline += FRAME_SECONDS
                now = time.monotonic()
                if next_deadline < now:
                    next_deadline = now + FRAME_SECONDS
        except asyncio.CancelledError:
            raise
        except Exception as caught:
            error = caught
            _LOGGER.exception("PCM frame send failed in voice chat %s", session.chat_id)
        finally:
            producer = session.producer_task
            if (
                producer is not None
                and producer is not asyncio.current_task()
                and not producer.done()
            ):
                producer.cancel()
                await asyncio.gather(producer, return_exceptions=True)
            try:
                await asyncio.to_thread(session.decoder.close)
            except Exception:
                _LOGGER.exception(
                    "Could not close PCM decoder in voice chat %s", session.chat_id
                )
            session.finished = True
            if self.sessions.get(session.chat_id) is session:
                self.sessions.pop(session.chat_id, None)
            if not session.stopping and session.on_end:
                self._finishing.add(session.chat_id)
                try:
                    await session.on_end(error)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.exception(
                        "PCM completion handler failed in voice chat %s",
                        session.chat_id,
                    )
                finally:
                    self._finishing.discard(session.chat_id)

    def pause(self, chat_id: int) -> bool:
        session = self.sessions.get(chat_id)
        if session is None:
            return False
        session.resumed.clear()
        return True

    def resume(self, chat_id: int) -> bool:
        session = self.sessions.get(chat_id)
        if session is None:
            return False
        session.resumed.set()
        return True

    async def stop(self, chat_id: int) -> None:
        session = self.sessions.pop(chat_id, None)
        if session is None:
            return
        session.stopping = True
        session.resumed.set()
        current_task = asyncio.current_task()
        tasks = []
        for task in (session.producer_task, session.consumer_task):
            if task is not None and task is not current_task and not task.done():
                task.cancel()
                tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await asyncio.to_thread(session.decoder.close)
        except Exception:
            _LOGGER.exception("Could not close PCM decoder in voice chat %s", chat_id)
