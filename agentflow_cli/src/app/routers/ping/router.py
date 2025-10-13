from fastapi import APIRouter, Request

from agentflow_cli.src.app.utils.response_helper import success_response
from agentflow_cli.src.app.utils.swagger_helper import generate_swagger_responses


router = APIRouter(
    tags=["Ping"],
)


@router.get(
    "/v1/ping",
    summary="Ping the server",
    responses=generate_swagger_responses(str),  # type: ignore
    description="Check the server's health",
    openapi_extra={},
)
async def ping_server(
    request: Request,
):
    """
    Invoke the graph with the provided input and return the final result.
    """
    return success_response(
        "pong",
        request,
    )
