import asyncio

import pytest

from src.app.utils.callable_helper import _is_async_callable, call_sync_or_async


SUM_RESULT = 5
PRODUCT_RESULT = 6


async def _async_fn(x, y):
    await asyncio.sleep(0)
    return x + y


def _sync_fn(x, y):
    return x * y


def test_is_async_callable():
    assert _is_async_callable(_async_fn) is True
    assert _is_async_callable(_sync_fn) is False


@pytest.mark.asyncio
async def test_call_sync_or_async_async():
    res = await call_sync_or_async(_async_fn, 2, 3)
    assert res == SUM_RESULT


@pytest.mark.asyncio
async def test_call_sync_or_async_sync():
    res = await call_sync_or_async(_sync_fn, 2, 3)
    assert res == PRODUCT_RESULT
