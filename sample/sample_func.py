# Azure Function: YouTube Caption Retriever for ChatGPT Tool Integration

This Azure Function exposes a single POST endpoint that ChatGPT (or any HTTP client) can call with a JSON payload to retrieve and chunk YouTube captions, with built‑in pagination to support very large transcripts.

---

## function.json
```json
{
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["post"],
      "route": "get-captions"
    },
    {
      "type": "http",
      "direction": "out",
      "name": "res"
    }
  ],
  "scriptFile": "__init__.py"
}
```

---

## __init__.py
```python
import os
import json
import azure.functions as func
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# Default maximum characters per chunk (override via environment variable)
DEFAULT_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "5000"))
# Default maximum chunks returned per request (override via environment variable)
DEFAULT_MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "5"))


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname in ('youtu.be',):
        return parsed.path.lstrip('/')
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        params = parse_qs(parsed.query)
        return params.get('v', [None])[0]
    return None


def chunk_text(text: str, size: int) -> list[dict]:
    return [
        {"index": idx, "text": text[i : i + size]}
        for idx, i in enumerate(range(0, len(text), size))
    ]


def paginate_chunks(chunks: list[dict], start: int, max_chunks: int) -> dict:
    total = len(chunks)
    end = min(start + max_chunks, total)
    page = chunks[start:end]
    next_index = end if end < total else None
    return {"chunks": page, "next_index": next_index, "total_chunks": total}


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        url = body.get('url')
        if not url:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'url' parameter."}),
                status_code=400, mimetype="application/json"
            )

        video_id = extract_video_id(url)
        if not video_id:
            return func.HttpResponse(
                json.dumps({"error": "Invalid YouTube URL."}),
                status_code=400, mimetype="application/json"
            )

        # Parameters
        chunk_size = int(body.get('chunk_size', DEFAULT_CHUNK_SIZE))
        max_chunks = int(body.get('max_chunks', DEFAULT_MAX_CHUNKS))
        start_index = int(body.get('start_index', 0))
        language = body.get('language', 'en')

        # Fetch and prepare transcript
        transcript_entries = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=[language] if language else None
        )
        full_text = " ".join(entry['text'] for entry in transcript_entries)
        all_chunks = chunk_text(full_text, chunk_size)

        # Paginate
        page_data = paginate_chunks(all_chunks, start_index, max_chunks)
        payload = {
            "video_id": video_id,
            "total_characters": len(full_text),
            **page_data
        }

        response = func.HttpResponse(
            json.dumps(payload, ensure_ascii=False),
            status_code=200, mimetype="application/json"
        )
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except json.JSONDecodeError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON payload."}),
            status_code=400, mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": f"Error: {str(e)}"}),
            status_code=500, mimetype="application/json"
        )
```

---

### requirements.txt
```
azure-functions
youtube-transcript-api
```

**New Pagination Features:**
- **`start_index` & `max_chunks`**: Request any page of chunks.
- **`next_index`**: Pointer to retrieve the next page (or `null` if done).
- **`total_chunks`**: Total number of available chunks.

This ensures ChatGPT can iteratively pull captions in manageable batches, regardless of transcript length.
