from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from tortoise.exceptions import (
    DoesNotExist,
    IntegrityError,
    MultipleObjectsReturned,
)

from src.app.core import logger
from src.app.utils import error_response
from src.app.utils.schemas import ErrorSchemas

from .resources_exceptions import ResourceNotFoundError
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
        DoesNotExist: Handles Tortoise ORM DoesNotExist exceptions.
        IntegrityError: Handles Tortoise ORM IntegrityError exceptions.
        MultipleObjectsReturned: Handles Tortoise ORM MultipleObjectsReturned exceptions.
        UserAccountError: Handles custom user account errors.
        UserPermissionError: Handles custom user permission errors.
        ResourceNotFoundError: Handles custom resource not found errors.
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
    ### Tortoise exception handler here ####
    ########################################
    @app.exception_handler(DoesNotExist)
    async def not_found_exception_handler(request: Request, exc: DoesNotExist):
        logger.error(f"Not found exception: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code="RESOURCE_NOT_FOUND",
            message="Requested Resource Not Found",
            status_code=404,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        logger.error(f"Integrity exception: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code="INTEGRITY_ERROR",
            message=str(exc),
            status_code=400,
        )

    @app.exception_handler(MultipleObjectsReturned)
    async def multiple_object_exception_handler(request: Request, exc: MultipleObjectsReturned):
        logger.error(f"Integrity exception: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code="MULTIPLE_OBJECTS_RETURNED",
            message=str(exc),
            status_code=400,
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

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
        logger.error(f"ResourceNotFoundError: url: {request.base_url}", exc_info=exc)
        return error_response(
            request,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )
