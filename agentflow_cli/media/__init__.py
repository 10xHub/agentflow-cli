"""Media processing module for pyagenity-api.

Document extraction lives here (not in PyAgenity core) because
the core library stays lightweight — SDK users extract text themselves.
The API platform auto-extracts using textxtract.
"""

from ._compat import ensure_document_handling_aliases
from .extractor import DocumentExtractor
from .pipeline import DocumentPipeline


ensure_document_handling_aliases()


__all__ = [
    "DocumentExtractor",
    "DocumentPipeline",
]
