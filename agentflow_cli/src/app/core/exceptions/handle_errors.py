# Handle all exceptions of agentflow here
from agentflow.exceptions import (
    GraphError,
    GraphRecursionError,
    MetricsError,
    NodeError,
    SchemaVersionError,
    SerializationError,
    StorageError,
    TransientStorageError,
)
from agentflow.utils.validators import ValidationError
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.utils import error_response
from agentflow_cli.src.app.utils.schemas import ErrorSchemas

from .resources_exceptions import ResourceNotFoundError as APIResourceNotFoundError
from .user_exception import (
    UserAccountError,
    UserPermissionError,
)


def init_errors_handler(app: FastAPI):
    """
    Initialize error handlers for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.

    Raises:
        HTTPException: Handles HTTP exceptions.
        RequestValidationError: Handles request validation errors.
        ValueError: Handles value errors.
        UserAccountError: Handles custom user account errors.
        UserPermissionError: Handles custom user permission errors.
        APIResourceNotFoundError: Handles custom API resource not found errors.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP exception: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code="HTTPException",
            message=str(exc.detail),
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Value error exception: url: {request.base_url}", exc_info=exc)
        details = [ErrorSchemas(**error) for error in exc.errors()]
        return error_response(
            request,
            error_code="VALIDATION_ERROR",
            message=str(exc.body),
            details=details,
            status_code=422,
        )

    @app.exception_handler(ValueError)
    async def value_exception_handler(request: Request, exc: ValueError):
        logger.error(f"Value error exception: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code="VALIDATION_ERROR",
            message=str(exc),
            status_code=422,
        )

    ########################################
    ##### Custom exception handler here ####
    ########################################
    @app.exception_handler(UserAccountError)
    async def user_account_exception_handler(request: Request, exc: UserAccountError):
        logger.error(f"UserAccountError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )

    @app.exception_handler(UserPermissionError)
    async def user_write_exception_handler(request: Request, exc: UserPermissionError):
        logger.error(f"UserPermissionError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )

    @app.exception_handler(APIResourceNotFoundError)
    async def resource_not_found_exception_handler(request: Request, exc: APIResourceNotFoundError):
        logger.error(f"ResourceNotFoundError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )

    ## Need to handle agentflow specific exceptions here
    @app.exception_handler(ValidationError)
    async def agentflow_validation_exception_handler(request: Request, exc: ValidationError):
        logger.error(f"AgentFlow ValidationError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code="AGENTFLOW_VALIDATION_ERROR",
            message=str(exc),
            status_code=422,
        )

    @app.exception_handler(GraphError)
    async def graph_error_exception_handler(request: Request, exc: GraphError):
        logger.error(f"GraphError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "GRAPH_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=500,
        )

    @app.exception_handler(NodeError)
    async def node_error_exception_handler(request: Request, exc: NodeError):
        logger.error(f"NodeError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "NODE_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=500,
        )

    @app.exception_handler(GraphRecursionError)
    async def graph_recursion_error_exception_handler(request: Request, exc: GraphRecursionError):
        logger.error(f"GraphRecursionError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "GRAPH_RECURSION_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=500,
        )

    @app.exception_handler(MetricsError)
    async def metrics_error_exception_handler(request: Request, exc: MetricsError):
        logger.error(f"MetricsError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "METRICS_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=500,
        )

    @app.exception_handler(SchemaVersionError)
    async def schema_version_error_exception_handler(request: Request, exc: SchemaVersionError):
        logger.error(f"SchemaVersionError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "SCHEMA_VERSION_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=422,
        )

    @app.exception_handler(SerializationError)
    async def serialization_error_exception_handler(request: Request, exc: SerializationError):
        logger.error(f"SerializationError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "SERIALIZATION_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=500,
        )

    @app.exception_handler(StorageError)
    async def storage_error_exception_handler(request: Request, exc: StorageError):
        logger.error(f"StorageError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "STORAGE_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=500,
        )

    @app.exception_handler(TransientStorageError)
    async def transient_storage_error_exception_handler(
        request: Request, exc: TransientStorageError
    ):
        logger.error(f"TransientStorageError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=getattr(exc, "error_code", "TRANSIENT_STORAGE_000"),
            message=getattr(exc, "message", str(exc)),
            details=getattr(exc, "context", None),
            status_code=503,
        )
