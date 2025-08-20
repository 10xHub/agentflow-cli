from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ErrorSchemas(BaseModel):
    loc: list[str] = Field(..., title="Location")
    msg: str = Field(..., title="Error message")
    type: str = Field(..., title="Error type")


class ErrorOutputSchema(BaseModel):
    code: str = Field(..., title="Error code")
    message: str = Field(..., title="Error message")
    details: list[ErrorSchemas] = Field([], title="Error details")


class ErrorResponse(BaseModel):
    error: ErrorOutputSchema | None = None
    metadata: dict = Field({}, title="Metadata")


class SuccessResponse(BaseModel, Generic[T]):
    data: T | None = None
    metadata: dict = Field({}, title="Metadata")
