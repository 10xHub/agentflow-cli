# File Upload API Guide

## Quick Start

The graph API now supports file uploads through two new endpoints:
- `/v1/graph/invoke-with-files` - Execute graph with files and get final result
- `/v1/graph/stream-with-files` - Execute graph with files and stream results

## Installation

### Basic Installation (without text extraction)
```bash
pip install 10xscale-agentflow-cli
```

### With Text Extraction Support
```bash
pip install 10xscale-agentflow-cli[textxtract-all]
```

Or for specific formats:
```bash
pip install 10xscale-agentflow-cli[textxtract]  # Basic support
```

## API Usage

### Python Example

```python
import requests
import json

# Prepare your files
files = [
    ('files', ('document.pdf', open('document.pdf', 'rb'), 'application/pdf')),
    ('files', ('image.png', open('image.png', 'rb'), 'image/png')),
]

# Prepare your request data
data = {
    'messages_json': json.dumps([
        {"role": "user", "content": "Please analyze these files"}
    ]),
    'extract_text': 'true',  # Set to 'false' to skip text extraction
    'recursion_limit': 25,
    'response_granularity': 'low',
}

# Make the request
response = requests.post(
    'http://localhost:8000/v1/graph/invoke-with-files',
    files=files,
    data=data,
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

print(response.json())
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/v1/graph/invoke-with-files" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "messages_json=[{\"role\":\"user\",\"content\":\"Analyze this\"}]" \
  -F "extract_text=true" \
  -F "files=@document.pdf" \
  -F "files=@image.png"
```

### Streaming Example

```python
import requests
import json

files = [('files', open('large_file.pdf', 'rb'))]

data = {
    'messages_json': json.dumps([
        {"role": "user", "content": "Process this file"}
    ]),
    'extract_text': 'true',
}

response = requests.post(
    'http://localhost:8000/v1/graph/stream-with-files',
    files=files,
    data=data,
    stream=True,
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `messages_json` | string | Yes | - | JSON string of messages array |
| `files` | file[] | No | [] | Array of files to upload |
| `extract_text` | boolean | No | false | Extract text from documents |
| `initial_state` | string | No | null | JSON string of initial state |
| `config` | string | No | null | JSON string of configuration |
| `recursion_limit` | integer | No | 25 | Maximum recursion depth |
| `response_granularity` | string | No | "low" | Response detail level |

## Supported File Types

### With Text Extraction (requires textxtract[all])
- **Documents**: PDF, DOCX, DOC, RTF, HTML
- **Text**: TXT, MD, CSV, JSON, XML

### Without Text Extraction
- **Images**: PNG, JPG, GIF, BMP, WebP, SVG
- **Audio**: MP3, WAV, OGG
- **Video**: MP4, WebM, AVI
- **Other**: Any file type (stored as base64)

## Response Format

### Successful Response
```json
{
  "success": true,
  "data": {
    "messages": [...],
    "state": {...},
    "context": [...],
    "summary": "...",
    "meta": {...}
  },
  "metadata": {
    "timestamp": "2025-11-07T12:00:00Z",
    "request_id": "..."
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid file format",
    "details": {...}
  }
}
```

## Best Practices

1. **File Size**: Keep files under 10MB for optimal performance
2. **Text Extraction**: Enable only when needed (requires additional dependencies)
3. **Multiple Files**: Upload related files in a single request
4. **Streaming**: Use streaming for large files or long-running operations
5. **Error Handling**: Always check response status and handle errors gracefully

## Examples by Use Case

### Document Analysis
```python
files = [('files', open('contract.pdf', 'rb'))]
data = {
    'messages_json': json.dumps([
        {"role": "user", "content": "Extract key terms from this contract"}
    ]),
    'extract_text': 'true',
}
```

### Image Processing
```python
files = [('files', open('diagram.png', 'rb'))]
data = {
    'messages_json': json.dumps([
        {"role": "user", "content": "Describe this diagram"}
    ]),
    'extract_text': 'false',  # Images don't need text extraction
}
```

### Mixed Content
```python
files = [
    ('files', open('report.pdf', 'rb')),
    ('files', open('chart.png', 'rb')),
]
data = {
    'messages_json': json.dumps([
        {"role": "user", "content": "Summarize the report and analyze the chart"}
    ]),
    'extract_text': 'true',
}
```

## Troubleshooting

### "textxtract not installed" Error
Install text extraction support:
```bash
pip install textxtract[all]
```

### "File too large" Error
- Reduce file size or split into multiple requests
- Use compression for documents
- Consider uploading to cloud storage and passing URL instead

### "Invalid JSON" Error
- Ensure `messages_json` is properly escaped
- Use `json.dumps()` to create the JSON string
- Check for special characters in content

## Performance Tips

1. **Batch Processing**: Upload multiple files in one request when possible
2. **Async Operations**: Use async/await in your client code
3. **Streaming**: Use stream endpoint for large files or real-time feedback
4. **Caching**: Cache extracted text when processing same files multiple times
5. **Format Selection**: Use extract_text only for text-heavy documents

## Security Considerations

1. **Authentication**: Always use authentication tokens
2. **File Validation**: Validate file types before uploading
3. **Size Limits**: Implement client-side size checks
4. **Sensitive Data**: Be cautious with files containing sensitive information
5. **HTTPS**: Always use HTTPS in production

## Migration from Old API

### Before (without files)
```python
response = requests.post(
    'http://localhost:8000/v1/graph/invoke',
    json={
        'messages': [{"role": "user", "content": "Hello"}],
    }
)
```

### After (with files)
```python
files = [('files', open('doc.pdf', 'rb'))]
response = requests.post(
    'http://localhost:8000/v1/graph/invoke-with-files',
    files=files,
    data={
        'messages_json': json.dumps([{"role": "user", "content": "Hello"}]),
        'extract_text': 'true',
    }
)
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/10xHub/agentflow-cli/issues
- Documentation: https://agentflow-cli.readthedocs.io/
- Email: contact@10xscale.ai
