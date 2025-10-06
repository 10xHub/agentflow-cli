import importlib

import pytest
from pydantic import BaseModel

from pyagenity_api.src.app.utils.swagger_helper import generate_swagger_responses


class DemoModel(BaseModel):
    id: int
    name: str


def test_generate_swagger_responses_basic():
    responses = generate_swagger_responses(DemoModel)
    assert 200 in responses
    assert responses[200]["model"].__name__.startswith("_SwaggerSuccessSchemas")
    assert responses[400]["description"] == "Invalid input"


def test_generate_swagger_responses_pagination():
    responses = generate_swagger_responses(DemoModel, show_pagination=True)
    assert responses[200]["model"].__name__.startswith("_SwaggerSuccessPaginationSchemas")


@pytest.mark.skipif(
    importlib.util.find_spec("snowflakekit") is None, reason="snowflakekit not installed"
)
def test_snowflake_id_generator_sequence():  # pragma: no cover - executed only if dependency present
    from pyagenity_api.src.app.utils.snowflake_id_generator import SnowFlakeIdGenerator

    # Use explicit config to avoid env dependence
    gen = SnowFlakeIdGenerator(
        snowflake_epoch=1609459200000,
        total_bits=64,
        snowflake_time_bits=39,
        snowflake_node_bits=7,
        snowflake_node_id=1,
        snowflake_worker_id=1,
        snowflake_worker_bits=5,
    )

    import asyncio

    async def _generate_many():
        ids = [await gen.generate() for _ in range(3)]
        return ids

    ids = asyncio.run(_generate_many())
    # Ensure strictly increasing sequence
    assert ids == sorted(ids)
    assert len(set(ids)) == 3
