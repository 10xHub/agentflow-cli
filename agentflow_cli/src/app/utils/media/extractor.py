"""Document extraction service using textxtract.

Wraps ``AsyncTextExtractor`` from the textxtract library.
This module lives in pyagenity-api, NOT in the core PyAgenity library,
because extraction is an API-platform concern.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger("agentflow_cli.media.extractor")

try:
    from textxtract import AsyncTextExtractor
    from textxtract.core.exceptions import ExtractionError, FileTypeNotSupportedError
except ImportError:  # pragma: no cover
    AsyncTextExtractor = None  # type: ignore[assignment]


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
                "Install with `pip install textxtract[pdf,docx,html,xml,md]`"
            )

        self.extractor = AsyncTextExtractor()

    async def extract(self, data: bytes | str, filename: str | None = None) -> str | None:
        """Extract text from bytes or a local path.

        Args:
            data: Raw bytes or local path.
            filename: Required when passing bytes so type can be detected.

        Returns:
            Extracted text, or ``None`` when file type is unsupported.

        Raises:
            ValueError: For missing filename or failed extraction.
        """
        if isinstance(data, bytes) and not filename:
            raise ValueError("filename must be provided when extracting from bytes")

        try:
            if isinstance(data, bytes):
                if filename is None:
                    raise ValueError("filename must be provided when extracting from bytes")
                return await self.extractor.extract(data, filename)
            return await self.extractor.extract(data)

        except FileTypeNotSupportedError:  # type: ignore
            logger.warning("Document type not supported for extraction: %s", filename)
            return None
        except ExtractionError as exc:  # type: ignore
            logger.exception("Document extraction failed for %s", filename)
            raise ValueError("Failed to extract text from document") from exc
