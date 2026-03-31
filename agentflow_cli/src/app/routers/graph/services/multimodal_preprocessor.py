"""Pre-processing utilities for multimodal messages at the API boundary."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agentflow.state import Message
from agentflow.state.message_block import DocumentBlock, ImageBlock, TextBlock

if TYPE_CHECKING:
    from agentflow_cli.src.app.routers.media import MediaService

logger = logging.getLogger("agentflow-cli.media")


async def preprocess_multimodal_messages(
    messages: list[Message],
    media_service: "MediaService | None",
) -> list[Message]:
    """Resolve file_id references in messages before graph execution.

    For each ``DocumentBlock`` with a ``file_id``:
      - If cached extracted text exists, replace with a ``TextBlock``.
      - Otherwise pass through unchanged (the agent converter will handle it).

    For each ``ImageBlock``/``AudioBlock`` with a ``file_id``:
      - Convert to a ``agentflow://media/{file_id}`` URL-based reference so
        the MediaRefResolver can pick it up at LLM-call time.

    This is a no-op when ``media_service`` is None.
    """
    if media_service is None:
        return messages

    processed: list[Message] = []
    for msg in messages:
        new_content = []
        changed = False

        for block in msg.content:
            if isinstance(block, DocumentBlock) and block.media.kind == "file_id" and block.media.file_id:
                cached = media_service.get_cached_extraction(block.media.file_id)
                if cached:
                    new_content.append(TextBlock(text=cached))
                    changed = True
                    continue

            if hasattr(block, "media") and block.media.kind == "file_id" and block.media.file_id:
                fid = block.media.file_id
                # Convert file_id → agentflow://media/ URL reference
                if not (block.media.url and block.media.url.startswith("agentflow://media/")):
                    block.media.kind = "url"
                    block.media.url = f"agentflow://media/{fid}"
                    changed = True

            new_content.append(block)

        if changed:
            new_msg = msg.model_copy(update={"content": new_content})
            processed.append(new_msg)
        else:
            processed.append(msg)

    return processed
