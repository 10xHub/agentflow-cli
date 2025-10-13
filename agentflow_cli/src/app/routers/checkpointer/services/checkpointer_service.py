from typing import Any

from agentflow.checkpointer import BaseCheckpointer
from agentflow.state import AgentState, Message
from injectq import inject, singleton

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.settings import get_settings
from agentflow_cli.src.app.routers.checkpointer.schemas.checkpointer_schemas import (
    MessagesListResponseSchema,
    ResponseSchema,
    StateResponseSchema,
    ThreadResponseSchema,
    ThreadsListResponseSchema,
)
from agentflow_cli.src.app.utils.parse_output import parse_state_output


@singleton
class CheckpointerService:
    @inject
    def __init__(self, checkpointer: BaseCheckpointer):
        self.checkpointer = checkpointer
        self.settings = get_settings()

    def _config(self, config: dict[str, Any] | None, user: dict) -> dict[str, Any]:
        if not self.checkpointer:
            raise ValueError("Checkpointer is not configured")

        cfg: dict[str, Any] = dict(config or {})
        cfg["user"] = user
        cfg["user_id"] = user.get("user_id", "anonymous")
        return cfg

    async def get_state(self, config: dict[str, Any], user: dict) -> StateResponseSchema:
        cfg = self._config(config, user)

        # this will return base pydantic model
        res = await self.checkpointer.aget_state(cfg)
        if not res:
            rs = await self.checkpointer.aget_state_cache(cfg)
            return StateResponseSchema(state=rs)

        if res:
            return StateResponseSchema(
                state=parse_state_output(
                    self.settings,
                    res,
                ),
            )

        return StateResponseSchema(state=res)

    async def put_state(
        self,
        config: dict[str, Any],
        user: dict,
        state: dict[str, Any],
    ) -> StateResponseSchema:
        cfg = self._config(config, user)
        old_state: AgentState | None = await self.checkpointer.aget_state(cfg)
        if not old_state:
            old_state = await self.checkpointer.aget_state_cache(cfg)

        # say two states are being merged
        # How to merge to pydantic model
        # Merge incoming state dict into existing Pydantic state, then rebuild the model.

        merged = self._merge_states(old_state, state)
        to_store = self._reconstruct_state(old_state, merged)
        res = await self.checkpointer.aput_state(cfg, to_store)  # type: ignore[arg-type]
        # update cache as well
        await self.checkpointer.aput_state_cache(cfg, to_store)  # type: ignore

        return StateResponseSchema(
            state=parse_state_output(
                self.settings,
                res,
            ),
        )

    async def clear_state(self, config: dict[str, Any], user: dict) -> ResponseSchema:
        cfg = self._config(config, user)
        res = await self.checkpointer.aclear_state(cfg)
        return ResponseSchema(success=True, message="State cleared successfully", data=res)

    # Messages
    async def put_messages(
        self,
        config: dict[str, Any],
        user: dict,
        messages: list[Message],
        metadata: dict[str, Any] | None = None,
    ) -> ResponseSchema:
        # For message operations tests expect only a minimal config containing user
        cfg = self._config(config, user)
        minimal_cfg = {"user": cfg["user"]}
        res = await self.checkpointer.aput_messages(minimal_cfg, messages, metadata)
        return ResponseSchema(success=True, message="Messages put successfully", data=res)

    async def get_message(
        self,
        config: dict[str, Any],
        user: dict,
        message_id: Any,
    ) -> Message:
        cfg = self._config(config, user)
        minimal_cfg = {"user": cfg["user"]}
        return await self.checkpointer.aget_message(minimal_cfg, message_id)

    async def get_messages(
        self,
        config: dict[str, Any],
        user: dict,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> MessagesListResponseSchema:
        cfg = self._config(config, user)
        minimal_cfg = {"user": cfg["user"]}
        res = await self.checkpointer.alist_messages(minimal_cfg, search, offset, limit)
        return MessagesListResponseSchema(messages=res)

    async def delete_message(
        self,
        config: dict[str, Any],
        user: dict,
        message_id: Any,
    ) -> ResponseSchema:
        cfg = self._config(config, user)
        minimal_cfg = {"user": cfg["user"]}
        res = await self.checkpointer.adelete_message(minimal_cfg, message_id)
        return ResponseSchema(success=True, message="Message deleted successfully", data=res)

    # Threads
    async def get_thread(self, config: dict[str, Any], user: dict) -> ThreadResponseSchema:
        cfg = self._config(config, user)
        logger.debug(f"User info: {user} and")
        res = await self.checkpointer.aget_thread(cfg)
        return ThreadResponseSchema(thread=res.model_dump() if res else None)

    async def list_threads(
        self,
        user: dict,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> ThreadsListResponseSchema:
        cfg = self._config({}, user)
        res = await self.checkpointer.alist_threads(cfg, search, offset, limit)
        return ThreadsListResponseSchema(threads=[t.model_dump() for t in res])

    async def delete_thread(
        self,
        config: dict[str, Any],
        user: dict,
        thread_id: Any,
    ) -> ResponseSchema:
        cfg = self._config(config, user)
        logger.debug(f"User info: {user} and thread ID: {thread_id}")
        res = await self.checkpointer.aclean_thread(cfg)
        return ResponseSchema(success=True, message="Thread deleted successfully", data=res)

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------
    def _merge_states(
        self, old_state: AgentState | None, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge a partial state dict into an existing AgentState.

        Rules:
        - Preserve execution_meta from old_state unless explicitly provided (discouraged).
        - Append context messages if both sides provide them; otherwise set from updates.
        - Deep-merge dictionaries; non-dict values from updates overwrite.
        - None values in updates do not overwrite existing values.
        """

        base: dict[str, Any] = {}
        if old_state is not None:
            # Keep full dump so we can preserve existing fields
            base = old_state.model_dump()

        merged: dict[str, Any] = {**base}

        # Handle context specially (append)
        if "context" in updates and updates["context"] is not None:
            old_ctx = base.get("context", []) if base else []
            new_ctx = updates.get("context") or []
            # Simply concatenate; Pydantic will validate/convert dicts to Message
            merged["context"] = list(old_ctx) + list(new_ctx)

        # execution_meta: keep from old unless explicitly provided as dict/model
        if old_state is not None:
            merged["execution_meta"] = old_state.execution_meta

        # Apply remaining fields with deep merge
        for k, v in updates.items():
            if k in ("context", "execution_meta"):
                continue
            if v is None:
                # Do not erase existing values with None by default
                continue
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = self._deep_merge_dicts(merged[k], v)
            else:
                merged[k] = v

        return merged

    def _deep_merge_dicts(self, base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries without mutating inputs."""
        out: dict[str, Any] = {**base}
        for k, v in updates.items():
            if v is None:
                continue
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_merge_dicts(out[k], v)
            else:
                out[k] = v
        return out

    def _reconstruct_state(self, old_state: AgentState | None, data: dict[str, Any]) -> AgentState:
        """Rebuild the appropriate AgentState (or subclass) from merged dict."""
        state_cls = type(old_state) if isinstance(old_state, AgentState) else AgentState

        # Ensure execution_meta stays as model if present
        if old_state is not None:
            data["execution_meta"] = old_state.execution_meta

        return state_cls.model_validate(data)
