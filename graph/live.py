"""
Dummy *live* (realtime audio) AgentFlow graph — no API key, no network at import.

Purpose: give the API + playground a graph the server recognises as a realtime
agent. ``CompiledGraph._find_live_nodes()`` finds the ``LiveAgent`` node, so:

* ``GET /v1/graph`` reports ``info.is_realtime = true`` (added in graph_service),
* the playground connection probe lights the "live" capability chip, and
* the Live page shows the live-capable state instead of "not available".

This is a MOCK. ``LiveAgent`` is built with a Gemini Live model *name* only — the
provider (google) is validated at construction time, but no key is needed until a
session is actually opened. Constructing + compiling this graph touches no network.

Note: a live graph is realtime-only. Turn-based endpoints (invoke/stream/ws) reject
it by design, so the playground's Chat page won't work while this is the active
agent. Point ``agent`` back at ``graph.react:app`` in agentflow.json for the
turn-based demo. Actually opening a session over ``WS /v1/graph/live`` needs a real
Gemini Live API key + provider.

Exposed as ``app`` and referenced in agentflow.json as ``"agent": "graph.live:app"``.
"""

from __future__ import annotations

from agentflow.core.graph import StateGraph
from agentflow.core.realtime.live_agent import LiveAgent


# Gemini Live model. Only the provider ("google") is checked when the agent is
# constructed; the API key is lazy (used by the provider client at connect time).
LIVE_MODEL = "gemini-2.5-flash-live"

live_agent = LiveAgent(model=LIVE_MODEL)

graph = StateGraph()
graph.add_node("LIVE", live_agent)
graph.set_entry_point("LIVE")

app = graph.compile()
