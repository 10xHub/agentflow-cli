"""Unit tests for file upload and processing functionality."""

import base64
import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from agentflow.state.message_block import (
    AudioBlock,
    DocumentBlock,
    ImageBlock,
    MediaRef,
    TextBlock,
    VideoBlock,
)
from agentflow_cli.src.app.utils.file_processor import FileProcessor
from agentflow_cli.src.app.utils.text_extractor import TextExtractor


class TestTextExtractor:
    """Tests for TextExtractor class."""

    def test_extractor_availability(self):
        """Test checking if extractor is available."""
        extractor = TextExtractor()
        # Should return False since textxtract is likely not installed in test environment
        # But the check should not raise an error
        result = extractor.is_available()
        assert isinstance(result, bool)

    def test_supported_extensions(self):
        """Test get supported extensions."""
        extensions = TextExtractor.get_supported_extensions()
        assert isinstance(extensions, dict)
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".txt" in extensions

    def test_is_extractable(self):
        """Test checking if a file is extractable."""
        assert TextExtractor.is_extractable("document.pdf")
        assert TextExtractor.is_extractable("file.docx")
        assert TextExtractor.is_extractable("notes.txt")
        assert not TextExtractor.is_extractable("image.png")
        assert not TextExtractor.is_extractable("unknown.xyz")


class TestFileProcessor:
    """Tests for FileProcessor class."""

    def test_calculate_sha256(self):
        """Test SHA256 calculation."""
        data = b"Hello, World!"
        expected = hashlib.sha256(data).hexdigest()
        result = FileProcessor.calculate_sha256(data)
        assert result == expected

    def test_detect_mime_type_pdf(self):
        """Test MIME type detection for PDF."""
        mime = FileProcessor.detect_mime_type("document.pdf")
        assert mime == "application/pdf"

    def test_detect_mime_type_image(self):
        """Test MIME type detection for images."""
        assert FileProcessor.detect_mime_type("photo.png") == "image/png"
        assert FileProcessor.detect_mime_type("photo.jpg") == "image/jpeg"

    def test_detect_mime_type_text(self):
        """Test MIME type detection for text files."""
        assert FileProcessor.detect_mime_type("file.txt") == "text/plain"
        assert FileProcessor.detect_mime_type("file.md") == "text/markdown"

    def test_is_image(self):
        """Test image type detection."""
        assert FileProcessor.is_image("image/png")
        assert FileProcessor.is_image("image/jpeg")
        assert not FileProcessor.is_image("application/pdf")
        assert not FileProcessor.is_image("text/plain")

    def test_is_document(self):
        """Test document type detection."""
        assert FileProcessor.is_document("application/pdf")
        assert FileProcessor.is_document("application/msword")
        assert FileProcessor.is_document("text/plain")
        assert not FileProcessor.is_document("image/png")
        assert not FileProcessor.is_document("video/mp4")

    @pytest.mark.asyncio
    async def test_process_file_data_image(self):
        """Test processing image file data."""
        processor = FileProcessor()

        # Create a simple image-like file (just bytes for testing)
        file_data = b"fake image data"
        filename = "test_image.png"

        result = await processor.process_file_data(
            file_data=file_data,
            filename=filename,
            extract_text=False,
        )

        # Should return ImageBlock
        assert isinstance(result, ImageBlock)
        assert result.type == "image"
        assert result.media.mime_type == "image/png"
        assert result.media.size_bytes == len(file_data)
        assert result.media.sha256 is not None

    @pytest.mark.asyncio
    async def test_process_file_data_document(self):
        """Test processing document file data."""
        processor = FileProcessor()

        # Create a simple document-like file
        file_data = b"This is a PDF document"
        filename = "test_document.pdf"

        result = await processor.process_file_data(
            file_data=file_data,
            filename=filename,
            extract_text=False,
        )

        # Should return DocumentBlock
        assert isinstance(result, DocumentBlock)
        assert result.type == "document"
        assert result.media.mime_type == "application/pdf"
        assert result.media.size_bytes == len(file_data)
        assert result.media.sha256 is not None

    @pytest.mark.asyncio
    async def test_process_file_data_with_base64(self):
        """Test that file data is properly encoded as base64."""
        processor = FileProcessor()

        file_data = b"test content"
        filename = "test.txt"

        result = await processor.process_file_data(
            file_data=file_data,
            filename=filename,
            extract_text=False,
        )

        # Verify base64 encoding
        assert result.media.data_base64 is not None
        decoded = base64.b64decode(result.media.data_base64)
        assert decoded == file_data

    @pytest.mark.asyncio
    async def test_process_upload_file(self):
        """Test processing FastAPI UploadFile."""
        processor = FileProcessor()

        # Create a mock UploadFile
        file_content = b"test file content"
        file = UploadFile(
            file=BytesIO(file_content),
            filename="test.txt",
        )

        result = await processor.process_upload_file(file, extract_text=False)

        # Should return a DocumentBlock (text files are documents)
        assert isinstance(result, DocumentBlock)
        assert result.media.filename == "test.txt"
        assert result.media.mime_type == "text/plain"

    @pytest.mark.asyncio
    async def test_process_multiple_files(self):
        """Test processing multiple files."""
        processor = FileProcessor()

        # Create multiple mock files
        files = [
            UploadFile(file=BytesIO(b"file 1"), filename="file1.txt"),
            UploadFile(file=BytesIO(b"file 2"), filename="file2.png"),
        ]

        results = await processor.process_multiple_files(files, extract_text=False)

        assert len(results) == 2
        assert isinstance(results[0], DocumentBlock)
        assert isinstance(results[1], ImageBlock)


class TestMediaRef:
    """Tests for MediaRef model."""

    def test_media_ref_creation(self):
        """Test creating MediaRef."""
        media = MediaRef(
            kind="data",
            data_base64="dGVzdCBkYXRh",
            mime_type="text/plain",
            size_bytes=100,
            sha256="abc123",
            filename="test.txt",
        )

        assert media.kind == "data"
        assert media.data_base64 == "dGVzdCBkYXRh"
        assert media.mime_type == "text/plain"
        assert media.size_bytes == 100
        assert media.sha256 == "abc123"
        assert media.filename == "test.txt"

    def test_media_ref_defaults(self):
        """Test MediaRef default values."""
        media = MediaRef()

        assert media.kind == "url"
        assert media.url is None
        assert media.file_id is None
        assert media.data_base64 is None


class TestContentBlocks:
    """Tests for ContentBlock models."""

    def test_text_block(self):
        """Test TextBlock creation."""
        block = TextBlock(text="Hello, World!")

        assert block.type == "text"
        assert block.text == "Hello, World!"
        assert block.annotations == []

    def test_image_block(self):
        """Test ImageBlock creation."""
        media = MediaRef(kind="url", url="https://example.com/image.png")
        block = ImageBlock(media=media, alt_text="Test image")

        assert block.type == "image"
        assert block.media == media
        assert block.alt_text == "Test image"

    def test_document_block(self):
        """Test DocumentBlock creation."""
        media = MediaRef(kind="data", data_base64="...")
        block = DocumentBlock(media=media, pages=[1, 2, 3])

        assert block.type == "document"
        assert block.media == media
        assert block.pages == [1, 2, 3]
