#!/usr/bin/env python3
"""
Simple script to demonstrate file upload processing with ContentBlocks.

This script shows how files are converted into agentflow ContentBlocks.
"""

import asyncio
import base64
from pathlib import Path

from agentflow.state import Message
from agentflow.state.message_block import ImageBlock, TextBlock

from agentflow_cli.src.app.utils.file_processor import FileProcessor


async def demo_file_processing():
    """Demonstrate file processing with ContentBlocks."""
    print("="  * 80)
    print("File Upload Processing Demo")
    print("=" * 80)
    print()

    processor = FileProcessor()

    # Demo 1: Process an image
    print("1. Processing image file...")
    image_data = b"Fake PNG image data\x89PNG\r\n\x1a\n"
    filename = "demo_image.png"

    image_block = await processor.process_file_data(
        file_data=image_data,
        filename=filename,
        extract_text=False,
    )

    print(f"   Type: {image_block.type}")
    print(f"   MIME: {image_block.media.mime_type}")
    print(f"   Size: {image_block.media.size_bytes} bytes")
    print(f"   SHA256: {image_block.media.sha256[:16]}...")
    print(f"   Filename: {image_block.media.filename}")
    print()

    # Demo 2: Process a text document
    print("2. Processing text document...")
    text_data = b"This is a sample text document with some content."
    filename = "demo_document.txt"

    doc_block = await processor.process_file_data(
        file_data=text_data,
        filename=filename,
        extract_text=True,  # Extract text from document
    )

    print(f"   Type: {doc_block.type}")
    if doc_block.type == "text":
        print(f"   Extracted text: {doc_block.text[:50]}...")
    else:
        print(f"   MIME: {doc_block.media.mime_type}")
    print()

    # Demo 3: Create a Message with ContentBlocks
    print("3. Creating message with file content blocks...")
    message = Message(
        role="user",
        content=[
            TextBlock(text="Here are the uploaded files:"),
            image_block,
            doc_block,
        ],
    )

    print(f"   Message role: {message.role}")
    print(f"   Content blocks: {len(message.content)}")
    print(f"   Block types: {[block.type for block in message.content]}")
    print()

    # Demo 4: Show MediaRef structure
    print("4. MediaRef structure:")
    print(f"   kind: {image_block.media.kind}")
    print(f"   data_base64: {image_block.media.data_base64[:30]}... (truncated)")
    print(f"   mime_type: {image_block.media.mime_type}")
    print(f"   size_bytes: {image_block.media.size_bytes}")
    print(f"   sha256: {image_block.media.sha256}")
    print(f"   filename: {image_block.media.filename}")
    print()

    # Demo 5: Show that data can be decoded
    print("5. Verify data integrity (decode base64):")
    decoded_data = base64.b64decode(image_block.media.data_base64)
    print(f"   Original size: {len(image_data)} bytes")
    print(f"   Decoded size: {len(decoded_data)} bytes")
    print(f"   Data matches: {decoded_data == image_data}")
    print()

    print("="  * 80)
    print("Demo complete! File upload processing works correctly.")
    print("="  * 80)


if __name__ == "__main__":
    asyncio.run(demo_file_processing())
