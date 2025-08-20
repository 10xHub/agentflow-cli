import orjson
import strawberry
from fastapi import Depends, Request
from strawberry.fastapi import GraphQLRouter
from strawberry.http import GraphQLHTTPResponse
from strawberry.schema.config import StrawberryConfig
from strawberry.types import ExecutionResult

from src.app.core.auth import get_current_user
from src.app.routers.graphql.schemas import Query
from src.app.utils import error_response, success_response
from src.app.utils.schemas import AuthUserSchema, ErrorSchemas

from .context import CustomContext


class MyGraphQLRouter(GraphQLRouter):
    async def process_result(
        self, request: Request, result: ExecutionResult
    ) -> GraphQLHTTPResponse:
        """
        Overwrite the default process_result to return a GraphQLHTTPResponse with
        error details if there are errors in the result.

        Args:
            request (Request): The FastAPI request object.
            result (ExecutionResult): The result of the GraphQL query.

        Returns:
            GraphQLHTTPResponse: The processed GraphQLHTTPResponse object.
        """
        if result.errors:
            return orjson.loads(
                error_response(
                    request,
                    "VALIDATION_ERROR",
                    details=[
                        ErrorSchemas(
                            loc=err.path,
                            msg=err.formatted.get("message"),
                            type=err.formatted.get("type", ""),
                        )
                        for err in result.errors
                    ],
                ).body
            )
        return orjson.loads(success_response(result.data, request).body)


async def custom_context_dependency(
    request: Request, user: AuthUserSchema = Depends(get_current_user)
) -> CustomContext:
    """
    Generate a CustomContext object based on the request and user.

    Args:
        request (Request): The FastAPI request object.
        user (AuthUserSchema): The authenticated user information.

    Returns:
        CustomContext: The generated CustomContext object.

    """
    return CustomContext(request, user)


async def get_context(
    custom_context: CustomContext = Depends(custom_context_dependency),
) -> CustomContext:
    return custom_context


schema = strawberry.Schema(Query, config=StrawberryConfig(auto_camel_case=False))

graphql_app = MyGraphQLRouter(schema, context_getter=get_context, allow_queries_via_get=True)
