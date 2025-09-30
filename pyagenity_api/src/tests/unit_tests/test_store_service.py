from __future__ import annotations

from typing import Any

import pytest

from pyagenity.store import BaseStore
from pyagenity.utils import Message

from pyagenity_api.src.app.routers.store.schemas.store_schemas import (
    ForgetMemorySchema,
    MemorySearchResponseSchema,
    MemorySearchResult,
    MemoryType,
    SearchMemorySchema,
    StoreMemorySchema,
    UpdateMemorySchema,
)
from pyagenity_api.src.app.routers.store.services.store_service import StoreService


class FakeStore(BaseStore):
    """Minimal in-memory implementation of the BaseStore interface for testing."""

    def __init__(self) -> None:
        self.records: dict[str, MemorySearchResult] = {}
        self.last_config: dict[str, Any] | None = None
        self.last_options: dict[str, Any] | None = None
        self.last_forget_kwargs: dict[str, Any] | None = None

    async def asetup(self) -> Any:  # pragma: no cover - not exercised
        return None

    async def astore(  # type: ignore[override]
        self,
        config: dict[str, Any],
        content: str | Message,
        memory_type: MemoryType = MemoryType.EPISODIC,
        category: str = "general",
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        self.last_config = config
        self.last_options = kwargs or None
        memory_id = f"mem-{len(self.records) + 1}"
        text = content.text() if isinstance(content, Message) else str(content)
        record = MemorySearchResult(
            id=memory_id,
            content=text,
            memory_type=memory_type,
            metadata={"category": category, **(metadata or {})},
        )
        self.records[memory_id] = record
        return memory_id

    async def asearch(  # type: ignore[override]
        self,
        config: dict[str, Any],
        query: str,
        memory_type: MemoryType | None = None,
        category: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
        retrieval_strategy=None,
        distance_metric=None,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> list[MemorySearchResult]:
        self.last_config = config
        self.last_options = kwargs or None
        query_lower = query.lower()
        results: list[MemorySearchResult] = []
        for record in self.records.values():
            if memory_type and record.memory_type != memory_type:
                continue
            if category and record.metadata.get("category") != category:
                continue
            if query_lower in record.content.lower():
                results.append(record)
        return results[:limit]

    async def aget(  # type: ignore[override]
        self,
        config: dict[str, Any],
        memory_id: str,
        **kwargs: Any,
    ) -> MemorySearchResult | None:
        self.last_config = config
        self.last_options = kwargs or None
        return self.records.get(memory_id)

    async def aget_all(  # type: ignore[override]
        self,
        config: dict[str, Any],
        limit: int = 100,
        **kwargs: Any,
    ) -> list[MemorySearchResult]:
        self.last_config = config
        self.last_options = kwargs or None
        return list(self.records.values())[:limit]

    async def aupdate(  # type: ignore[override]
        self,
        config: dict[str, Any],
        memory_id: str,
        content: str | Message,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemorySearchResult | None:
        self.last_config = config
        self.last_options = kwargs or None
        record = self.records.get(memory_id)
        if record:
            record.content = content.text() if isinstance(content, Message) else str(content)
            if metadata is not None:
                record.metadata.update(metadata)
        return record

    async def adelete(  # type: ignore[override]
        self,
        config: dict[str, Any],
        memory_id: str,
        **kwargs: Any,
    ) -> MemorySearchResult | None:
        self.last_config = config
        self.last_options = kwargs or None
        return self.records.pop(memory_id, None)

    async def aforget_memory(  # type: ignore[override]
        self,
        config: dict[str, Any],
        **kwargs: Any,
    ) -> list[MemorySearchResult]:
        self.last_config = config
        self.last_forget_kwargs = kwargs
        removed: list[MemorySearchResult] = []
        for memory_id, record in list(self.records.items()):
            if kwargs.get("memory_type") and record.memory_type != kwargs["memory_type"]:
                continue
            if kwargs.get("category") and record.metadata.get("category") != kwargs["category"]:
                continue
            removed.append(self.records.pop(memory_id))
        return removed

    async def arelease(self) -> None:  # pragma: no cover - not exercised
        return None


@pytest.mark.asyncio
async def test_store_memory_returns_identifier_and_records_metadata():
    store = FakeStore()
    service = StoreService(store)
    payload = StoreMemorySchema(
        content="hello",
        metadata={"tags": ["greeting"]},
        category="support",
        options={"sync": True},
    )
    user = {"id": "user-1"}

    response = await service.store_memory(payload, user)

    assert response.memory_id in store.records
    stored = store.records[response.memory_id]
    assert stored.content == "hello"
    assert stored.metadata["category"] == "support"
    assert store.last_config and store.last_config["user"] == user
    assert store.last_options == {"sync": True}


@pytest.mark.asyncio
async def test_search_memories_returns_matching_results():
    store = FakeStore()
    service = StoreService(store)
    user = {"id": "user-2"}
    await service.store_memory(StoreMemorySchema(content="Hello World"), user)
    await service.store_memory(StoreMemorySchema(content="Another entry"), user)

    payload = SearchMemorySchema(query="hello")
    result = await service.search_memories(payload, user)

    assert isinstance(result, MemorySearchResponseSchema)
    assert len(result.results) == 1
    assert result.results[0].content == "Hello World"


@pytest.mark.asyncio
async def test_update_and_delete_memory_flow():
    store = FakeStore()
    service = StoreService(store)
    user = {"id": "user-3"}
    created = await service.store_memory(StoreMemorySchema(content="old"), user)

    await service.update_memory(
        created.memory_id,
        UpdateMemorySchema(content="new text", metadata={"version": 2}, options={"upsert": True}),
        user,
    )

    assert store.records[created.memory_id].content == "new text"
    UPDATED_VERSION = 2
    assert store.records[created.memory_id].metadata["version"] == UPDATED_VERSION
    assert store.last_options == {"upsert": True}

    await service.delete_memory(created.memory_id, {}, user)
    assert created.memory_id not in store.records


@pytest.mark.asyncio
async def test_forget_memory_applies_filters_and_options():
    store = FakeStore()
    service = StoreService(store)
    user = {"id": "user-4"}
    await service.store_memory(
        StoreMemorySchema(content="keep", memory_type=MemoryType.EPISODIC, category="keep"),
        user,
    )
    await service.store_memory(
        StoreMemorySchema(content="remove", memory_type=MemoryType.SEMANTIC, category="remove"),
        user,
    )

    await service.forget_memory(
        ForgetMemorySchema(memory_type=MemoryType.SEMANTIC, options={"dry_run": False}),
        user,
    )

    assert len(store.records) == 1
    assert store.last_forget_kwargs and store.last_forget_kwargs["dry_run"] is False


@pytest.mark.asyncio
async def test_service_raises_when_store_not_configured():
    service = StoreService(None)
    with pytest.raises(ValueError):
        await service.list_memories({}, {"id": "user-5"})
