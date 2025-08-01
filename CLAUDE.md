# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Azure Functions app that provides a REST API for retrieving YouTube video transcripts/captions. The main function extracts video IDs from YouTube URLs, fetches transcripts using the YouTube Transcript API, and returns paginated chunks of transcript text.

## Architecture

- **Function App**: Built using Azure Functions Python runtime v2
- **Main Endpoint**: `/func_ytb_caption` - HTTP trigger function that accepts POST requests
- **Core Dependencies**: 
  - `azure-functions` - Azure Functions runtime
  - `youtube-transcript-api` - YouTube transcript retrieval

## Key Components

### Main Function (`function_app.py`)
- `func_ytb_caption()` - Main HTTP endpoint handler
- `extract_video_id()` - Extracts video ID from YouTube URLs (supports both youtube.com and youtu.be formats)
- `chunk_text()` - Splits transcript text into configurable chunks
- `paginate_chunks()` - Handles pagination of chunked transcript data

### Configuration
- Environment variables: `CHUNK_SIZE` (default: 5000), `MAX_CHUNKS` (default: 5)
- Supports both manual and auto-generated transcripts
- Smart language fallback: manual English → any manual → auto English → any auto → any available
- Translation support for unsupported languages

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_function_app.py

# Run specific test
pytest test_function_app.py::TestExtractVideoId::test_extract_video_id_youtube_com
```

### Local Development
The function can be run locally using Azure Functions Core Tools. Configuration is in `local.settings.json` and `host.json`.

## API Usage

**Endpoint**: POST `/func_ytb_caption`

**Request Body**:
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "chunk_size": 5000,  // optional
  "max_chunks": 5,     // optional
  "start_index": 0,    // optional, for pagination
  "language": "en"     // optional, string or array
}
```

**Response**:
- Returns paginated transcript chunks with metadata
- Includes available languages, transcript type (manual/generated)
- CORS headers enabled for cross-origin requests

## Error Handling

The function handles various YouTube API exceptions:
- `NoTranscriptFound` → 404
- `VideoUnavailable` → 404  
- `TranscriptsDisabled` → 403
- Invalid JSON → 400
- Invalid YouTube URL → 400

## Testing

Comprehensive test suite in `test_function_app.py` covering:
- URL parsing and video ID extraction
- Text chunking and pagination logic
- Main function with various scenarios and error cases
- Mocked YouTube API responses