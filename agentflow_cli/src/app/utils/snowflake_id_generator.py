import os
from enum import Enum
from importlib.util import find_spec


class IDType(Enum):
    BIGINT = "bigint"


class BaseIDGenerator:
    @property
    def id_type(self) -> IDType:
        raise NotImplementedError


# Check if snowflakekit is available
HAS_SNOWFLAKE = find_spec("snowflakekit") is not None


class SnowFlakeIdGenerator(BaseIDGenerator):
    def __init__(
        self,
        snowflake_epoch: int | None = None,
        total_bits: int | None = None,
        snowflake_time_bits: int | None = None,
        snowflake_node_bits: int | None = None,
        snowflake_node_id: int | None = None,
        snowflake_worker_id: int | None = None,
        snowflake_worker_bits: int | None = None,
    ):
        # IF all these are None then try to read from env
        config = None
        if not HAS_SNOWFLAKE:
            raise ImportError(
                "snowflakekit is not installed. Please install it to use SnowFlakeIdGenerator."
            )

        from snowflakekit import SnowflakeConfig, SnowflakeGenerator

        if (
            snowflake_epoch is None
            and total_bits is None
            and snowflake_time_bits is None
            and snowflake_node_bits is None
            and snowflake_node_id is None
            and snowflake_worker_id is None
            and snowflake_worker_bits is None
        ):
            snowflake_epoch = int(os.environ.get("SNOWFLAKE_EPOCH", "1723323246031"))
            total_bits = int(os.environ.get("SNOWFLAKE_TOTAL_BITS", "64"))
            snowflake_time_bits = int(os.environ.get("SNOWFLAKE_TIME_BITS", "39"))
            snowflake_node_bits = int(os.environ.get("SNOWFLAKE_NODE_BITS", "7"))
            snowflake_node_id = int(os.environ.get("SNOWFLAKE_NODE_ID", "0"))
            snowflake_worker_id = int(os.environ.get("SNOWFLAKE_WORKER_ID", "0"))
            snowflake_worker_bits = int(os.environ.get("SNOWFLAKE_WORKER_BITS", "5"))

            config = SnowflakeConfig(
                epoch=snowflake_epoch,
                total_bits=total_bits,
                time_bits=snowflake_time_bits,
                node_bits=snowflake_node_bits,
                node_id=snowflake_node_id,
                worker_id=snowflake_worker_id,
                worker_bits=snowflake_worker_bits,
            )

        elif (
            snowflake_epoch is not None
            and total_bits is not None
            and snowflake_time_bits is not None
            and snowflake_node_bits is not None
            and snowflake_node_id is not None
            and snowflake_worker_id is not None
            and snowflake_worker_bits is not None
        ):
            config = SnowflakeConfig(
                epoch=snowflake_epoch,
                total_bits=total_bits,
                time_bits=snowflake_time_bits,
                node_bits=snowflake_node_bits,
                node_id=snowflake_node_id,
                worker_id=snowflake_worker_id,
                worker_bits=snowflake_worker_bits,
            )

        # Now create generator
        self.generator = SnowflakeGenerator(config=config)

    @property
    def id_type(self) -> IDType:
        return IDType.BIGINT

    async def generate(self) -> int:
        """Generate a new Snowflake ID.

        Returns:
            int: A new Snowflake ID.
        """
        return await self.generator.generate()
