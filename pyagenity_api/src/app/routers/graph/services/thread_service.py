import json
from typing import Any

from injectq import inject, singleton
from litellm import acompletion
from litellm.types.utils import ModelResponse
from pyagenity.checkpointer import BaseCheckpointer
from pyagenity.utils import Message

from pyagenity_api.src.app.core import logger
from pyagenity_api.src.app.core.config.graph_config import GraphConfig

from .dummy_name_generator import generate_dummy_thread_name


MODEL_PROMPT = """
You are a helpful assistant. Given the following conversation, generate a concise, descriptive 
thread name summarizing its topic.

Requirements:
- Keep it under 10 words.
- Make it specific and relevant.
- Avoid generic names like "Chat" or "Conversation".

Respond only in this format:
{
  "thread_name": "Generated Thread Name"
}
"""


@singleton
class ThreadService:
    """
    Service for thread-related operations, such as generating thread names using LLMs.
    """

    @inject
    def __init__(
        self,
        checkpointer: BaseCheckpointer,
        config: GraphConfig,
    ):
        self.checkpointer = checkpointer
        self.config = config

    async def _save_thread(self, config: dict[str, Any], thread_id: int, thread_name: str):
        """
        Save the generated thread name to the database.
        """
        return await self.checkpointer.aput_thread(
            config,
            {"thread_id": thread_id, "thread_name": thread_name},
        )

    async def save_thread_name(
        self,
        config: dict[str, Any],
        thread_id: int,
        messages: list[dict[str, Any]],
    ) -> bool:
        """
        Generate a thread name using an LLM based on the provided messages.

        Args:
                messages (list[dict]): List of message dicts with 'role' and 'content'.

        Returns:
                str: Generated thread name.
        """
        # check enabled or not
        if not self.config.generate_thread_name:
            logger.debug(
                f"Thread name generation is disabled in settings. "
                f"Here is a name for you {generate_dummy_thread_name()}"
            )
            return False

        # check checkpointer is available or not
        if not self.checkpointer:
            logger.debug(
                f"Thread name generation is disabled because checkpointer is not available. "
                f"Here is a name for you {generate_dummy_thread_name()}"
            )
            return False

        if not self.config.thread_model_name:
            logger.debug(
                f"Thread name generation is disabled because thread_model_name "
                f"is not set in config."
                f"Here is a name for you {generate_dummy_thread_name()}"
            )
            return False

        llm_messages = [
            {"role": "system", "content": MODEL_PROMPT},
        ]
        llm_messages.extend(messages)

        try:
            response = await acompletion(
                model=self.config.thread_model_name,
                messages=llm_messages,
                max_tokens=100,
                temperature=0.5,
                top_p=1.0,
                n=1,
                stop=None,
            )
            res: ModelResponse = response  # type: ignore
            thread_name = ""
            if res and res.choices and len(res.choices) > 0:
                content = res.get("choices", [{}])[0].get("message", {}).get("content", "")  # type: ignore
                logger.debug(f"LLM response for thread name: {content}")
                # Extract thread name from the response
                try:
                    data = json.loads(content)
                    thread_name = data.get("thread_name", "").strip()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    thread_name = generate_dummy_thread_name()
            if not thread_name:
                thread_name = generate_dummy_thread_name()
            logger.debug(f"Generated thread name: {thread_name}")

            await self._save_thread(config, thread_id, thread_name)
        except Exception as e:
            logger.error(f"Error generating thread name: {e}")
            thread_name = generate_dummy_thread_name()
            await self._save_thread(config, thread_id, thread_name)
            return False
        return True

    async def generate_thread_name_invoke(
        self,
        config: dict[str, Any],
        thread_id: int,
        messages: list[Message],
    ) -> bool:
        llm_messages = []
        for msg in messages:
            if not msg.content:
                continue
            if msg.role == "tool":
                continue
            llm_messages.append({"role": msg.role, "content": msg.content})

        return await self.save_thread_name(config, thread_id, llm_messages)

    async def generate_thread_name_stream(
        self,
        config: dict[str, Any],
        thread_id: int,
        messages: list[dict[str, Any]],
    ) -> bool:
        llm_messages = []
        content_list = set()
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            if not role or not content:
                continue
            if role == "tool":
                continue

            if content in content_list:
                continue
            content_list.add(content)

            llm_messages.append({"role": role, "content": content})

        return await self.save_thread_name(config, thread_id, llm_messages)
