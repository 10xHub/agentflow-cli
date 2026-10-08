"""Document extraction service using textxtract.

Wraps ``AsyncTextExtractor`` from the textxtract library.
This module lives in 10xgraph-api, NOT in the core 10xGraph library,
because extraction is an API-platform concern.
"""

from __future__ import annotations

import asyncio
import io
import logging
import zipfile
from pathlib import PurePosixPath
from typing import Any


logger = logging.getLogger("tenxgraph_api.media.extractor")

try:
    from textxtract import AsyncTextExtractor
    from textxtract.core.exceptions import ExtractionError, FileTypeNotSupportedError
except ImportError:  # pragma: no cover
    AsyncTextExtractor = None  # type: ignore[assignment]


# The handler textxtract runs is chosen from the file extension. Uploads never pass their
# own file name through: the declared MIME type picks one of these extensions, and a file
# with any other type (archives included) is not extracted. That keeps a file named
# ``a.zip`` out of textxtract's ZIP handler, which unpacks nested archives with no overall
# size budget.
HANDLER_EXTENSIONS: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/html": ".html",
    "text/xml": ".xml",
    "application/xml": ".xml",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
    "text/plain": ".txt",
}
_EXTRACTABLE_EXTENSIONS = frozenset(HANDLER_EXTENSIONS.values())

# DOCX files are ZIP containers, so they are inspected before parsing: a small upload can
# declare gigabytes of XML.
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_ARCHIVE_ENTRIES = 10_000

EXTRACTION_TIMEOUT_SECONDS = 30.0
MAX_EXTRACTED_CHARS = 1_000_000


def _handler_extension(filename: str | None, mime_type: str | None) -> str | None:
    """The extension (and so the handler) to extract with, or None to skip extraction."""
    if mime_type:
        return HANDLER_EXTENSIONS.get(mime_type.split(";", 1)[0].strip().lower())
    suffix = PurePosixPath(filename or "").suffix.lower()
    return suffix if suffix in _EXTRACTABLE_EXTENSIONS else None


def _check_zip_container(data: bytes) -> None:
    """Reject a ZIP-based document whose contents would expand far beyond its size."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
    except zipfile.BadZipFile as exc:
        raise ValueError("Document is not a valid ZIP-based file") from exc

    if len(entries) > MAX_ARCHIVE_ENTRIES:
        raise ValueError("Document has too many parts to extract")
    total = sum(entry.file_size for entry in entries)
    if total > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise ValueError("Document is too large to extract once uncompressed")
    for entry in entries:
        if entry.file_size > MAX_COMPRESSION_RATIO * max(entry.compress_size, 1):
            raise ValueError(f"Document part {entry.filename!r} has a suspicious compression ratio")


def _as_text(result: Any) -> str | None:
    if result is None:
        return None
    if isinstance(result, list | tuple):
        result = "\n\n".join(str(part) for part in result)
    text = str(result)
    if len(text) > MAX_EXTRACTED_CHARS:
        logger.warning(
            "Extracted text truncated from %d to %d chars", len(text), MAX_EXTRACTED_CHARS
        )
        text = text[:MAX_EXTRACTED_CHARS]
    return text


class DocumentExtractor:
    """Wraps textxtract AsyncTextExtractor for API-side document extraction.

    Examples::

        extractor = DocumentExtractor()
        text = await extractor.extract(pdf_bytes, "report.pdf")
    """

    def __init__(self, extractor: Any | None = None):
        if extractor is not None:
            self.extractor = extractor
            return

        if AsyncTextExtractor is None:
            raise ImportError(
                "textxtract is required for document extraction. "
                'Install with `pip install "10xgraph-api[media]"`'
            )

        self.extractor = AsyncTextExtractor()

    async def extract(
        self,
        data: bytes | str,
        filename: str | None = None,
        mime_type: str | None = None,
    ) -> str | None:
        """Extract text from bytes or a local path.

        For bytes, the handler comes from ``mime_type`` when given, otherwise from the
        extension of ``filename``, and only document types are extracted: archives and
        unknown types return ``None``. The client's file name is never handed to textxtract.

        Args:
            data: Raw bytes or local path.
            filename: Required when passing bytes (used only when ``mime_type`` is absent).
            mime_type: The declared content type; preferred for picking the handler.

        Returns:
            Extracted text (capped at ``MAX_EXTRACTED_CHARS``), or ``None`` when the file
            type is not extracted.

        Raises:
            ValueError: For a missing filename, an oversized or bomb-like document, a
                timeout, or failed extraction.
        """
        if isinstance(data, bytes) and not filename:
            raise ValueError("filename must be provided when extracting from bytes")

        try:
            if isinstance(data, bytes):
                extension = _handler_extension(filename, mime_type)
                if extension is None:
                    logger.info(
                        "Not extracting %s (%s): not a supported document", filename, mime_type
                    )
                    return None
                if extension == ".docx":
                    _check_zip_container(data)
                result = await asyncio.wait_for(
                    self.extractor.extract(data, f"upload{extension}"),
                    timeout=EXTRACTION_TIMEOUT_SECONDS,
                )
                return _as_text(result)
            return _as_text(await self.extractor.extract(data))

        except TimeoutError as exc:
            logger.warning("Document extraction timed out for %s", filename)
            raise ValueError("Document extraction timed out") from exc

        except FileTypeNotSupportedError:  # type: ignore
            logger.warning("Document type not supported for extraction: %s", filename)
            return None
        except ExtractionError as exc:  # type: ignore
            logger.exception("Document extraction failed for %s", filename)
            raise ValueError("Failed to extract text from document") from exc
