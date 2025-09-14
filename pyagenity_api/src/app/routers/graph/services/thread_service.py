from typing import Any

from injectq import inject, singleton
from litellm import acompletion
from pyagenity.checkpointer import BaseCheckpointer
from pyagenity.utils import Message

from src.app.core import logger
from src.app.core.config.settings import get_settings

from .dummy_name_generator import generate_dummy_thread_name


@singleton
class ThreadService:
    """
    Service for thread-related operations, such as generating thread names using LLMs.
    """

    @inject
    def __init__(self, checkpointer: BaseCheckpointer):
        self.settings = get_settings()
        self.model = self.settings.THREAD_MODEL_NAME or "gemini/gemini-2.0-flash"
        self.checkpointer = checkpointer

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
        messages: list[Message],
    ) -> bool:
        """
        Generate a thread name using an LLM based on the provided messages.

        Args:
                messages (list[dict]): List of message dicts with 'role' and 'content'.

        Returns:
                str: Generated thread name.
        """
        # check enabled or not
        if not self.settings.GENERATE_THREAD_NAME:
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

        prompt = (
            "You are a helpful assistant. "
            "Given the following conversation, generate a concise and descriptive thread name "
            "summarizing the topic. Only return the thread name, nothing else."
        )
        llm_messages = [
            {"role": "system", "content": prompt},
        ]
        for msg in messages:
            if not msg.content:
                continue
            if msg.role == "tool":
                continue
            llm_messages.append({"role": msg.role, "content": msg.content})

        response = await acompletion(
            model=self.model,
            messages=llm_messages,
            stream=False,
        )
        # response is a dict with 'choices', each with 'message' and 'content'
        res = response.model_dump()  # type: ignore
        thread_name = res.get("choices", [{}])[0].get("message", {}).get("content", "")
        thread_name = str(thread_name).strip() if thread_name else generate_dummy_thread_name()

        # now save into db
        res = await self._save_thread(config, thread_id, thread_name)
        logger.debug(f"Thread name generated and saved: {thread_name}")
        return True
