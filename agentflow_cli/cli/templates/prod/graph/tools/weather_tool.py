import logging
import random

from agentflow.core.state.stream_emitter import StreamEmitter

from graph.state import WeatherState


logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def call_weather_api(location: str) -> str:
    is_failed = random.choice([True, False])  # noqa: S311
    if is_failed:
        raise Exception("Failed to fetch weather data due to a simulated API error.")
    return f"The weather in {location} is sunny"


def get_weather(
    location: str,
    tool_call_id: str | None = None,
    state: WeatherState | None = None,
    emit: StreamEmitter | None = None,
) -> str:
    """Get the current weather for a specific location."""
    if tool_call_id:
        logger.info(f"Tool call ID: {tool_call_id}")
    if state and hasattr(state, "context"):
        logger.info(f"Number of messages in context: {len(state.context)}")  # type: ignore
    if emit:
        emit.progress("Fetching weather data...")

    for i in range(MAX_RETRIES):
        try:
            return call_weather_api(location)
        except Exception as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
            if emit:
                emit.progress(f"Attempt {i + 1} failed, retrying...")

    return f"Sorry, I couldn't fetch the weather for {location} after multiple attempts."
