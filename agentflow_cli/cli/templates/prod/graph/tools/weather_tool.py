import logging
import random

from agentflow.core.state.stream_emitter import StreamEmitter

from graph.state import WeatherState


logger = logging.getLogger(__name__)


def call_weather_api(location: str) -> str:
    is_failed = random.choice([True, False])  # Randomly simulate success or failure  # noqa: S311
    if is_failed:
        raise Exception("Failed to fetch weather data due to a simulated API error.")
    return f"The weather in {location} is sunny"


def get_weather(
    location: str,
    tool_call_id: str | None = None,
    state: WeatherState | None = None,
    emit: StreamEmitter | None = None,
) -> str:
    """
    Get the current weather for a specific location.
    This demo shows injectable parameters: tool_call_id and state are automatically injected.
    """
    # You can access injected parameters here
    if tool_call_id:
        logger.info(f"Tool call ID: {tool_call_id}")
    if state and hasattr(state, "context"):
        logger.info(f"Number of messages in context: {len(state.context)}")  # type: ignore
    if emit:
        emit.progress("Fetching weather data...")

    # return f"The weather in {location} is sunny"

    result = ""
    for i in range(3):  # Try up to 3 times
        try:
            result = call_weather_api(location)
            break  # If successful, exit the loop
        except Exception as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
            result = f"Sorry, I couldn't fetch the weather for {location} after multiple attempts."
            if emit:
                emit.progress(f"Attempt {i + 1} failed, retrying...")

    return result
