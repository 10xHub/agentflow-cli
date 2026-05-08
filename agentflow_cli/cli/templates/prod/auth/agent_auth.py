from typing import Any

from agentflow_cli import BaseAuth
from fastapi import Request, Response
from fastapi.security import HTTPAuthorizationCredentials


class AgentAuth(BaseAuth):
    def authenticate(
        self,
        request: Request,
        response: Response,
        credential: HTTPAuthorizationCredentials,
    ) -> dict[str, Any] | None:
        # TODO: Implement actual authentication logic here

        return {
            "user_id": "random_user_id",
        }
