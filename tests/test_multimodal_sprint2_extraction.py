"""Tests for Sprint 2 – DocumentExtractor & DocumentPipeline.

These tests live in pyagenity-api because document extraction is an API concern
(not a core library concern).
"""

import pytest
from agentflow.core.state.message_block import DocumentBlock, MediaRef, TextBlock
from agentflow.storage.media.config import DocumentHandling

from agentflow_cli.src.app.utils.media.extractor import (
    DocumentExtractor,
    ExtractionError,
    FileTypeNotSupportedError,
)
from agentflow_cli.src.app.utils.media.pipeline import DocumentPipeline


# ---------------------------------------------------------------------------
# Fake textxtract extractor for testing
# ---------------------------------------------------------------------------


class FakeExtractor:
    """Simulates textxtract.AsyncTextExtractor behavior."""

    async def extract(self, data, filename=None):
        if filename == "unsupported.xyz":
            raise FileTypeNotSupportedError("unsupported file type")
        if data == b"corrupt":
            raise ExtractionError("extraction failed")
        if isinstance(data, bytes):
            return f"extracted:{len(data)}bytes"
        return f"extracted:path={data}"


# ---------------------------------------------------------------------------
# DocumentExtractor tests
# ---------------------------------------------------------------------------


class TestDocumentExtractor:
    @pytest.mark.asyncio
    async def test_extract_bytes_success(self):
        ext = DocumentExtractor(extractor=FakeExtractor())
        result = await ext.extract(b"hello", "doc.pdf")
        assert result == "extracted:5bytes"

    @pytest.mark.asyncio
    async def test_extract_path_success(self):
        ext = DocumentExtractor(extractor=FakeExtractor())
        result = await ext.extract("/tmp/report.pdf")
        assert result == "extracted:path=/tmp/report.pdf"

    @pytest.mark.asyncio
    async def test_extract_bytes_no_filename_raises(self):
        ext = DocumentExtractor(extractor=FakeExtractor())
        with pytest.raises(ValueError, match="filename must be provided"):
            await ext.extract(b"hello")

    @pytest.mark.asyncio
    async def test_unsupported_type_returns_none(self):
        ext = DocumentExtractor(extractor=FakeExtractor())
        result = await ext.extract(b"abc", "unsupported.xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_extraction_error_raises_value_error(self):
        ext = DocumentExtractor(extractor=FakeExtractor())
        with pytest.raises(ValueError, match="Failed to extract"):
            await ext.extract(b"corrupt", "doc.pdf")

    def test_no_textxtract_raises_import_error(self, monkeypatch):
        """If textxtract is not installed, instantiation raises ImportError."""
        import agentflow_cli.src.app.utils.media.extractor as mod

        monkeypatch.setattr(mod, "AsyncTextExtractor", None)
        with pytest.raises(ImportError, match="textxtract is required"):
            DocumentExtractor()

    def test_custom_extractor_injection(self):
        """Custom extractor can be injected for testing."""
        ext = DocumentExtractor(extractor=FakeExtractor())
        assert ext.extractor is not None


# ---------------------------------------------------------------------------
# DocumentPipeline tests
# ---------------------------------------------------------------------------


class TestDocumentPipeline:
    @pytest.mark.asyncio
    async def test_skip_returns_none(self):
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.SKIP,
        )
        block = DocumentBlock(media=MediaRef(kind="url", url="https://example.com/doc.pdf"))
        result = await pipeline.process_document(block)
        assert result is None

    @pytest.mark.asyncio
    async def test_pass_raw_returns_original(self):
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.FORWARD_RAW,
        )
        block = DocumentBlock(media=MediaRef(kind="url", url="https://example.com/doc.pdf"))
        result = await pipeline.process_document(block)
        assert result is block

    @pytest.mark.asyncio
    async def test_extract_text_from_base64(self):
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.EXTRACT_TEXT,
        )
        block = DocumentBlock(
            media=MediaRef(
                kind="data",
                data_base64="YWJj",  # base64 of b"abc"
                mime_type="application/pdf",
                filename="report.pdf",
            )
        )
        result = await pipeline.process_document(block)
        assert isinstance(result, TextBlock)
        assert "extracted:" in result.text

    @pytest.mark.asyncio
    async def test_extract_text_uses_excerpt_if_present(self):
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.EXTRACT_TEXT,
        )
        block = DocumentBlock(
            media=MediaRef(kind="url", url="https://example.com/doc.pdf"),
            excerpt="Already extracted text",
        )
        result = await pipeline.process_document(block)
        assert isinstance(result, TextBlock)
        assert result.text == "Already extracted text"

    @pytest.mark.asyncio
    async def test_extract_text_url_ref_pass_through(self):
        """URL-referenced docs can't be extracted locally; return as-is."""
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.EXTRACT_TEXT,
        )
        block = DocumentBlock(media=MediaRef(kind="url", url="https://example.com/doc.pdf"))
        result = await pipeline.process_document(block)
        assert result is block  # Can't extract from URL => pass through

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_falls_back(self):
        """When extraction returns None (unsupported), keep raw block."""

        class UnsupportedExtractor:
            async def extract(self, data, filename=None):
                raise FileTypeNotSupportedError("nope")

        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=UnsupportedExtractor()),
            handling=DocumentHandling.EXTRACT_TEXT,
        )
        block = DocumentBlock(
            media=MediaRef(
                kind="data",
                data_base64="YWJj",
                mime_type="application/octet-stream",
                filename="weird.dat",
            )
        )
        result = await pipeline.process_document(block)
        # Extractor returns None for unsupported => DocumentExtractor returns None => pipeline returns raw block
        assert result is block

    @pytest.mark.asyncio
    async def test_extract_rejects_non_document_block(self):
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.EXTRACT_TEXT,
        )
        with pytest.raises(ValueError, match="Expected DocumentBlock"):
            await pipeline.process_document("not a block")

    @pytest.mark.asyncio
    async def test_extract_uses_default_filename(self):
        """When filename is missing, defaults to 'document.pdf'."""
        pipeline = DocumentPipeline(
            document_extractor=DocumentExtractor(extractor=FakeExtractor()),
            handling=DocumentHandling.EXTRACT_TEXT,
        )
        block = DocumentBlock(
            media=MediaRef(kind="data", data_base64="YWJj", mime_type="application/pdf")
        )
        result = await pipeline.process_document(block)
        assert isinstance(result, TextBlock)

    @pytest.mark.asyncio
    async def test_lazy_extractor_init(self):
        """Extractor is lazily initialized when not provided."""
        # This would raise ImportError if textxtract isn't installed,
        # but we test the lazy property pattern
        pipeline = DocumentPipeline(handling=DocumentHandling.SKIP)
        assert pipeline._extractor is None
        # Skip mode doesn't need extractor
        result = await pipeline.process_document(
            DocumentBlock(media=MediaRef(kind="url", url="https://x.com/a.pdf"))
        )
        assert result is None
