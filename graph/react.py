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
                    summary=(
                        "### Reading the tool result\n\n"
                        "`get_weather` came back for **Dhaka, BD**. Pulling the four "
                        "fields that actually matter for the question:\n\n"
                        "| Field | Value | Reads as |\n"
                        "| --- | --- | --- |\n"
                        "| `temp_c` | 31.4 | hot, but not extreme |\n"
                        "| `condition` | Partly cloudy | unstable sky |\n"
                        "| `precip_prob_pct` | 62 | *the deciding number* |\n"
                        "| `wind_kph` | 11 | light, umbrella stays usable |\n\n"
                        "**How I weighed it**\n\n"
                        "1. Anything at or above ~50% precipitation probability is a "
                        "coin flip I would not want to lose while outside.\n"
                        "2. 62% sits comfortably above that line, so the expected cost "
                        "of carrying an umbrella (mild inconvenience) is smaller than "
                        "the expected cost of skipping it (getting soaked).\n"
                        "3. Wind at 11 km/h is low enough that an umbrella will not "
                        "invert, so the recommendation is actually actionable — at "
                        "25+ km/h I would have suggested a rain jacket instead.\n\n"
                        "> Conclusion: recommend the umbrella, and surface the raw "
                        "numbers in a card so the user can second-guess me.\n\n"
                        "Rendering the answer as an HTML card rather than prose so the "
                        "playground's HTML path gets exercised too."
                    ),
                ),
                TextBlock(
                    text=(
                        '<div style="max-width:340px;border:1px solid #e2e8f0;'
                        "border-radius:12px;padding:16px;font-family:system-ui,sans-serif;"
                        'box-shadow:0 1px 3px rgba(0,0,0,.08)">'
                        '<div style="display:flex;justify-content:space-between;'
                        'align-items:baseline">'
                        '<strong style="font-size:15px">Dhaka, BD</strong>'
                        '<span style="font-size:12px;color:#64748b">now</span>'
                        "</div>"
                        '<div style="font-size:34px;font-weight:600;margin:6px 0">'
                        "31.4&deg;C</div>"
                        '<div style="font-size:13px;color:#475569">Partly cloudy</div>'
                        '<hr style="border:none;border-top:1px solid #e2e8f0;margin:12px 0">'
                        '<table style="width:100%;font-size:13px;border-collapse:collapse">'
                        '<tr><td style="color:#64748b">Rain chance</td>'
                        '<td style="text-align:right"><strong>62%</strong></td></tr>'
                        '<tr><td style="color:#64748b">Wind</td>'
                        '<td style="text-align:right">11 km/h</td></tr>'
                        "</table>"
                        '<div style="margin-top:12px;padding:8px 10px;border-radius:8px;'
                        'background:#eff6ff;color:#1d4ed8;font-size:13px">'
                        "&#9730; Take the umbrella</div>"
                        "</div>\n\n"
                        "So: hot and muggy, and that <strong>62%</strong> is the number "
                        "doing the work here. An afternoon shower is more likely than "
                        "not, and with winds only around 11 km/h an umbrella will "
                        "actually hold up.\n\n"
                        "Plain text again, no tags — the last line is deliberately "
                        "unstyled so you can see where the HTML stops."
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
                summary=(
                    "### Planning the first pass\n\n"
                    "The user is asking about **current conditions**, which is not "
                    "something I can answer from memory — it needs a live lookup.\n\n"
                    "**Tools available**\n\n"
                    "- `get_weather(location)` — returns temp, condition, precipitation "
                    "probability and wind. This is the only one that fits.\n\n"
                    "**Argument choice**\n\n"
                    "No location was given explicitly, so I default to "
                    '`"Dhaka, BD"` — country code included so the call is unambiguous '
                    "(there is more than one Dhaka).\n\n"
                    "I emit the call in *both* places on purpose:\n\n"
                    "1. `ToolCallBlock` in `content` — drives what the UI renders.\n"
                    "2. `tools_calls` on the message — drives execution and routing.\n\n"
                    "> Next hop: `TOOL`, then back to `MAIN` to turn the raw numbers "
                    "into an answer."
                ),
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
