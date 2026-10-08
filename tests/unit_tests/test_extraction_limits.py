"""Document extraction must not be steerable into archives or run without limits (H5).

textxtract picks its handler from the file name. A client could upload a ``text/plain`` file
named ``a.zip`` and have it unzipped, with nested archives and no overall size budget.
"""

# ruff: noqa: S101, PLR2004

import asyncio
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from tenxgraph.core.state.message_block import DocumentBlock, MediaRef
from tenxgraph.storage.media.config import DocumentHandling

from tenxgraph_api.src.app.utils.media import extractor as extractor_module
from tenxgraph_api.src.app.utils.media.extractor import DocumentExtractor
from tenxgraph_api.src.app.utils.media.pipeline import DocumentPipeline


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class RecordingExtractor:
    """Fake textxtract: records the file name it was given (which picks the handler)."""

    def __init__(self, result="text"):
        self.result = result
        self.filenames: list[str] = []

    async def extract(self, data, filename=None):
        self.filenames.append(filename)
        return self.result


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_handler_comes_from_the_declared_type_not_the_filename():
    fake = RecordingExtractor()
    await DocumentExtractor(extractor=fake).extract(b"hello", "a.zip", mime_type="text/plain")
    assert fake.filenames == ["upload.txt"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "mime_type"),
    [("a.zip", None), ("b.tar.gz", None), ("c.bin", "application/zip"), ("d", None)],
)
async def test_archives_and_unknown_types_are_never_extracted(filename, mime_type):
    fake = RecordingExtractor()
    result = await DocumentExtractor(extractor=fake).extract(b"PK..", filename, mime_type)
    assert result is None
    assert fake.filenames == []


@pytest.mark.asyncio
async def test_known_extension_still_works_without_a_mime_type():
    fake = RecordingExtractor()
    await DocumentExtractor(extractor=fake).extract(b"%PDF", "report.PDF")
    assert fake.filenames == ["upload.pdf"]


@pytest.mark.asyncio
async def test_highly_compressed_docx_is_rejected():
    bomb = _zip({"word/document.xml": b"\0" * 5_000_000})  # ratio in the thousands
    fake = RecordingExtractor()
    with pytest.raises(ValueError, match="compression"):
        await DocumentExtractor(extractor=fake).extract(bomb, "cv.docx", DOCX)
    assert fake.filenames == []


@pytest.mark.asyncio
async def test_oversized_docx_is_rejected(monkeypatch):
    monkeypatch.setattr(extractor_module, "MAX_ARCHIVE_UNCOMPRESSED_BYTES", 1_000)
    import os

    payload = _zip({"word/document.xml": os.urandom(5_000)})  # incompressible
    with pytest.raises(ValueError, match="too large"):
        await DocumentExtractor(extractor=RecordingExtractor()).extract(payload, "cv.docx", DOCX)


@pytest.mark.asyncio
async def test_ordinary_docx_is_extracted():
    payload = _zip({"word/document.xml": b"<w:t>Hello CV</w:t>" * 50})
    fake = RecordingExtractor()
    await DocumentExtractor(extractor=fake).extract(payload, "cv.docx", DOCX)
    assert fake.filenames == ["upload.docx"]


@pytest.mark.asyncio
async def test_extraction_times_out(monkeypatch):
    monkeypatch.setattr(extractor_module, "EXTRACTION_TIMEOUT_SECONDS", 0.05)

    class Slow:
        async def extract(self, data, filename=None):
            await asyncio.sleep(1)

    with pytest.raises(ValueError, match="timed out"):
        await DocumentExtractor(extractor=Slow()).extract(b"x", "a.txt", "text/plain")


@pytest.mark.asyncio
async def test_extracted_text_is_capped(monkeypatch):
    monkeypatch.setattr(extractor_module, "MAX_EXTRACTED_CHARS", 100)
    fake = RecordingExtractor(result="x" * 1_000)
    text = await DocumentExtractor(extractor=fake).extract(b"x", "a.txt", "text/plain")
    assert len(text) == 100


@pytest.mark.asyncio
async def test_list_results_become_text():
    fake = RecordingExtractor(result=["one", "two"])
    text = await DocumentExtractor(extractor=fake).extract(b"x", "a.txt", "text/plain")
    assert text == "one\n\ntwo"


# ---------------------------------------------------------------------------
# callers pass the declared type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inline_document_uses_its_declared_type():
    fake = RecordingExtractor()
    pipeline = DocumentPipeline(
        document_extractor=DocumentExtractor(extractor=fake),
        handling=DocumentHandling.EXTRACT_TEXT,
    )
    block = DocumentBlock(
        media=MediaRef(
            kind="data", data_base64="aGVsbG8=", filename="a.zip", mime_type="text/plain"
        )
    )
    await pipeline.process_document(block)
    assert fake.filenames == ["upload.txt"]


@pytest.mark.asyncio
async def test_upload_uses_its_declared_type():
    from tenxgraph_api.src.app.routers.media import MediaService

    fake = RecordingExtractor()
    service = MediaService.__new__(MediaService)
    service._settings = MagicMock(MEDIA_MAX_SIZE_MB=1)
    service._store = MagicMock(store=AsyncMock(return_value="k1"))
    service._pipeline = MagicMock(
        handling=DocumentHandling.EXTRACT_TEXT, extractor=DocumentExtractor(extractor=fake)
    )
    service._cache_extraction = AsyncMock()
    service.get_direct_url_info = AsyncMock(return_value=None)

    await service.upload_file(b"hello", "a.zip", "text/plain", user_id="u1")
    assert fake.filenames == ["upload.txt"]
