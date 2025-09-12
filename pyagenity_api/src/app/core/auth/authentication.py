from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import Response

from src.app.core import logger
from src.app.core.config.settings import get_settings
from src.app.core.exceptions import UserAccountError


def verify_jwt(
    res: Response,
    credential: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False),
    ),
) -> dict[str, Any]:
    """
    Get the current user based on the provided HTTP
    Authorization credentials.

    Args:
        res (Response): The response object to set headers if needed.
        credential (HTTPAuthorizationCredentials): The HTTP Authorization
        credentials obtained from the request.

    Returns:
        UserSchema: A UserSchema object containing the decoded user information.

    Raises:
        HTTPException: If the credentials are missing.
        UserAccountError: If there are token verification errors such as
            RevokedIdTokenError,
            UserDisabledError,
            InvalidIdTokenError,
            or any other unexpected exceptions.
    """
    if credential is None:
        raise UserAccountError(
            message="Invalid token, please login again",
            error_code="REVOKED_TOKEN",
        )
    settings = get_settings()

    if settings.JWT_SECRET_KEY is None or settings.JWT_ALGORITHM is None:
        raise UserAccountError(
            message="JWT settings are not configured",
            error_code="JWT_SETTINGS_NOT_CONFIGURED",
        )

    try:
        decoded_token = jwt.decode(
            credential.credentials,
            settings.JWT_SECRET_KEY,  # type: ignore
            algorithms=[settings.JWT_ALGORITHM],  # type: ignore
        )
    except jwt.ExpiredSignatureError:
        raise UserAccountError(
            message="Token has expired, please login again",
            error_code="EXPIRED_TOKEN",
        )
    except jwt.InvalidTokenError as err:
        logger.exception("JWT AUTH ERROR", exc_info=err)
        raise UserAccountError(
            message="Invalid token, please login again",
            error_code="INVALID_TOKEN",
        )
    res.headers["WWW-Authenticate"] = 'Bearer realm="auth_required"'
    return decoded_token
