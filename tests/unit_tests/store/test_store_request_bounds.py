"""Memory store requests have upper bounds (M11)."""

# ruff: noqa: S101

import pytest
from pydantic import ValidationError

from agentflow_cli.src.app.routers.store.schemas.store_schemas import (
    MAX_LIST_LIMIT,
    MAX_SEARCH_LIMIT,
    MAX_SEARCH_TOKENS,
    ListMemoriesSchema,
    SearchMemorySchema,
)


@pytest.mark.parametrize(
    "fields",
    [{"limit": MAX_SEARCH_LIMIT + 1}, {"max_tokens": MAX_SEARCH_TOKENS + 1}],
)
def test_search_rejects_values_past_the_bound(fields):
    with pytest.raises(ValidationError):
        SearchMemorySchema(query="q", **fields)


def test_search_accepts_the_bound():
    schema = SearchMemorySchema(query="q", limit=MAX_SEARCH_LIMIT, max_tokens=MAX_SEARCH_TOKENS)
    assert schema.limit == MAX_SEARCH_LIMIT


def test_list_rejects_a_limit_past_the_bound():
    with pytest.raises(ValidationError):
        ListMemoriesSchema(limit=MAX_LIST_LIMIT + 1)
    assert ListMemoriesSchema(limit=MAX_LIST_LIMIT).limit == MAX_LIST_LIMIT
