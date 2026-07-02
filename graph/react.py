"""
Dummy AgentFlow graph — no LLM, no API key required.

Purpose: exercise the full API + playground integration (streaming, reasoning
blocks, tool_call/tool_result blocks, final answer) with deterministic output.

Flow:  MAIN (emit reasoning + tool_call) -> TOOL (dummy weather) -> MAIN (answer)

Exposed as ``app`` and referenced in agentflow.json as ``"agent": "graph.react:app"``.
Swap ``main_node`` for a real LLM node when a valid provider key is available.
"""

from __future__ import annotations

import json

from agentflow.core.graph import StateGraph, ToolNode
from agentflow.core.state import (
    AgentState,
    Message,
    ReasoningBlock,
    TextBlock,
    TokenUsages,
    ToolCallBlock,
)
from agentflow.utils.constants import END


# --------------------------------------------------------------------------- #
#  Dummy tool (real ToolNode, but the function is canned — no network/LLM)     #
# --------------------------------------------------------------------------- #

_FIXED_TOOL_CALL_ID = "call_dummy_weather_1"


async def get_weather(location: str = "Dhaka, BD") -> dict:
    """Return a canned weather report for the given location (no external call)."""
    return {
        "location": location,
        "temp_c": 31.4,
        "condition": "Partly cloudy",
        "precip_prob_pct": 62,
        "wind_kph": 11,
    }


tool_node = ToolNode([get_weather])

# --------------------------------------------------------------------------- #
#  Main node — deterministic, no LLM                                           #
# --------------------------------------------------------------------------- #


async def main_node(state: AgentState):
    """Two-pass node: first call emits a tool_call, second call answers."""
    last = state.context[-1] if state.context else None

    # Second pass: a tool result is present -> produce the final answer.
    if last is not None and last.role == "tool":
        return Message(
            role="assistant",
            content=[
                ReasoningBlock(
                    summary="Read the weather result and decided on an umbrella recommendation.",
                ),
                TextBlock(
                    text=(
                        "It's **31.4°C** and partly cloudy in Dhaka right now, with a "
                        "**62% chance of rain** this afternoon and light winds around "
                        "11 km/h.\n\nYes — I'd carry the umbrella. The precipitation "
                        "probability is high enough that an afternoon shower is likely."
                    ),
                ),
            ],
            # Dummy-but-realistic usage so the playground can surface token counts.
            usages=TokenUsages(
                prompt_tokens=486,
                completion_tokens=74,
                total_tokens=560,
                reasoning_tokens=18,
            ),
        )

    # First pass: think, then call the (dummy) weather tool.
    #
    # ToolNode reads tool calls from the message's `tools_calls` field (OpenAI
    # shape: {"id", "function": {"name", "arguments"}}), NOT from the content
    # ToolCallBlock. We must populate both: the block drives UI rendering, the
    # field drives execution + routing.
    tool_args = {"location": "Dhaka, BD"}
    return Message(
        role="assistant",
        content=[
            ReasoningBlock(
                summary="User asked about the weather. I'll call get_weather for Dhaka.",
            ),
            ToolCallBlock(
                id=_FIXED_TOOL_CALL_ID,
                name="get_weather",
                args=tool_args,
            ),
        ],
        tools_calls=[
            {
                "id": _FIXED_TOOL_CALL_ID,
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": json.dumps(tool_args),
                },
            }
        ],
        # First-pass usage (reasoning + tool call). The playground sums usages
        # across the run to show a per-turn total.
        usages=TokenUsages(
            prompt_tokens=312,
            completion_tokens=41,
            total_tokens=353,
            reasoning_tokens=24,
        ),
    )


# --------------------------------------------------------------------------- #
#  Routing                                                                      #
# --------------------------------------------------------------------------- #


def route(state: AgentState) -> str:
    if not state.context:
        return END

    last = state.context[-1]

    # Assistant asked for a tool -> run it. main_node populates `tools_calls`
    # (the same field ToolNode executes from), so route on it.
    if last.role == "assistant" and last.tools_calls:
        return "TOOL"

    # Tool finished -> back to MAIN to summarise.
    if last.role == "tool":
        return "MAIN"

    return END


# --------------------------------------------------------------------------- #
#  Graph                                                                        #
# --------------------------------------------------------------------------- #

graph = StateGraph()
graph.add_node("MAIN", main_node)
graph.add_node("TOOL", tool_node)
graph.add_conditional_edges("MAIN", route, {"TOOL": "TOOL", "MAIN": "MAIN", END: END})
graph.add_edge("TOOL", "MAIN")
graph.set_entry_point("MAIN")

app = graph.compile()
