import os
from typing import Any

import jwt
from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.base_auth import BaseAuth
from agentflow_cli.src.app.core.exceptions import UserAccountError


class JwtAuth(BaseAuth):
    def authenticate(
        self, res: Response, credential: HTTPAuthorizationCredentials
    ) -> dict[str, Any] | None:
        """No authentication is required, so return None."""
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
        jwt_secret_key = os.environ.get("JWT_SECRET_KEY", None)
        jwt_algorithm = os.environ.get("JWT_ALGORITHM", None)

        if jwt_secret_key is None or jwt_algorithm is None:
            raise UserAccountError(
                message="JWT settings are not configured",
                error_code="JWT_SETTINGS_NOT_CONFIGURED",
            )

        try:
            decoded_token = jwt.decode(
                credential.credentials,
                jwt_secret_key,  # type: ignore
                algorithms=[jwt_algorithm],  # type: ignore
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

        # check if user_id exists in the token
        if "user_id" not in decoded_token:
            raise UserAccountError(
                message="Invalid token, user_id missing",
                error_code="INVALID_TOKEN",
            )
        return decoded_token
