from typing import Any

from injector import singleton
from pyagenity.checkpointer import BaseCheckpointer
from pyagenity.state import AgentState
from pyagenity.utils import Message

from src.app.core import logger
from src.app.core.config.settings import get_settings
from src.app.routers.checkpointer.schemas.checkpointer_schemas import (
    MessagesListResponseSchema,
    ResponseSchema,
    StateResponseSchema,
    ThreadResponseSchema,
    ThreadsListResponseSchema,
)


@singleton
class CheckpointerService:
    def __init__(self, checkpointer: BaseCheckpointer[AgentState]):
        self.checkpointer = checkpointer
        self.settings = get_settings(0)

    def _config(self, config: dict, user: dict):
        if not self.checkpointer:
            raise ValueError("Checkpointer is not configured")

        config["user"] = user
        config["user_id"] = user.get(self.settings.USER_ID_KEY, None)
        return config

    async def get_state(self, config: dict, user: dict) -> StateResponseSchema:
        config = self._config(config, user)
        res = await self.checkpointer.aget_state(config)
        return StateResponseSchema(
            state=res,
        )

    async def put_state(
        self,
        config: dict,
        user: dict,
        state: AgentState,
    ) -> StateResponseSchema:
        config = self._config(config, user)
        # lets merge it
        old_state: AgentState | None = await self.checkpointer.aget_state(config)

        # if old state not found then read from cache
        if not old_state:
            old_state = await self.checkpointer.aget_state_cache(config)

        # merge both states, both are pydantic
        if old_state:
            # update execution_meta its not expected to shared by frontend
            state.execution_meta = old_state.execution_meta

        if not state.context and old_state:
            state.context = old_state.context

        # check summary:
        if not state.context_summary and old_state:
            state.context_summary = old_state.context_summary

        res = await self.checkpointer.aput_state(config, state)
        return StateResponseSchema(
            state=res,
        )

    async def clear_state(self, config: dict, user: dict) -> ResponseSchema:
        config = self._config(config, user)
        res = await self.checkpointer.aclear_state(config)
        return ResponseSchema(
            success=True,
            message="State cleared successfully",
            data=res,
        )

    # Messages
    async def put_messages(
        self,
        config: dict,
        user: dict,
        messages: list[Message],
        metadata: dict | None = None,
    ) -> ResponseSchema:
        config = self._config(config, user)
        res = await self.checkpointer.aput_messages(config, messages, metadata)
        return ResponseSchema(
            success=True,
            message="Messages put successfully",
            data=res,
        )

    async def get_message(
        self,
        config: dict,
        user: dict,
        message_id: Any,
    ) -> Message:
        config = self._config(config, user)
        return await self.checkpointer.aget_message(config, message_id)

    async def get_messages(
        self,
        config: dict[str, Any],
        user: dict,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> MessagesListResponseSchema:
        config = self._config(config, user)
        res = await self.checkpointer.alist_messages(config, search, offset, limit)
        return MessagesListResponseSchema(messages=res)

    async def delete_message(self, config: dict, user: dict, message_id: Any) -> ResponseSchema:
        config = self._config(config, user)
        res = await self.checkpointer.adelete_message(config, message_id)
        return ResponseSchema(
            success=True,
            message="Message deleted successfully",
            data=res,
        )

    # Now Thread
    async def get_thread(self, config: dict, user: dict) -> ThreadResponseSchema:
        config = self._config(config, user)
        logger.debug(f"User info: {user} and")
        res = await self.checkpointer.aget_thread(config)
        return ThreadResponseSchema(thread=res)

    async def list_threads(
        self,
        user: dict,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> ThreadsListResponseSchema:
        config = self._config({}, user)
        res = await self.checkpointer.alist_threads(config, search, offset, limit)
        return ThreadsListResponseSchema(threads=res)

    async def delete_thread(self, config: dict, user: dict, thread_id: Any) -> ResponseSchema:
        config = self._config(config, user)
        logger.debug(f"User info: {user} and thread ID: {thread_id}")
        res = await self.checkpointer.aclean_thread(config)
        return ResponseSchema(
            success=True,
            message="Thread deleted successfully",
            data=res,
        )
