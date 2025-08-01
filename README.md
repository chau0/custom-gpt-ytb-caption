# YouTube Caption API

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Azure Functions](https://img.shields.io/badge/Azure%20Functions-v4-blue.svg)](https://azure.microsoft.com/en-us/products/functions/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust Azure Functions-based REST API for extracting YouTube video transcripts/captions with advanced features including pagination, multi-language support, and smart fallback mechanisms.

## Features

- **YouTube URL Support**: Extract video IDs from both `youtube.com` and `youtu.be` URLs
- **Multi-language Support**: Retrieve transcripts in specific languages or use intelligent fallback
- **Translation Support**: Access YouTube's automatic translation features
- **Pagination**: Handle large transcripts with configurable chunking and pagination
- **Smart Language Fallback**: Priority-based transcript selection (manual → auto-generated)
- **Proxy Support**: Built-in support for Webshare proxies to bypass IP restrictions
- **Comprehensive Error Handling**: Detailed error responses for various failure scenarios
- **CORS Enabled**: Cross-origin requests supported out of the box

## Architecture

This project is built as an Azure Functions application using:

- **Runtime**: Azure Functions Python v2
- **Main Endpoint**: `/func_ytb_caption` (HTTP POST)
- **Core Dependencies**: 
  - `azure-functions` - Azure Functions runtime
  - `youtube-transcript-api` - YouTube transcript retrieval

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Azure Functions Core Tools (for local development)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd CustomGPT_ytb_caption
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure local settings** (optional):
   Update `local.settings.json` with your preferred configuration:
   ```json
   {
     "Values": {
       "CHUNK_SIZE": "5000",
       "MAX_CHUNKS": "5",
       "USE_PROXY": "0"
     }
   }
   ```

4. **Run locally**:
   ```bash
   func start
   ```

## API Usage

### Endpoint

**POST** `/func_ytb_caption`

### Request Format

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "chunk_size": 5000,      // optional, default: 5000
  "max_chunks": 5,         // optional, default: 5
  "start_index": 0,        // optional, default: 0 (for pagination)
  "language": "en"         // optional, string or array
}
```

### Response Format

```json
{
  "video_id": "VIDEO_ID",
  "total_characters": 15420,
  "selected_language": "English",
  "selected_language_code": "en",
  "is_generated": false,
  "available_languages": [
    {
      "language": "English",
      "language_code": "en",
      "is_generated": false,
      "is_translatable": true,
      "translation_languages": ["es", "fr", "de", "..."]
    }
  ],
  "chunks": [
    {
      "index": 0,
      "text": "Welcome to this video about..."
    },
    {
      "index": 1,
      "text": "In today's tutorial, we'll cover..."
    }
  ],
  "next_index": 2,
  "total_chunks": 8
}
```

### Usage Examples

**Basic Request**:
```bash
curl -X POST "http://localhost:7071/api/func_ytb_caption" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

**With Language Preference**:
```bash
curl -X POST "http://localhost:7071/api/func_ytb_caption" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "language": "es",
    "chunk_size": 3000,
    "max_chunks": 3
  }'
```

**Pagination Example**:
```bash
curl -X POST "http://localhost:7071/api/func_ytb_caption" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "start_index": 2,
    "max_chunks": 5
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CHUNK_SIZE` | Maximum characters per chunk | 5000 | No |
| `MAX_CHUNKS` | Maximum chunks returned per request | 5 | No |
| `USE_PROXY` | Enable proxy support (0 or 1) | 0 | No |
| `WEBSHARE_PROXY_USERNAME` | Webshare proxy username | - | If using proxy |
| `WEBSHARE_PROXY_PASSWORD` | Webshare proxy password | - | If using proxy |

### Language Support

The API supports intelligent language selection:

1. **Manual transcripts** in English (preferred)
2. **Any manual transcript** available
3. **Auto-generated transcripts** in English
4. **Any auto-generated transcript** available
5. **Translation** if original language can be translated to requested language

## Error Handling

The API provides comprehensive error handling with appropriate HTTP status codes:

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 400 | Bad Request | Invalid JSON, missing URL, or invalid YouTube URL |
| 403 | Forbidden | Transcripts disabled for the video |
| 404 | Not Found | Video unavailable or no transcripts found |
| 500 | Internal Server Error | Unexpected server error |

### Error Response Format

```json
{
  "error": "Detailed error message describing the issue"
}
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest test_function_app.py

# Run specific test class
pytest test_function_app.py::TestExtractVideoId

# Run with coverage
pytest test_function_app.py --cov=function_app

# Run specific test method
pytest test_function_app.py::TestFuncYtbCaption::test_func_ytb_caption_success
```

### Test Coverage

The test suite covers:
- URL parsing and video ID extraction
- Text chunking and pagination logic
- Main function with various scenarios and error cases
- Mock YouTube API responses
- Language fallback mechanisms
- Translation functionality

## Deployment

### Azure Functions Deployment

1. **Create Azure Function App**:
   ```bash
   az functionapp create --resource-group myResourceGroup \
     --consumption-plan-location westeurope \
     --runtime python --runtime-version 3.9 \
     --functions-version 4 \
     --name myYouTubeCaptionApp \
     --storage-account mystorageaccount
   ```

2. **Deploy the function**:
   ```bash
   func azure functionapp publish myYouTubeCaptionApp
   ```

3. **Configure environment variables** in Azure portal or via CLI:
   ```bash
   az functionapp config appsettings set --name myYouTubeCaptionApp \
     --resource-group myResourceGroup \
     --settings CHUNK_SIZE=5000 MAX_CHUNKS=5
   ```

### Authentication

The function uses Azure Functions' built-in key-based authentication. Include the function key in requests:

```bash
curl -X POST "https://myapp.azurewebsites.net/api/func_ytb_caption?code=YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## Proxy Configuration

For production deployments that might face IP restrictions, configure proxy support:

1. **Set environment variables**:
   ```bash
   USE_PROXY=1
   WEBSHARE_PROXY_USERNAME=your_username
   WEBSHARE_PROXY_PASSWORD=your_password
   ```

2. **The API will automatically use rotating residential proxies** through Webshare when enabled.

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes and add tests**
4. **Run the test suite**: `pytest test_function_app.py`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Add tests for new functionality
- Update documentation for API changes
- Ensure all tests pass before submitting PR

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api) - Core transcript extraction functionality
- [Azure Functions](https://azure.microsoft.com/en-us/products/functions/) - Serverless hosting platform

---

**Note**: This API uses YouTube's unofficial transcript API. While efforts are made to maintain compatibility, YouTube may change their internal APIs at any time.