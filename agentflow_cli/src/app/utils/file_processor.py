"""
File upload handler for processing uploaded files and creating content blocks.

This module handles file uploads, extraction, hash calculation, and creation
of appropriate ContentBlock objects from agentflow.
"""

import base64
import hashlib
import logging
import mimetypes
from pathlib import Path

from agentflow.state.message_block import (
    AudioBlock,
    ContentBlock,
    DocumentBlock,
    ImageBlock,
    MediaRef,
    TextBlock,
    VideoBlock,
)
from fastapi import UploadFile

from agentflow_cli.src.app.utils.text_extractor import TextExtractor


logger = logging.getLogger(__name__)


class FileProcessor:
    """
    Process uploaded files and create appropriate content blocks.

    This class handles file processing, text extraction, and content block creation.
    """

    def __init__(self):
        """Initialize the file processor."""
        self.text_extractor = TextExtractor()

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """
        Calculate SHA256 hash of file data.

        Args:
            data (bytes): File data.

        Returns:
            str: SHA256 hash as hex string.
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def detect_mime_type(filename: str, data: bytes | None = None) -> str:
        """
        Detect MIME type of a file.

        Args:
            filename (str): Name of the file.
            data (bytes | None): File data (optional).

        Returns:
            str: MIME type.
        """
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type

        # Fallback to generic types based on extension
        ext = Path(filename).suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".json": "application/json",
            ".xml": "application/xml",
            ".html": "text/html",
            ".htm": "text/html",
            ".rtf": "application/rtf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".avi": "video/x-msvideo",
        }
        return mime_map.get(ext, "application/octet-stream")

    @staticmethod
    def is_image(mime_type: str) -> bool:
        """
        Check if MIME type is an image.

        Args:
            mime_type (str): MIME type.

        Returns:
            bool: True if image type.
        """
        return mime_type.startswith("image/")

    @staticmethod
    def is_audio(mime_type: str) -> bool:
        """
        Check if MIME type is audio.

        Args:
            mime_type (str): MIME type.

        Returns:
            bool: True if audio type.
        """
        return mime_type.startswith("audio/")

    @staticmethod
    def is_video(mime_type: str) -> bool:
        """
        Check if MIME type is video.

        Args:
            mime_type (str): MIME type.

        Returns:
            bool: True if video type.
        """
        return mime_type.startswith("video/")

    @staticmethod
    def is_document(mime_type: str) -> bool:
        """
        Check if MIME type is a document.

        Args:
            mime_type (str): MIME type.

        Returns:
            bool: True if document type.
        """
        document_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/rtf",
            "text/plain",
            "text/markdown",
            "text/csv",
            "text/html",
        ]
        return mime_type in document_types or mime_type.startswith("text/")

    async def process_upload_file(
        self,
        file: UploadFile,
        extract_text: bool = False,
    ) -> ContentBlock:
        """
        Process an uploaded file and create appropriate content block.

        Args:
            file (UploadFile): Uploaded file from FastAPI.
            extract_text (bool): Whether to extract text from documents.

        Returns:
            ContentBlock: Appropriate content block (TextBlock, ImageBlock, DocumentBlock).
        """
        try:
            # Read file data
            file_data = await file.read()
            filename = file.filename or "unknown"

            return await self.process_file_data(
                file_data=file_data,
                filename=filename,
                extract_text=extract_text,
            )
        except Exception as e:
            logger.exception(f"Error processing upload file {file.filename}: {e}")
            raise
        finally:
            # Reset file position for potential reuse
            await file.seek(0)

    async def process_file_data(
        self,
        file_data: bytes,
        filename: str,
        extract_text: bool = False,
    ) -> ContentBlock:
        """
        Process file data and create appropriate content block.

        Args:
            file_data (bytes): File content as bytes.
            filename (str): Name of the file.
            extract_text (bool): Whether to extract text from documents.

        Returns:
            ContentBlock: Appropriate content block.
        """
        # Calculate metadata
        sha256_hash = self.calculate_sha256(file_data)
        mime_type = self.detect_mime_type(filename, file_data)
        size_bytes = len(file_data)

        logger.info(
            f"Processing file: {filename} (type: {mime_type}, size: {size_bytes} bytes)"
        )

        # Check if we should extract text
        if (
            extract_text
            and self.is_document(mime_type)
            and self.text_extractor.is_available()
            and self.text_extractor.is_extractable(filename)
        ):
            logger.info(f"Extracting text from {filename}")
            extraction_result = await self.text_extractor.extract_from_bytes(
                file_data, filename
            )

            if extraction_result.success and extraction_result.text:
                # Return as TextBlock if extraction successful
                return TextBlock(
                    text=extraction_result.text,
                )

            logger.warning(
                f"Text extraction failed for {filename}: {extraction_result.error}"
            )

        # Create base64 encoded data for MediaRef
        data_base64 = base64.b64encode(file_data).decode("utf-8")

        # Create MediaRef
        media_ref = MediaRef(
            kind="data",
            data_base64=data_base64,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            filename=filename,
        )

        # Return appropriate content block based on file type
        if self.is_image(mime_type):
            return ImageBlock(
                media=media_ref,
                alt_text=f"Image: {filename}",
            )

        if self.is_audio(mime_type):
            return AudioBlock(
                media=media_ref,
            )

        if self.is_video(mime_type):
            return VideoBlock(
                media=media_ref,
            )

        if self.is_document(mime_type):
            return DocumentBlock(
                media=media_ref,
            )

        # For other types, return as document block
        return DocumentBlock(
            media=media_ref,
        )

    async def process_multiple_files(
        self,
        files: list[UploadFile],
        extract_text: bool = False,
    ) -> list[ContentBlock]:
        """
        Process multiple uploaded files.

        Args:
            files (list[UploadFile]): List of uploaded files.
            extract_text (bool): Whether to extract text from documents.

        Returns:
            list[ContentBlock]: List of content blocks.
        """
        content_blocks = []
        for file in files:
            try:
                block = await self.process_upload_file(file, extract_text)
                content_blocks.append(block)
            except Exception as e:
                logger.error(f"Failed to process file {file.filename}: {e}")
                # Continue processing other files

        return content_blocks
