import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI

from .checkpointer.router import router as checkpointer_router
from .evals import router as evals_router
from .graph import router as graph_router
from .graph import ws_router as graph_ws_router
from .media.router import router as media_router
from .ping.router import router as ping_router
from .store import router as store_router


if TYPE_CHECKING:
    from agentflow_cli.src.app.core.config.graph_config import GraphConfig


logger = logging.getLogger("agentflow_api")


# Routers the ``routers`` block in agentflow.json can switch off, keyed by the name used
# there. The names must match TOGGLEABLE_ROUTERS in graph_config, which is what validates
# them; this table decides what each one actually mounts. ``websocket`` is in
# TOGGLEABLE_ROUTERS but not here: it has a second spelling and is resolved separately by
# :func:`websocket_enabled`.
OPTIONAL_ROUTERS: tuple[tuple[str, APIRouter], ...] = (
    ("checkpointer", checkpointer_router),
    ("store", store_router),
    ("evals", evals_router),
    ("media", media_router),
)


def websocket_enabled(graph_config: "GraphConfig | None") -> bool:
    """Whether ``/v1/graph/ws`` should be mounted.

    The endpoint can be switched off from either spelling in agentflow.json --
    ``websocket.enabled`` or ``routers.websocket`` -- so that neither place is the "wrong"
    one to write it. Setting both is fine. When they disagree the endpoint stays unmounted
    and the mismatch is logged: this is a surface-reduction switch, so a config that says
    "off" anywhere must never end up serving.
    """
    if graph_config is None:
        return True

    websocket_config = graph_config.websocket
    routers_config = graph_config.routers
    from_block = websocket_config.enabled
    from_routers = routers_config.is_enabled("websocket")

    both_written = websocket_config.enabled_declared and "websocket" in routers_config.declared
    if both_written and from_block != from_routers:
        logger.warning(
            "websocket.enabled (%s) and routers.websocket (%s) disagree in agentflow.json; "
            "leaving /v1/graph/ws unmounted. Remove one of the two to silence this.",
            from_block,
            from_routers,
        )

    return from_block and from_routers


def init_routes(app: FastAPI, graph_config: "GraphConfig | None" = None):
    """
    Initialize the routes for the FastAPI application.

    The graph router and ``/ping`` are always mounted. The rest are mounted unless
    agentflow.json turns them off:

    - ``routers`` drops a whole router (``checkpointer``, ``store``, ``evals``, ``media``),
      so a deployment ships only the surface it uses.
    - the streaming endpoint ``/v1/graph/ws`` drops on its own, leaving the rest of the graph
      router in place. Write it as ``routers.websocket`` or as ``websocket.enabled``,
      whichever you prefer; see :func:`websocket_enabled`.

    A route that is not mounted has no handler, dependency, or auth code behind it: an HTTP
    path returns 404 and a WebSocket handshake is refused with HTTP 403. Passing no config
    mounts everything, which is what the default configuration does.

    Args:
        app (FastAPI): The FastAPI application instance to which the routes
        will be added.
        graph_config (GraphConfig | None): Parsed agentflow.json, used to decide which
        routers are mounted. ``None`` mounts everything.
    """
    app.include_router(graph_router)

    if websocket_enabled(graph_config):
        app.include_router(graph_ws_router)
    else:
        logger.info(
            "WebSocket streaming endpoint /v1/graph/ws is disabled in agentflow.json "
            "(websocket.enabled or routers.websocket = false)"
        )

    for name, router in OPTIONAL_ROUTERS:
        if graph_config is None or graph_config.routers.is_enabled(name):
            app.include_router(router)
        else:
            logger.info(
                "Router '%s' is disabled (routers.%s = false in agentflow.json)", name, name
            )

    app.include_router(ping_router)
