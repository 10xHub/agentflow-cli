from fastapi import Request
from strawberry.fastapi import BaseContext

from src.app.utils.schemas import AuthUserSchema


class CustomContext(BaseContext):
    """
    Custom context for GraphQL requests.

    Args:
        request (Request): The incoming HTTP request.
        user (AuthUserSchema): The authenticated user schema.

    Attributes:
        request (Request): Stores the incoming HTTP request.
        user (AuthUserSchema): Stores the authenticated user schema.
    """

    def __init__(self, request: Request, user: AuthUserSchema):
        super().__init__()
        self.request = request
        self.user = user
