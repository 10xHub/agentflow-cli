"""
Swagger Helper Module
Contains helper functions to generate Swagger Responses
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .schemas import (
    ErrorOutputSchema,
    ErrorSchemas,
)


class _SwaggerSuccessSchemas[T](BaseModel):
    """
    Swagger Success Response Schema
    """

    data: T
    metadata: dict = {
        "message": "Success",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
    }


class _SwaggerSuccessPaginationSchemas[T](BaseModel):
    data: T
    metadata: dict = {
        "message": "Success",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
        "pagination": {
            "total": 100,
            "offset": 0,
            "limit": 10,
        },
    }


class _SwaggerError400Schemas(BaseModel):
    metadata: dict = {
        "message": "Failed",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
    }
    error: ErrorOutputSchema = ErrorOutputSchema(
        code="BAD_REQUEST",
        message="Invalid input, please check the input data for any errors",
        details=[],
    )


class _SwaggerError404Schemas(BaseModel):
    metadata: dict = {
        "message": "Failed",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
    }
    error: ErrorOutputSchema = ErrorOutputSchema(
        code="RESOURCE_NOT_FOUND", message="Resource not found", details=[]
    )


class _SwaggerError401Schemas(BaseModel):
    metadata: dict = {
        "message": "Failed",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
    }
    error: ErrorOutputSchema = ErrorOutputSchema(
        code="AUTHENTICATION_FAILED",
        message="Please provide valid credentials",
        details=[],
    )


class _SwaggerError403Schemas(BaseModel):
    metadata: dict = {
        "message": "Failed",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
    }
    error: ErrorOutputSchema = ErrorOutputSchema(
        code="PERMISSION_ERROR",
        message="You don't have permission to access this resource",
        details=[],
    )


class _SwaggerError426Schemas(BaseModel):
    metadata: dict = {
        "message": "Failed",
        "request_id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(),
    }
    error: ErrorOutputSchema = ErrorOutputSchema(
        code="VALIDATION_ERROR",
        message="Invalid input",
        details=[
            ErrorSchemas(
                loc=["body", "name"],
                msg="field required",
                type="value_error.missing",
            )
        ],
    )


def generate_swagger_responses(
    model: type[BaseModel],
    show_pagination: bool = False,
) -> dict[int | str, dict[str, Any]]:
    """
    Generate Swagger Responses Example, based on the provided model.
    This will generate the following responses:
    - 400: Invalid input
    - 404: Resource not found
    - 401: Authentication failed
    - 403: Forbidden
    - 422: Validation error
    - 200: Success

    The 200 response will be based on the provided model. If show_pagination is True,
    then the response will have pagination metadata.
    It will be used to generate redoc and swagger documentation.

    Args:
        model (type[BaseModel]): Base Pydantic Model class, which will be used as response.
        show_pagination (bool, optional): Show Pagination in Swagger Response. Defaults to False.

    Returns:
        dict[int, dict[str, Any]]: Collection of Swagger Responses

    """
    return {
        400: {"model": _SwaggerError400Schemas, "description": "Invalid input"},
        404: {
            "model": _SwaggerError404Schemas,
            "description": "Resource not found",
        },
        401: {
            "model": _SwaggerError401Schemas,
            "description": "Authentication failed",
        },
        403: {"model": _SwaggerError403Schemas, "description": "Forbidden"},
        422: {
            "model": _SwaggerError426Schemas,
            "description": "Validation error",
        },
        200: {
            "model": _SwaggerSuccessPaginationSchemas[model]  # type: ignore
            if show_pagination
            else _SwaggerSuccessSchemas[model],  # type: ignore
        },
    }
