from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from agentflow_cli import BaseAuth


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
