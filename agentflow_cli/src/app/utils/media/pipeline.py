"""Document processing pipeline for the API layer.

Orchestrates: receive uploaded file -> extract text via DocumentExtractor
-> return TextBlock or DocumentBlock depending on config.
"""

from __future__ import annotations

import logging
from base64 import b64decode
from typing import Any

from agentflow.core.state.message_block import DocumentBlock, TextBlock
from agentflow.storage.media.config import DocumentHandling

from .extractor import DocumentExtractor


logger = logging.getLogger("agentflow_cli.media.pipeline")


class DocumentPipeline:
    """Document processing pipeline with extraction config.

    Modes:
        - ``EXTRACT_TEXT``: Extract text via textxtract, return TextBlock.
        - ``PASS_RAW``/``FORWARD_RAW``: Return the original DocumentBlock untouched.
        - ``SKIP``: Drop the document entirely (returns None).
    """

    def __init__(
        self,
        document_extractor: DocumentExtractor | None = None,
        handling: DocumentHandling = DocumentHandling.EXTRACT_TEXT,
    ):
        self.handling = handling
        # Lazy-init extractor only when actually needed (EXTRACT_TEXT mode)
        self._extractor = document_extractor

    @property
    def extractor(self) -> DocumentExtractor:
        if self._extractor is None:
            self._extractor = DocumentExtractor()
        return self._extractor

    async def process_document(self, document_block: Any) -> Any | None:
        """Process a DocumentBlock according to the handling policy.

        Args:
            document_block: A ``DocumentBlock`` instance.

        Returns:
            A ``TextBlock`` (if extracted), the original ``DocumentBlock``
            (if pass-raw or extraction unsupported), or ``None`` (if skip).
        """
        if self.handling == DocumentHandling.SKIP:
            return None

        if self.handling == DocumentHandling.FORWARD_RAW:
            return document_block

        # EXTRACT_TEXT path
        if not isinstance(document_block, DocumentBlock):
            raise ValueError("Expected DocumentBlock in pipeline")

        # If an excerpt already exists, return it as text
        if document_block.excerpt and document_block.excerpt.strip():
            return TextBlock(text=document_block.excerpt)

        media = document_block.media

        if media.kind == "data" and media.data_base64:
            decoded = b64decode(media.data_base64)
            filename = media.filename or "document.pdf"
            extracted = await self.extractor.extract(decoded, filename)
            if extracted:
                return TextBlock(text=extracted)
            # Extraction returned None (unsupported type) — keep raw
            return document_block

        # For external URLs or provider file_id, we cannot extract directly.
        # Keep as-is so API layer may resolve later.
        return document_block
