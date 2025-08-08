import os
import json
import logging
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Union, List
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
from youtube_transcript_api.proxies import WebshareProxyConfig
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key from environment
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.warning("API_KEY environment variable not set. API will run without authentication.")

# Default maximum characters per chunk (override via environment variable)
DEFAULT_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "5000"))
# Default maximum chunks returned per request (override via environment variable)
DEFAULT_MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "5"))

app = FastAPI(
    title="YouTube Caption API",
    description="REST API for retrieving YouTube video transcripts/captions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme for API key authentication
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the API key from the Authorization header."""
    if not API_KEY:
        # If no API key is configured, skip authentication
        return True
    
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Invalid API key"
        )
    return True

class CaptionRequest(BaseModel):
    url: str
    chunk_size: Optional[int] = DEFAULT_CHUNK_SIZE
    max_chunks: Optional[int] = DEFAULT_MAX_CHUNKS
    start_index: Optional[int] = 0
    language: Optional[Union[str, List[str]]] = None

def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        if parsed.hostname in ('youtu.be',):
            return parsed.path.lstrip('/')
        if parsed.hostname in ('www.youtube.com', 'youtube.com'):
            params = parse_qs(parsed.query)
            return params.get('v', [None])[0]
        return None
    except Exception:
        return None

def chunk_text(text: str, size: int) -> list[dict]:
    """Split text into chunks of specified size."""
    if not text or size <= 0:
        return []
    
    return [
        {"index": idx, "text": text[i : i + size]}
        for idx, i in enumerate(range(0, len(text), size))
    ]

def paginate_chunks(chunks: list[dict], start: int, max_chunks: int) -> dict:
    """Paginate chunks for response."""
    if not chunks:
        return {"chunks": [], "next_index": None, "total_chunks": 0}
    
    total = len(chunks)
    start = max(0, start)  # Ensure start is not negative
    end = min(start + max_chunks, total)
    page = chunks[start:end]
    next_index = end if end < total else None
    return {"chunks": page, "next_index": next_index, "total_chunks": total}

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}

@app.post("/func_ytb_caption")
async def get_youtube_caption(request: CaptionRequest, _: bool = Depends(verify_api_key)):
    """Retrieve YouTube captions with pagination."""
    logger.info('YouTube caption function processed a request.')

    try:
        video_id = extract_video_id(request.url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL.")

        # Parameters
        chunk_size = request.chunk_size
        max_chunks = request.max_chunks
        start_index = request.start_index
        languages_param = request.language
        
        # Initialize YouTube Transcript API with modern v2 approach and optional proxy
        proxy_config = None
        use_proxy = os.getenv("USE_PROXY", "0") == "1"
        
        if use_proxy:
            proxy_username = os.getenv("WEBSHARE_PROXY_USERNAME")
            proxy_password = os.getenv("WEBSHARE_PROXY_PASSWORD")
            
            if not proxy_username or not proxy_password:
                logger.warning("Proxy enabled but credentials missing. Proceeding without proxy.")
            else:
                proxy_config = WebshareProxyConfig(
                    proxy_username=proxy_username,
                    proxy_password=proxy_password
                )
                logger.info("Using Webshare proxy for YouTube API requests")
        
        ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        
        # Get available transcripts for the video
        transcript_list = ytt_api.list(video_id)
        
        # Handle language parameter with smart fallback
        if languages_param:
            # User specified language(s) - convert to list if needed
            if isinstance(languages_param, str):
                requested_languages = [languages_param]
            else:
                requested_languages = languages_param
            
            # Try to find transcript in requested language(s)
            try:
                transcript = transcript_list.find_transcript(requested_languages)
            except NoTranscriptFound:
                # Try translation if direct transcript not available
                try:
                    # Find any available transcript that can be translated
                    available_transcript = None
                    for t in transcript_list:
                        if t.is_translatable and requested_languages[0] in [lang.language_code for lang in t.translation_languages]:
                            available_transcript = t
                            break
                    
                    if available_transcript:
                        transcript = available_transcript.translate(requested_languages[0])
                    else:
                        raise NoTranscriptFound(video_id, requested_languages, [])
                except:
                    raise NoTranscriptFound(video_id, requested_languages, [])
        else:
            # No language specified - use best available transcript
            # Priority: manually created English > any manually created > auto-generated English > any auto-generated
            transcript = None
            
            # Try manually created transcripts first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except NoTranscriptFound:
                try:
                    # Try any manually created transcript
                    for t in transcript_list:
                        if not t.is_generated:
                            transcript = t
                            break
                except:
                    pass
            
            # Fall back to auto-generated if no manual transcripts
            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except NoTranscriptFound:
                    # Use first available auto-generated transcript
                    for t in transcript_list:
                        if t.is_generated:
                            transcript = t
                            break
                
                # If still no transcript, use any available transcript
                if not transcript:
                    for t in transcript_list:
                        transcript = t
                        break
            
            # If still no transcript found, raise error
            if not transcript:
                raise NoTranscriptFound(video_id, [], [])
        
        # Fetch the actual transcript data
        fetched_transcript = transcript.fetch()
        
        # Extract text from snippets (modern API returns FetchedTranscript with snippets)
        full_text = " ".join(snippet.text for snippet in fetched_transcript)
        all_chunks = chunk_text(full_text, chunk_size)

        # Paginate
        page_data = paginate_chunks(all_chunks, start_index, max_chunks)
        
        # Collect available languages metadata
        available_languages = []
        for t in transcript_list:
            lang_info = {
                "language": t.language,
                "language_code": t.language_code,
                "is_generated": t.is_generated,
                "is_translatable": t.is_translatable,
            }
            if t.is_translatable:
                lang_info["translation_languages"] = [lang.language_code for lang in t.translation_languages]
            available_languages.append(lang_info)
        
        # Enhanced payload with metadata
        payload = {
            "video_id": video_id,
            "total_characters": len(full_text),
            "selected_language": fetched_transcript.language,
            "selected_language_code": fetched_transcript.language_code,
            "is_generated": fetched_transcript.is_generated,
            "available_languages": available_languages,
            **page_data
        }

        return payload

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except VideoUnavailable as e:
        logger.warning(f"Video unavailable {video_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Video is unavailable or private.")
    except TranscriptsDisabled as e:
        logger.warning(f"Transcripts disabled for video {video_id}: {str(e)}")
        raise HTTPException(status_code=403, detail="Transcripts are disabled for this video.")
    except NoTranscriptFound as e:
        logger.warning(f"No transcript found for video {video_id}: {str(e)}")
        raise HTTPException(
            status_code=404, 
            detail="No transcript available for this video in the requested language(s)."
        )
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid parameter value: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)