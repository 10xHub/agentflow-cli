from __future__ import annotations

from typing import Any

from agentflow.state import Message
from agentflow.store import BaseStore
from injectq import inject, singleton

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.routers.store.schemas.store_schemas import (
    ForgetMemorySchema,
    MemoryCreateResponseSchema,
    MemoryItemResponseSchema,
    MemoryListResponseSchema,
    MemoryOperationResponseSchema,
    MemorySearchResponseSchema,
    SearchMemorySchema,
    StoreMemorySchema,
    UpdateMemorySchema,
)


@singleton
class StoreService:
    """Service layer wrapping interactions with the configured BaseStore."""

    @inject
    def __init__(self, store: BaseStore | None):
        self.store = store

    def _get_store(self) -> BaseStore:
        if not self.store:
            raise ValueError("Store is not configured")
        return self.store

    def _config(self, config: dict[str, Any] | None, user: dict[str, Any]) -> dict[str, Any]:
        cfg: dict[str, Any] = dict(config or {})
        cfg.setdefault("user", user)
        cfg["user_id"] = user.get("user_id", "anonymous")
        return cfg

    async def store_memory(
        self,
        payload: StoreMemorySchema,
        user: dict[str, Any],
    ) -> MemoryCreateResponseSchema:
        store = self._get_store()
        cfg = self._config(payload.config, user)
        options = payload.options or {}

        if isinstance(payload.content, Message):
            content: str | Message = payload.content
        else:
            content = payload.content

        memory_id = await store.astore(
            cfg,
            content,
            memory_type=payload.memory_type,
            category=payload.category,
            metadata=payload.metadata,
            **options,
        )
        logger.debug("Stored memory with id %s", memory_id)
        return MemoryCreateResponseSchema(memory_id=memory_id)

    async def search_memories(
        self,
        payload: SearchMemorySchema,
        user: dict[str, Any],
    ) -> MemorySearchResponseSchema:
        store = self._get_store()
        cfg = self._config(payload.config, user)
        options = payload.options or {}

        results = await store.asearch(
            cfg,
            payload.query,
            memory_type=payload.memory_type,
            category=payload.category,
            limit=payload.limit,
            score_threshold=payload.score_threshold,
            filters=payload.filters,
            retrieval_strategy=payload.retrieval_strategy,
            distance_metric=payload.distance_metric,
            max_tokens=payload.max_tokens,
            **options,
        )
        return MemorySearchResponseSchema(results=results)

    async def get_memory(
        self,
        memory_id: str,
        config: dict[str, Any] | None,
        user: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> MemoryItemResponseSchema:
        store = self._get_store()
        cfg = self._config(config, user)
        result = await store.aget(cfg, memory_id, **(options or {}))
        return MemoryItemResponseSchema(memory=result)

    async def list_memories(
        self,
        config: dict[str, Any] | None,
        user: dict[str, Any],
        limit: int = 100,
        options: dict[str, Any] | None = None,
    ) -> MemoryListResponseSchema:
        store = self._get_store()
        cfg = self._config(config, user)
        memories = await store.aget_all(cfg, limit=limit, **(options or {}))
        return MemoryListResponseSchema(memories=memories)

    async def update_memory(
        self,
        memory_id: str,
        payload: UpdateMemorySchema,
        user: dict[str, Any],
    ) -> MemoryOperationResponseSchema:
        store = self._get_store()
        cfg = self._config(payload.config, user)
        options = payload.options or {}

        result = await store.aupdate(
            cfg,
            memory_id,
            payload.content,
            metadata=payload.metadata,
            **options,
        )
        return MemoryOperationResponseSchema(success=True, data=result)

    async def delete_memory(
        self,
        memory_id: str,
        config: dict[str, Any] | None,
        user: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> MemoryOperationResponseSchema:
        store = self._get_store()
        cfg = self._config(config, user)
        result = await store.adelete(cfg, memory_id, **(options or {}))
        return MemoryOperationResponseSchema(success=True, data=result)

    async def forget_memory(
        self,
        payload: ForgetMemorySchema,
        user: dict[str, Any],
    ) -> MemoryOperationResponseSchema:
        store = self._get_store()
        cfg = self._config(payload.config, user)
        options = payload.options or {}
        forget_kwargs: dict[str, Any] = {
            "memory_type": payload.memory_type,
            "category": payload.category,
            "filters": payload.filters,
        }
        # Remove None values before forwarding to the store
        forget_kwargs = {k: v for k, v in forget_kwargs.items() if v is not None}
        forget_kwargs.update(options)
        result = await store.aforget_memory(cfg, **forget_kwargs)
        return MemoryOperationResponseSchema(success=True, data=result)
