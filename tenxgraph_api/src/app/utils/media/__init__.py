"""Media processing module for 10xgraph-api.

Document extraction lives here (not in 10xGraph core) because
the core library stays lightweight — SDK users extract text themselves.
The API platform auto-extracts using textxtract.
"""

from .extractor import DocumentExtractor
from .pipeline import DocumentPipeline


__all__ = [
    "DocumentExtractor",
    "DocumentPipeline",
]
