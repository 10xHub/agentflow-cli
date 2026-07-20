"""
FakeRealtimeClient — a keyless, network-free stand-in for a realtime provider.

Implements the ``agentflow.core.realtime.base.RealtimeClient`` protocol so a
``LiveAgent`` can run a full ``/v1/graph/live`` session with NO Gemini key and NO
network. It scripts a tiny conversation: a greeting on connect, and a canned reply
(input-transcript echo + output-transcript + a short audio tone + turn_complete)
whenever the client sends text or ends a push-to-talk turn.

Wired into graph/live.py via ``LiveAgent(..., realtime_client_factory=...)`` so the
playground's Live page can be exercised end-to-end. Swap for a real
``GeminiLiveClient`` (drop the factory + set an API key) for actual audio.
"""

from __future__ import annotations

import array
import asyncio
import math
from itertools import cycle
from typing import Any

from agentflow.core.realtime.base import (
    AudioDeltaEvent,
    OutputTranscriptEvent,
    RealtimeConfig,
    TurnCompleteEvent,
)
from agentflow.core.realtime.base import (
    InputTranscriptEvent as _InputTranscript,
)


OUTPUT_SAMPLE_RATE = 24000


# A short, quiet 440 Hz tone (PCM16 mono @ 24 kHz) reused as the agent's "audio".
# Precomputed once so responding is cheap and deterministic.
def _make_tone(freq: int = 440, ms: int = 320, amplitude: float = 0.18) -> bytes:
    n = int(OUTPUT_SAMPLE_RATE * ms / 1000)
    samples = array.array("h")
    peak = int(amplitude * 32767)
    for i in range(n):
        # Fade in/out so the tone doesn't click.
        env = min(1.0, i / 480, (n - i) / 480)
        samples.append(int(peak * env * math.sin(2 * math.pi * freq * i / OUTPUT_SAMPLE_RATE)))
    return samples.tobytes()


_TONE = _make_tone()

_REPLIES = cycle(
    [
        "You're talking to a mock live agent; no real model is connected, so this reply is canned.",
        "Got it. This session runs over the real /v1/graph/live socket, but the provider is faked.",
        "Heard you. Wire in a Gemini Live key to swap this stub for a real audio-to-audio model.",
        "Still here. Everything you see is scripted server-side to exercise the Live page.",
    ]
)

_SENTINEL = object()


class FakeRealtimeClient:
    """Scripted realtime provider. See module docstring."""

    def __init__(self) -> None:
        self._out: asyncio.Queue[Any] = asyncio.Queue()
        self._closed = False

    # ---- lifecycle -------------------------------------------------------- #

    async def connect(self, config: RealtimeConfig, resume_handle: str | None = None) -> None:
        # Greet as soon as the session opens (no user turn yet).
        self._emit_agent_turn(
            "Hi! I'm a mock live agent. Tap the mic and speak, and I'll reply with "
            "canned audio. (No real model or API key is connected.)"
        )

    async def close(self) -> None:
        self._closed = True
        self._out.put_nowait(_SENTINEL)

    # ---- upstream (client -> provider) ------------------------------------ #

    async def send_text(self, text: str) -> None:
        if text.strip():
            self._out.put_nowait(_InputTranscript(text=text, finished=True))
        self._emit_agent_turn(next(_REPLIES))

    async def send_activity_end(self) -> None:
        # Push-to-talk finished: we can't transcribe fake audio, so acknowledge.
        self._out.put_nowait(_InputTranscript(text="(spoken input)", finished=True))
        self._emit_agent_turn(next(_REPLIES))

    async def send_audio(self, pcm: bytes, sample_rate: int) -> None:
        # Streaming mic audio: ignored by the stub (it responds on text / activity_end).
        return None

    async def send_activity_start(self) -> None:
        return None

    async def send_image(self, data: bytes, mime_type: str) -> None:
        return None

    async def send_tool_response(self, call_id: str, name: str, result: Any) -> None:
        return None

    async def reseed_history(self, messages: list[Any]) -> None:
        return None

    # ---- downstream (provider -> client) ---------------------------------- #

    async def receive(self):
        while True:
            item = await self._out.get()
            if item is _SENTINEL:
                return
            yield item

    # ---- internal --------------------------------------------------------- #

    def _emit_agent_turn(self, text: str) -> None:
        """Enqueue one agent turn: output transcript + a short tone + turn_complete."""
        if self._closed:
            return
        self._out.put_nowait(OutputTranscriptEvent(text=text, finished=True))
        self._out.put_nowait(AudioDeltaEvent(data=_TONE, sample_rate=OUTPUT_SAMPLE_RATE))
        self._out.put_nowait(TurnCompleteEvent())
