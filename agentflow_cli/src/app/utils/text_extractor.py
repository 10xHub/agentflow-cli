"""
Text extraction utility for various file formats.

This module provides utilities for extracting text from various file formats
using the textxtract library. It handles both file paths and file bytes.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from pydantic import BaseModel

if TYPE_CHECKING:
    from textxtract import AsyncTextExtractor

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    """
    Result of text extraction from a file.

    Attributes:
        text (str): Extracted text content.
        success (bool): Whether extraction was successful.
        error (str | None): Error message if extraction failed.
        file_type (str | None): Detected file type/extension.
    """

    text: str = ""
    success: bool = True
    error: str | None = None
    file_type: str | None = None


class TextExtractor:
    """
    Async text extractor for various file formats.

    This class provides a wrapper around the textxtract library with
    proper error handling and fallback mechanisms.
    """

    def __init__(self):
        """Initialize the text extractor."""
        self._extractor = None
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """
        Check if textxtract library is available.

        Returns:
            bool: True if textxtract is available, False otherwise.
        """
        try:
            from textxtract import AsyncTextExtractor  # noqa: F401

            return True
        except ImportError:
            logger.warning(
                "textxtract library not available. "
                "Install with: pip install textxtract[all] for full support"
            )
            return False

    async def extract_from_path(self, file_path: str | Path) -> ExtractionResult:
        """
        Extract text from a file path.

        Args:
            file_path (str | Path): Path to the file.

        Returns:
            ExtractionResult: Result of the extraction.
        """
        if not self._available:
            return ExtractionResult(
                success=False,
                error="textxtract library not installed",
            )

        try:
            from textxtract import AsyncTextExtractor

            if self._extractor is None:
                self._extractor = AsyncTextExtractor()

            file_path = Path(file_path)
            text = await self._extractor.extract(str(file_path))

            return ExtractionResult(
                text=text,
                success=True,
                file_type=file_path.suffix.lower(),
            )
        except Exception as e:
            logger.exception(f"Error extracting text from {file_path}: {e}")
            return ExtractionResult(
                success=False,
                error=str(e),
                file_type=Path(file_path).suffix.lower() if file_path else None,
            )

    async def extract_from_bytes(
        self, file_bytes: bytes, filename: str
    ) -> ExtractionResult:
        """
        Extract text from file bytes.

        Args:
            file_bytes (bytes): File content as bytes.
            filename (str): Filename (required for type detection).

        Returns:
            ExtractionResult: Result of the extraction.
        """
        if not self._available:
            return ExtractionResult(
                success=False,
                error="textxtract library not installed",
            )

        try:
            from textxtract import AsyncTextExtractor

            if self._extractor is None:
                self._extractor = AsyncTextExtractor()

            text = await self._extractor.extract(file_bytes, filename)

            file_ext = Path(filename).suffix.lower()
            return ExtractionResult(
                text=text,
                success=True,
                file_type=file_ext,
            )
        except Exception as e:
            logger.exception(f"Error extracting text from {filename}: {e}")
            return ExtractionResult(
                success=False,
                error=str(e),
                file_type=Path(filename).suffix.lower() if filename else None,
            )

    async def extract_from_upload(
        self, file: BinaryIO, filename: str
    ) -> ExtractionResult:
        """
        Extract text from an uploaded file.

        Args:
            file (BinaryIO): File-like object from upload.
            filename (str): Filename of the uploaded file.

        Returns:
            ExtractionResult: Result of the extraction.
        """
        try:
            file_bytes = file.read()
            return await self.extract_from_bytes(file_bytes, filename)
        except Exception as e:
            logger.exception(f"Error reading uploaded file {filename}: {e}")
            return ExtractionResult(
                success=False,
                error=f"Error reading file: {e}",
                file_type=Path(filename).suffix.lower() if filename else None,
            )

    def is_available(self) -> bool:
        """
        Check if text extraction is available.

        Returns:
            bool: True if textxtract is available.
        """
        return self._available

    @staticmethod
    def get_supported_extensions() -> dict[str, str]:
        """
        Get supported file extensions and their descriptions.

        Returns:
            dict[str, str]: Mapping of extensions to format names.
        """
        return {
            ".txt": "Text",
            ".text": "Text",
            ".md": "Markdown",
            ".pdf": "PDF",
            ".docx": "Word Document",
            ".doc": "Word Legacy Document",
            ".rtf": "Rich Text Format",
            ".html": "HTML",
            ".htm": "HTML",
            ".csv": "CSV",
            ".json": "JSON",
            ".xml": "XML",
        }

    @staticmethod
    def is_extractable(filename: str) -> bool:
        """
        Check if a file type is extractable.

        Args:
            filename (str): Name of the file.

        Returns:
            bool: True if the file type is supported.
        """
        ext = Path(filename).suffix.lower()
        return ext in TextExtractor.get_supported_extensions()
