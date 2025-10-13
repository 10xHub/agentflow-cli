from typing import Any

from fastapi import Depends, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.base_auth import BaseAuth
from agentflow_cli.src.app.core.config.graph_config import GraphConfig


def verify_current_user(
    res: Response,
    credential: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False),
    ),
    config: GraphConfig = InjectAPI(GraphConfig),
    auth_backend: BaseAuth = InjectAPI(BaseAuth),
) -> dict[str, Any]:
    # check auth backend
    user = {}
    backend = config.auth_config()
    if not backend:
        return user

    if not auth_backend:
        logger.error("Auth backend is not configured")
        return user

    user: dict | None = auth_backend.authenticate(res, credential)
    if user and "user_id" not in user:
        logger.error("Authentication failed: 'user_id' not found in user info")
    return user or {}
