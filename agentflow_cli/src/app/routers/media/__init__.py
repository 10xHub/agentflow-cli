"""Media service — provides the configured MediaStore and DocumentPipeline."""

from __future__ import annotations

import logging
from typing import Any

from agentflow.media.config import DocumentHandling
from agentflow.media.storage.base import BaseMediaStore
from injectq import inject, singleton

from agentflow_cli.media.extractor import DocumentExtractor
from agentflow_cli.media.pipeline import DocumentPipeline
from agentflow_cli.src.app.core.config.media_settings import MediaSettings, MediaStorageType

logger = logging.getLogger("agentflow-cli.media")


def _create_media_store(settings: MediaSettings) -> BaseMediaStore:
    """Factory that instantiates the right MediaStore from settings."""
    stype = settings.MEDIA_STORAGE_TYPE

    if stype == MediaStorageType.MEMORY:
        from agentflow.media.storage.memory_store import InMemoryMediaStore

        return InMemoryMediaStore()

    if stype == MediaStorageType.LOCAL:
        from agentflow.media.storage.local_store import LocalFileMediaStore

        return LocalFileMediaStore(base_dir=settings.MEDIA_STORAGE_PATH)

    if stype == MediaStorageType.CLOUD:
        from agentflow.media.storage.cloud_store import CloudMediaStore

        return CloudMediaStore(
            provider=settings.MEDIA_CLOUD_PROVIDER,
            bucket=settings.MEDIA_CLOUD_BUCKET,
            region=settings.MEDIA_CLOUD_REGION,
        )

    if stype == MediaStorageType.PG:
        from agentflow.media.storage.pg_store import PgBlobStore

        return PgBlobStore()

    raise ValueError(f"Unknown MEDIA_STORAGE_TYPE: {stype}")


def _create_document_pipeline(settings: MediaSettings) -> DocumentPipeline:
    handling_map = {
        "extract_text": DocumentHandling.EXTRACT_TEXT,
        "pass_raw": DocumentHandling.PASS_RAW,
        "skip": DocumentHandling.SKIP,
    }
    handling = handling_map.get(settings.DOCUMENT_HANDLING, DocumentHandling.EXTRACT_TEXT)

    extractor = DocumentExtractor() if handling == DocumentHandling.EXTRACT_TEXT else None
    return DocumentPipeline(document_extractor=extractor, handling=handling)


@singleton
class MediaService:
    """Central media service providing storage + document extraction."""

    @inject
    def __init__(self, settings: MediaSettings | None = None):
        from agentflow_cli.src.app.core.config.media_settings import get_media_settings

        self._settings = settings or get_media_settings()
        self._store: BaseMediaStore | None = None
        self._pipeline: DocumentPipeline | None = None
        self._extraction_cache: dict[str, str] = {}  # file_id -> extracted text

    @property
    def store(self) -> BaseMediaStore:
        if self._store is None:
            self._store = _create_media_store(self._settings)
        return self._store

    @property
    def pipeline(self) -> DocumentPipeline:
        if self._pipeline is None:
            self._pipeline = _create_document_pipeline(self._settings)
        return self._pipeline

    @property
    def max_size_bytes(self) -> int:
        return int(self._settings.MEDIA_MAX_SIZE_MB * 1024 * 1024)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    async def upload_file(
        self,
        data: bytes,
        filename: str,
        mime_type: str,
    ) -> dict[str, Any]:
        """Upload a file: store binary + optionally extract text.

        Returns a dict with file_id, mime_type, size_bytes, filename,
        extracted_text (nullable), and url.
        """
        if len(data) > self.max_size_bytes:
            raise ValueError(
                f"File size {len(data)} exceeds maximum "
                f"{self._settings.MEDIA_MAX_SIZE_MB}MB"
            )

        # Store binary in the configured MediaStore
        storage_key = await self.store.store(
            data,
            mime_type,
            metadata={"filename": filename},
        )

        result: dict[str, Any] = {
            "file_id": storage_key,
            "mime_type": mime_type,
            "size_bytes": len(data),
            "filename": filename,
            "extracted_text": None,
            "url": f"/v1/files/{storage_key}",
        }

        # If it's a document, try extraction
        if self._is_extractable(mime_type):
            try:
                text = await self.pipeline.extractor.extract(data, filename)
                if text:
                    result["extracted_text"] = text
                    self._extraction_cache[storage_key] = text
            except Exception as exc:
                logger.warning("Extraction failed for %s: %s", filename, exc)

        return result

    async def get_file(self, file_id: str) -> tuple[bytes, str]:
        """Retrieve file bytes and MIME type."""
        return await self.store.retrieve(file_id)

    async def get_file_info(self, file_id: str) -> dict[str, Any]:
        """Return metadata about a stored file."""
        exists = await self.store.exists(file_id)
        if not exists:
            raise KeyError(f"File not found: {file_id}")

        data, mime_type = await self.store.retrieve(file_id)
        return {
            "file_id": file_id,
            "mime_type": mime_type,
            "size_bytes": len(data),
            "extracted_text": self._extraction_cache.get(file_id),
        }

    def get_cached_extraction(self, file_id: str) -> str | None:
        """Return cached extracted text for a file_id."""
        return self._extraction_cache.get(file_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_extractable(mime_type: str) -> bool:
        extractable = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "text/html",
            "text/xml",
            "application/xml",
            "text/markdown",
            "text/csv",
            "application/json",
            "text/plain",
        }
        return mime_type.lower() in extractable
