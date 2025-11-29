from typing import Any

from pydantic import BaseModel

from agentflow_cli.src.app.core.config.settings import Settings


def parse_state_output(settings: Settings, response: BaseModel) -> dict[str, Any]:
    # if settings.IS_DEBUG:
    #     return response.model_dump(exclude={"execution_meta"}, serialize_as_any=True)
    return response.model_dump(serialize_as_any=True)


def parse_message_output(settings: Settings, response: BaseModel) -> dict[str, Any]:
    # if settings.IS_DEBUG:
    #     return response.model_dump(exclude={"raw"}, serialize_as_any=True)
    return response.model_dump(serialize_as_any=True)
