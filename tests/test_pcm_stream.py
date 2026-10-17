import asyncio
import os
import tempfile
import unittest
import wave
from unittest.mock import patch

from DestinyMusic.core.pcm_stream import FRAME_BYTES, PCMDecoder, PCMStreamManager


def make_silent_wav(path: str, duration_seconds: float) -> None:
    sample_count = int(48_000 * duration_seconds)
    with wave.open(path, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(b"\0\0\0\0" * sample_count)


class FakeClient:
    def __init__(self, fail_on_frame: int | None = None):
        self.fail_on_frame = fail_on_frame
        self.frames: list[bytes] = []

    async def play(self, **kwargs):
        return None

    async def send_frame(self, chat_id, device, frame):
        self.frames.append(frame)
        if self.fail_on_frame == len(self.frames):
            raise RuntimeError("synthetic send_frame failure")


class PCMStreamTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.tempdir.name, "synthetic.wav")
        make_silent_wav(self.source, 5)

    async def asyncTearDown(self):
        self.tempdir.cleanup()

    async def test_decoder_returns_fixed_size_frames_through_eof(self):
        decoder = PCMDecoder(self.source)
        await asyncio.to_thread(decoder.open)
        try:
            frames = []
            while (frame := await asyncio.to_thread(decoder.read_chunk)) is not None:
                frames.append(frame)
        finally:
            await asyncio.to_thread(decoder.close)

        self.assertEqual(len(frames), 500)
        self.assertTrue(all(len(frame) == FRAME_BYTES == 1920 for frame in frames))

    async def test_decode_failure_reaches_completion_callback(self):
        manager = PCMStreamManager()
        client = FakeClient()
        finished = asyncio.Event()
        errors = []

        async def on_end(error):
            errors.append(error)
            finished.set()

        with patch.object(
            PCMDecoder, "read_chunk", side_effect=ValueError("synthetic decode failure")
        ):
            session = await manager.start(
                client=client,
                chat_id=12346,
                source=self.source,
                stream=None,
                on_end=on_end,
            )
            await asyncio.wait_for(finished.wait(), timeout=3)
            await asyncio.wait_for(session.consumer_task, timeout=1)

        self.assertEqual(client.frames, [])
        self.assertIsInstance(errors[0], ValueError)
        self.assertFalse(manager.is_active(12346))

    async def test_send_failure_cancels_producer_and_notifies_end(self):
        manager = PCMStreamManager()
        client = FakeClient(fail_on_frame=1)
        finished = asyncio.Event()
        errors = []

        async def on_end(error):
            errors.append(error)
            finished.set()

        session = await manager.start(
            client=client,
            chat_id=12345,
            source=self.source,
            stream=None,
            on_end=on_end,
        )
        await asyncio.wait_for(finished.wait(), timeout=3)
        await asyncio.wait_for(session.consumer_task, timeout=1)

        self.assertEqual(len(client.frames), 1)
        self.assertIsInstance(errors[0], RuntimeError)
        self.assertTrue(session.producer_task.cancelled())
        self.assertFalse(manager.is_active(12345))
