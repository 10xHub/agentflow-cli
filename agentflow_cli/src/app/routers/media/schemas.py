"""Schemas for the media / file upload endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    file_id: str = Field(..., description="Opaque storage key")
    mime_type: str
    size_bytes: int
    filename: str
    extracted_text: str | None = None
    url: str = Field(..., description="Relative retrieval URL")


class FileInfoResponse(BaseModel):
    file_id: str
    mime_type: str
    size_bytes: int
    extracted_text: str | None = None


class MultimodalConfigResponse(BaseModel):
    media_storage_type: str
    media_storage_path: str
    media_max_size_mb: float
    document_handling: str
