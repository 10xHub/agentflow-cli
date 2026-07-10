"""
Real *live* (realtime audio-to-audio) AgentFlow graph — Gemini Live.

This is a genuine realtime agent: ``LiveAgent`` with no ``realtime_client_factory``
override, so it uses the framework's real ``GeminiLiveClient``. That client reads the
API key lazily at connect time from ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``) in the
environment — set one in ``.env`` before opening a session.

What the server does with this graph:

* ``CompiledGraph`` recognises the ``LiveAgent`` node, so ``GET /v1/graph`` reports
  ``info.is_realtime = true`` and the playground lights the "live" capability chip.
* A session runs over ``WS /v1/graph/live``: mic PCM in, model audio out, plus input
  and output transcripts (both transcriptions enabled below).

VAD is disabled (``VADConfig(enabled=False)``) so the session uses *manual* activity
detection — the playground's push-to-talk (activity_start -> stream audio ->
activity_end) is the supported flow. Leave VAD enabled instead if you want the model
to auto-detect turn boundaries from a continuously open mic.

Constructing/compiling this graph touches no network and needs no key; only opening a
session does. A live graph is realtime-only: turn-based endpoints (invoke/stream/ws)
reject it by design, so the playground's Chat page won't work while this is the active
agent. Point ``agent`` back at ``graph.react:app`` in agentflow.json for turn-based.

(A keyless, network-free stand-in for local UI testing lives in
``graph.fake_realtime_client``; pass ``realtime_client_factory=FakeRealtimeClient`` to
the ``LiveAgent`` below to use it instead of the real provider.)

Exposed as ``app`` and referenced in agentflow.json as ``"agent": "graph.live:app"``.
"""

from __future__ import annotations

import os

from agentflow.core.graph import StateGraph
from agentflow.core.realtime.base import RealtimeConfig, VADConfig
from agentflow.core.realtime.live_agent import LiveAgent


# Gemini Live model. Live model availability is key/region specific: list yours with
#   client.models.list()  -> keep those whose supported_actions include "bidiGenerateContent".
# The default below is a native-audio dialog model verified to accept this graph's
# push-to-talk (manual VAD) session. Override with LIVE_MODEL to use another (e.g.
# "gemini-3.1-flash-live-preview"). detect_provider only needs the name to resolve to the
# "google" provider; the exact id is validated by Gemini at connect.
LIVE_MODEL = os.getenv("LIVE_MODEL", "gemini-2.5-flash-native-audio-latest")

# A Gemini prebuilt voice (Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr).
LIVE_VOICE = os.getenv("LIVE_VOICE", "Puck")

SYSTEM_PROMPT = (
    "You are a friendly, concise voice assistant running inside the AgentFlow "
    "playground. Keep spoken replies short and natural, and ask a brief clarifying "
    "question when a request is ambiguous."
)

realtime_config = RealtimeConfig(
    model=LIVE_MODEL,
    response_modalities=["AUDIO"],
    voice=LIVE_VOICE,
    # Manual activity detection so push-to-talk (activity_start/activity_end) is valid.
    vad=VADConfig(enabled=False),
    input_audio_transcription=True,
    output_audio_transcription=True,
)

live_agent = LiveAgent(
    model=LIVE_MODEL,
    realtime_config=realtime_config,
    system_prompt=[{"role": "system", "content": SYSTEM_PROMPT}],
)

graph = StateGraph()
graph.add_node("LIVE", live_agent)
graph.set_entry_point("LIVE")

app = graph.compile()
