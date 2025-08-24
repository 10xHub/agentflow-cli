from typing import Any

from fastapi import Depends, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.app.core.config.settings import get_settings

from .authentication import verify_jwt


def verify_current_user(
    res: Response,
    credential: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False),
    ),
) -> dict[str, Any]:
    # check auth backend
    user = {}
    settings = get_settings()

    if settings.AUTH_BACKEND == "jwt":
        # now check keys
        user = verify_jwt(res, credential)
    return user or {}
