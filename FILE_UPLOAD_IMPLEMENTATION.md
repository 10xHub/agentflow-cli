# File Upload Implementation Summary

## Overview
Implemented file upload support for graph APIs with proper ContentBlock handling using agentflow's built-in types.

## Key Features

### 1. File Processing (`agentflow_cli/src/app/utils/file_processor.py`)
- Processes uploaded files and converts them into appropriate ContentBlock types
- **Supported File Types:**
  - **Images** (PNG, JPG, GIF, BMP, WebP, SVG) → `ImageBlock`
  - **Audio** (MP3, WAV, OGG) → `AudioBlock`
  - **Video** (MP4, WebM, AVI) → `VideoBlock`
  - **Documents** (PDF, DOCX, DOC, TXT, MD, CSV, JSON, XML, HTML, RTF) → `DocumentBlock` or `TextBlock` (if text extraction enabled)
  - **Text files** → `TextBlock` (with optional extraction)

### 2. Text Extraction (`agentflow_cli/src/app/utils/text_extractor.py`)
- Optional text extraction from documents using `textxtract` library
- Gracefully handles absence of textxtract (optional dependency)
- Supports extraction from: PDF, DOCX, DOC, RTF, HTML, CSV, JSON, XML, MD, TXT
- Async implementation for better performance

### 3. API Endpoints (`agentflow_cli/src/app/routers/graph/router.py`)

#### POST `/v1/graph/invoke-with-files`
- Execute graph with file uploads
- Files are processed into ContentBlocks and added to messages
- Supports `extract_text` parameter for document text extraction

#### POST `/v1/graph/stream-with-files`
- Stream graph execution with file uploads
- Same file processing as invoke endpoint
- Real-time streaming output

### 4. ContentBlock Integration
- Uses agentflow's built-in ContentBlock types from `agentflow.state.message_block`
- **MediaRef Structure:**
  ```python
  MediaRef(
      kind="data",                # Literal['url', 'file_id', 'data']
      data_base64="...",          # Base64-encoded file content
      mime_type="image/png",      # MIME type of the file
      size_bytes=1024,            # File size in bytes
      sha256="...",               # SHA-256 hash
      filename="image.png",       # Original filename
  )
  ```

- **Message Integration:**
  - Files are added as ContentBlocks to the last user message's content array
  - If no user message exists, a new message is created with the file ContentBlocks

## Implementation Details

### File Processing Flow
1. **Upload**: Files received as `UploadFile` objects via multipart/form-data
2. **Detection**: MIME type detected based on file extension and content
3. **Hashing**: SHA-256 hash calculated for file integrity
4. **Encoding**: File content base64-encoded for MediaRef
5. **Block Creation**: Appropriate ContentBlock type created based on MIME type
6. **Message Integration**: ContentBlocks appended to message content array

### Example Usage

```python
# Process single file
file_processor = FileProcessor()
content_block = await file_processor.process_upload_file(file, extract_text=False)

# Process multiple files
content_blocks = await file_processor.process_multiple_files(files, extract_text=True)

# Add to message
message = Message(
    role="user",
    content=[
        TextBlock(text="Here are the images:"),
        *content_blocks  # Image blocks, document blocks, etc.
    ]
)
```

## Testing
- **19 unit tests** covering all functionality
- Tests for file processor, text extractor, MediaRef, and ContentBlocks
- All tests passing ✅

## Dependencies
- **Required**: FastAPI, Pydantic, agentflow
- **Optional**: `textxtract[all]` for document text extraction
  - Install with: `pip install textxtract[all]`
  - Gracefully falls back if not available

## File Structure
```
agentflow_cli/src/app/
├── utils/
│   ├── file_processor.py       # Main file processing logic
│   └── text_extractor.py       # Optional text extraction
└── routers/graph/
    ├── router.py                # API endpoints with file upload
    └── schemas/
        └── graph_schemas.py     # Pydantic schemas

tests/unit_tests/
└── test_file_upload.py          # Comprehensive tests
```

## Notes
- Messages parameter remains as JSON string in Form data due to FastAPI/Pydantic limitations with complex nested Union types
- All media types properly handled with appropriate ContentBlock types
- Text extraction is optional and requires textxtract library
- Files are stored as base64 in MediaRef with kind="data"
