"""File upload, retrieval, and multimodal config endpoints."""

from __future__ import annotations

import mimetypes
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.logger import logger
from fastapi.responses import Response
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core.auth.permissions import RequirePermission
from agentflow_cli.src.app.core.config.media_settings import get_media_settings
from agentflow_cli.src.app.routers.media import MediaService
from agentflow_cli.src.app.routers.media.schemas import (
    FileAccessUrlResponse,
    FileInfoResponse,
    FileUploadResponse,
    MultimodalConfigResponse,
)
from agentflow_cli.src.app.utils import success_response


router = APIRouter(tags=["Files"])

# Read uploads in 1 MiB chunks so a size-cap breach is caught before the whole body
# is buffered in memory.
_UPLOAD_CHUNK_BYTES = 1024 * 1024


# ------------------------------------------------------------------
# 4.1  POST /v1/files/upload
# ------------------------------------------------------------------
@router.post(
    "/v1/files/upload",
    summary="Upload a file (image, audio, document)",
    response_model=FileUploadResponse,
    description=(
        "Accepts a multipart file upload.  Stores binary in the configured "
        "MediaStore and optionally extracts text for documents."
    ),
)
async def upload_file(
    request: Request,
    file: UploadFile,
    service: MediaService = InjectAPI(MediaService),
    user: dict[str, Any] = Depends(RequirePermission("files", "upload")),
):
    if file.filename is None:
        raise HTTPException(status_code=400, detail="filename is required")

    media_settings = get_media_settings()
    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    if not media_settings.is_content_type_allowed(mime):
        raise HTTPException(status_code=415, detail=f"Content type not allowed: {mime}")

    # Read with a running size cap instead of ``await file.read()``. A chunked upload
    # (no Content-Length) slips past RequestSizeLimitMiddleware, so a naive full read
    # would let a multi-GB body OOM-kill the worker. Stop as soon as we exceed the
    # limit and reject, never materializing more than max_size + one chunk.
    max_bytes = int(media_settings.MEDIA_MAX_SIZE_MB * 1024 * 1024)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum {media_settings.MEDIA_MAX_SIZE_MB}MB",
            )
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    logger.info("File upload: %s (%s, %d bytes)", file.filename, mime, len(data))

    try:
        # Record the uploader as the owner, so the file cannot later be read by a
        # different user who knows the id.
        result = await service.upload_file(
            data, file.filename, mime, user_id=user.get("user_id")
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    return success_response(FileUploadResponse(**result), request)


# ------------------------------------------------------------------
# 4.2  GET /v1/files/{file_id}  — raw binary download
# ------------------------------------------------------------------
@router.get(
    "/v1/files/{file_id}",
    summary="Retrieve file binary",
    description="Returns the raw binary with the correct Content-Type.",
)
async def get_file(
    file_id: str,
    service: MediaService = InjectAPI(MediaService),
    user: dict[str, Any] = Depends(RequirePermission("files", "read")),
):
    try:
        # Authentication alone is not enough: without this, ANY authenticated user
        # who knew a file_id could download another user's file.
        await service.ensure_can_access(file_id, user.get("user_id"))
        data, mime_type = await service.get_file(file_id, user.get("user_id"))
    except KeyError:
        raise HTTPException(status_code=404, detail="File not found")
    except PermissionError:
        # 404, not 403: do not confirm that someone else's file_id exists.
        raise HTTPException(status_code=404, detail="File not found")

    return Response(content=data, media_type=mime_type)


# ------------------------------------------------------------------
# 4.2  GET /v1/files/{file_id}/info  — metadata only
# ------------------------------------------------------------------
@router.get(
    "/v1/files/{file_id}/info",
    summary="Retrieve file metadata",
    response_model=FileInfoResponse,
)
async def get_file_info(
    request: Request,
    file_id: str,
    service: MediaService = InjectAPI(MediaService),
    user: dict[str, Any] = Depends(RequirePermission("files", "read")),
):
    try:
        await service.ensure_can_access(file_id, user.get("user_id"))
        info = await service.get_file_info(file_id, user.get("user_id"))
    except KeyError:
        raise HTTPException(status_code=404, detail="File not found")
    except PermissionError:
        raise HTTPException(status_code=404, detail="File not found")

    return success_response(FileInfoResponse(**info), request)


@router.get(
    "/v1/files/{file_id}/url",
    summary="Retrieve direct access URL",
    response_model=FileAccessUrlResponse,
)
async def get_file_access_url(
    request: Request,
    file_id: str,
    service: MediaService = InjectAPI(MediaService),
    user: dict[str, Any] = Depends(RequirePermission("files", "read")),
):
    try:
        # Especially important here: this hands out a *signed direct URL*, which
        # bypasses the API entirely. Handing one to a non-owner would leak the file
        # even after this check was added elsewhere.
        await service.ensure_can_access(file_id, user.get("user_id"))
        info = await service.get_file_info(file_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="File not found")
    except PermissionError:
        raise HTTPException(status_code=404, detail="File not found")

    payload = FileAccessUrlResponse(
        file_id=file_id,
        url=info["direct_url"] or f"/v1/files/{file_id}",
        expires_at=info.get("direct_url_expires_at"),
        mime_type=info["mime_type"],
    )
    return success_response(payload, request)


# ------------------------------------------------------------------
# 4.4  GET /v1/config/multimodal  — read current multimodal config
# ------------------------------------------------------------------
@router.get(
    "/v1/config/multimodal",
    summary="Get multimodal configuration",
    response_model=MultimodalConfigResponse,
)
async def get_multimodal_config(
    request: Request,
    user: dict[str, Any] = Depends(RequirePermission("config", "read")),
):
    settings = get_media_settings()
    return success_response(
        MultimodalConfigResponse(
            media_storage_type=settings.MEDIA_STORAGE_TYPE.value,
            media_storage_path=settings.MEDIA_STORAGE_PATH,
            media_max_size_mb=settings.MEDIA_MAX_SIZE_MB,
            document_handling=settings.DOCUMENT_HANDLING,
        ),
        request,
    )
