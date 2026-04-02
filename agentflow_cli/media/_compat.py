"""Compatibility helpers for upstream AgentFlow media enums."""

from __future__ import annotations

from agentflow.media.config import DocumentHandling


def ensure_document_handling_aliases() -> None:
    """Expose stable aliases across AgentFlow enum renames."""
    try:
        _ = DocumentHandling.PASS_RAW
    except AttributeError:
        DocumentHandling.PASS_RAW = DocumentHandling.FORWARD_RAW

    try:
        _ = DocumentHandling.FORWARD_RAW
    except AttributeError:
        DocumentHandling.FORWARD_RAW = DocumentHandling.PASS_RAW


ensure_document_handling_aliases()

DOCUMENT_PASS_RAW = DocumentHandling.PASS_RAW
