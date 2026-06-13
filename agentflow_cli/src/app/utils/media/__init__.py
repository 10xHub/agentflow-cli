"""Media processing module for agentflow-api.

Document extraction lives here (not in Agentflow core) because
the core library stays lightweight — SDK users extract text themselves.
The API platform auto-extracts using textxtract.
"""

from .extractor import DocumentExtractor
from .pipeline import DocumentPipeline


__all__ = [
    "DocumentExtractor",
    "DocumentPipeline",
]
