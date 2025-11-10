"""
AI-Powered Thread Name Generator

This module provides an intelligent thread name generator that uses LiteLLM
to create meaningful, concise names for conversation threads based on message content.

Features:
- AI-powered name generation using Gemini 2.0 Flash
- Cost tracking and performance metrics
- Robust error handling with fallback strategies
- Comprehensive logging for debugging and monitoring
- Configurable limits and parameters

Design Philosophy:
- Professional-grade logging at appropriate levels
- Detailed metrics collection for cost analysis
- Graceful degradation when AI services are unavailable
- Clean separation of concerns and single responsibility
"""

import logging
import time
from dataclasses import dataclass
from typing import Final

from litellm import acompletion

from agentflow_cli import ThreadNameGenerator


# Configure module logger
logger = logging.getLogger(__name__)

# Constants for thread name generation
MAX_THREAD_NAME_LENGTH: Final[int] = 50
MAX_MESSAGES_FOR_CONTEXT: Final[int] = 5
DEFAULT_THREAD_NAME: Final[str] = "New Conversation"
FALLBACK_THREAD_NAME: Final[str] = "MyCustomThreadName"
AI_MODEL: Final[str] = "gemini/gemini-2.0-flash-exp"
AI_TEMPERATURE: Final[float] = 0.7
AI_MAX_TOKENS: Final[int] = 50


@dataclass
class GenerationMetrics:
    """Metrics for tracking thread name generation performance and costs."""

    generation_time_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_used: str = ""
    success: bool = False
    error_message: str = ""

    def log_metrics(self) -> None:
        """Log metrics in a structured format."""
        if self.success:
            logger.info(
                "Thread name generation metrics: "
                f"time={self.generation_time_ms:.2f}ms, "
                f"tokens={self.total_tokens} "
                f"(prompt={self.prompt_tokens}, completion={self.completion_tokens}), "
                f"model={self.model_used}"
            )
        else:
            logger.warning(
                "Thread name generation failed: "
                f"time={self.generation_time_ms:.2f}ms, "
                f"error={self.error_message}"
            )


class MyNameGenerator(ThreadNameGenerator):
    """
    AI-powered thread name generator with comprehensive monitoring and error handling.

    This class generates meaningful thread names by analyzing conversation messages
    using LiteLLM's AI capabilities. It includes:
    - Detailed performance and cost metrics
    - Multiple fallback strategies
    - Comprehensive logging for production environments
    - Input validation and sanitization

    Attributes:
        max_length: Maximum length for generated thread names
        max_context_messages: Maximum number of messages to use for context
        model: AI model identifier for LiteLLM
    """

    def __init__(
        self,
        max_length: int = MAX_THREAD_NAME_LENGTH,
        max_context_messages: int = MAX_MESSAGES_FOR_CONTEXT,
        model: str = AI_MODEL,
    ):
        """
        Initialize the thread name generator with configurable parameters.

        Args:
            max_length: Maximum length for generated names (default: 50)
            max_context_messages: Number of messages to use for context (default: 5)
            model: LiteLLM model identifier (default: gemini/gemini-2.0-flash-exp)
        """
        self.max_length = max_length
        self.max_context_messages = max_context_messages
        self.model = model
        logger.debug(
            f"Initialized ThreadNameGenerator: "
            f"max_length={max_length}, max_context={max_context_messages}, model={model}"
        )

    async def generate_name(self, messages: list[str]) -> str:
        """
        Generate a thread name using AI based on conversation messages.

        This method orchestrates the entire generation process including:
        1. Input validation
        2. AI prompt construction
        3. AI model invocation
        4. Response processing and sanitization
        5. Metrics collection and logging
        6. Fallback handling

        Args:
            messages: List of message strings from the conversation

        Returns:
            Generated thread name (respects max_length constraint)

        Raises:
            Does not raise exceptions - handles all errors gracefully with fallbacks
        """
        start_time = time.perf_counter()

        try:
            # Validate input
            if not messages or len(messages) == 0:
                logger.warning("Empty message list provided for thread name generation")
                return self._create_metrics_and_return(
                    start_time, DEFAULT_THREAD_NAME, error="No messages provided"
                )

            logger.debug(f"Generating thread name from {len(messages)} messages")

            # Generate using AI
            thread_name, metrics = await self._generate_with_ai(messages, start_time)
            metrics.log_metrics()

            return thread_name

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Unexpected error in thread name generation: {e}")
            return self._create_metrics_and_return(
                start_time, FALLBACK_THREAD_NAME, error=f"Unexpected error: {e!s}"
            )

    async def _generate_with_ai(
        self, messages: list[str], start_time: float
    ) -> tuple[str, GenerationMetrics]:
        """
        Generate thread name using AI model.

        Args:
            messages: Conversation messages for context
            start_time: Start time for metrics calculation

        Returns:
            Tuple of (generated_name, metrics)
        """
        try:
            # Prepare context from messages
            conversation_preview = self._prepare_conversation_context(messages)

            # Construct prompts
            system_prompt, user_prompt = self._build_prompts(conversation_preview)

            logger.debug(f"Calling AI model: {self.model}")
            logger.debug(f"Conversation preview (first 100 chars): {conversation_preview[:100]}...")

            # Call AI model
            response = await acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
            )

            # Process response
            thread_name = self._extract_and_sanitize_name(response)

            # Calculate metrics
            generation_time_ms = (time.perf_counter() - start_time) * 1000
            metrics = self._extract_metrics(response, generation_time_ms, success=True)

            logger.info(f"Successfully generated thread name: '{thread_name}'")

            return thread_name, metrics

        except Exception as e:
            logger.exception(f"AI generation failed: {type(e).__name__}: {e}")
            generation_time_ms = (time.perf_counter() - start_time) * 1000

            metrics = GenerationMetrics(
                generation_time_ms=generation_time_ms,
                success=False,
                error_message=f"{type(e).__name__}: {e!s}",
            )

            return FALLBACK_THREAD_NAME, metrics

    def _prepare_conversation_context(self, messages: list[str]) -> str:
        """
        Prepare conversation context from messages.

        Args:
            messages: Full list of conversation messages

        Returns:
            Formatted conversation preview string
        """
        # Take first N messages for context
        context_messages = messages[: self.max_context_messages]

        # Format with line numbers for clarity
        formatted_lines = [f"{i+1}. {msg}" for i, msg in enumerate(context_messages)]

        preview = "\n".join(formatted_lines)

        if len(messages) > self.max_context_messages:
            preview += f"\n... ({len(messages) - self.max_context_messages} more messages)"

        return preview

    def _build_prompts(self, conversation_preview: str) -> tuple[str, str]:
        """
        Build system and user prompts for AI model.

        Args:
            conversation_preview: Formatted conversation context

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = (
            "You are an expert at generating concise, meaningful thread titles. "
            f"Generate a short, descriptive title (maximum {self.max_length} characters) "
            "that captures the essence of the conversation. "
            "The title should be:\n"
            "- Clear and professional\n"
            "- Informative and specific\n"
            "- Free of unnecessary words like 'Chat', 'Conversation', 'Thread'\n"
            "- Focused on the main topic or question\n"
            "Return ONLY the title text, nothing else."
        )

        user_prompt = (
            f"Based on the following conversation, generate a concise thread name "
            f"(max {self.max_length} characters):\n\n"
            f"Conversation:\n{conversation_preview}\n\n"
            "Thread name:"
        )

        return system_prompt, user_prompt

    def _extract_and_sanitize_name(self, response) -> str:
        """
        Extract and sanitize thread name from AI response.

        Args:
            response: LiteLLM response object

        Returns:
            Sanitized thread name

        Raises:
            ValueError: If response is invalid or empty
        """
        # Validate response structure
        if not hasattr(response, "choices") or len(response.choices) == 0:
            logger.warning("AI response has no choices")
            raise ValueError("Invalid AI response: no choices")

        # Extract content
        content = response.choices[0].message.content
        if not content:
            logger.warning("AI response content is empty")
            raise ValueError("Invalid AI response: empty content")

        # Sanitize
        thread_name = content.strip()

        # Remove common quote marks
        thread_name = thread_name.strip("\"'`")

        # Remove newlines and excessive whitespace
        thread_name = " ".join(thread_name.split())

        # Enforce length limit
        if len(thread_name) > self.max_length:
            thread_name = thread_name[: self.max_length - 3] + "..."
            logger.debug(f"Truncated thread name to {self.max_length} characters")

        # Validate result
        if not thread_name or thread_name.isspace():
            logger.warning("Sanitized thread name is empty")
            raise ValueError("Thread name is empty after sanitization")

        return thread_name

    def _extract_metrics(
        self, response, generation_time_ms: float, success: bool = True
    ) -> GenerationMetrics:
        """
        Extract usage metrics from AI response.

        Args:
            response: LiteLLM response object
            generation_time_ms: Time taken for generation
            success: Whether generation was successful

        Returns:
            GenerationMetrics object
        """
        metrics = GenerationMetrics(
            generation_time_ms=generation_time_ms, success=success, model_used=self.model
        )

        # Extract token usage if available
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            metrics.prompt_tokens = getattr(usage, "prompt_tokens", 0)
            metrics.completion_tokens = getattr(usage, "completion_tokens", 0)
            metrics.total_tokens = getattr(usage, "total_tokens", 0)
        else:
            logger.debug("No usage information in AI response")

        return metrics

    def _create_metrics_and_return(
        self, start_time: float, thread_name: str, error: str = ""
    ) -> str:
        """
        Helper to create metrics and return thread name.

        Args:
            start_time: Start time for metrics
            thread_name: Name to return
            error: Error message if applicable

        Returns:
            Thread name
        """
        generation_time_ms = (time.perf_counter() - start_time) * 1000
        metrics = GenerationMetrics(
            generation_time_ms=generation_time_ms, success=(error == ""), error_message=error
        )
        metrics.log_metrics()
        return thread_name
