import logging

from agentflow.utils.constants import END


logger = logging.getLogger(__name__)


def should_use_tools(state) -> str:
    """Route between the assistant node and the tool node."""
    if not state.context:
        return END

    last_message = state.context[-1]
    if not last_message:
        return END

    if (
        last_message.role == "assistant"
        and hasattr(last_message, "tools_calls")
        and last_message.tools_calls
    ):
        logger.debug("Routing assistant tool call to TOOL node")
        return "TOOL"

    if last_message.role == "tool":
        logger.debug("Tool result received, routing back to MAIN for final response")
        return "MAIN"

    return END
