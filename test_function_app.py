import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import azure.functions as func
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound

from function_app import (
    extract_video_id,
    chunk_text,
    paginate_chunks,
    func_ytb_caption
)


class TestExtractVideoId:
    """Test the extract_video_id helper function."""
    
    def test_extract_video_id_youtube_com(self):
        """Test extraction from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_extract_video_id_youtube_com_without_www(self):
        """Test extraction from YouTube URL without www."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_extract_video_id_youtu_be(self):
        """Test extraction from shortened YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_extract_video_id_with_parameters(self):
        """Test extraction from URL with additional parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123&list=playlist"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid_url(self):
        """Test with invalid URL."""
        url = "https://example.com/video"
        result = extract_video_id(url)
        assert result is None
    
    def test_extract_video_id_empty_url(self):
        """Test with empty URL."""
        result = extract_video_id("")
        assert result is None
    
    def test_extract_video_id_none(self):
        """Test with None URL."""
        result = extract_video_id(None)
        assert result is None


class TestChunkText:
    """Test the chunk_text helper function."""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "Hello world this is a test"
        size = 10
        result = chunk_text(text, size)
        expected = [
            {"index": 0, "text": "Hello worl"},
            {"index": 1, "text": "d this is "},
            {"index": 2, "text": "a test"}
        ]
        assert result == expected
    
    def test_chunk_text_exact_size(self):
        """Test chunking when text length equals chunk size."""
        text = "Hello"
        size = 5
        result = chunk_text(text, size)
        expected = [{"index": 0, "text": "Hello"}]
        assert result == expected
    
    def test_chunk_text_smaller_than_size(self):
        """Test chunking when text is smaller than chunk size."""
        text = "Hi"
        size = 10
        result = chunk_text(text, size)
        expected = [{"index": 0, "text": "Hi"}]
        assert result == expected
    
    def test_chunk_text_empty_string(self):
        """Test with empty string."""
        result = chunk_text("", 10)
        assert result == []
    
    def test_chunk_text_zero_size(self):
        """Test with zero chunk size."""
        result = chunk_text("Hello", 0)
        assert result == []
    
    def test_chunk_text_negative_size(self):
        """Test with negative chunk size."""
        result = chunk_text("Hello", -5)
        assert result == []


class TestPaginateChunks:
    """Test the paginate_chunks helper function."""
    
    def test_paginate_chunks_basic(self):
        """Test basic pagination."""
        chunks = [
            {"index": 0, "text": "chunk1"},
            {"index": 1, "text": "chunk2"},
            {"index": 2, "text": "chunk3"},
            {"index": 3, "text": "chunk4"}
        ]
        result = paginate_chunks(chunks, 0, 2)
        expected = {
            "chunks": [{"index": 0, "text": "chunk1"}, {"index": 1, "text": "chunk2"}],
            "next_index": 2,
            "total_chunks": 4
        }
        assert result == expected
    
    def test_paginate_chunks_last_page(self):
        """Test pagination on last page."""
        chunks = [
            {"index": 0, "text": "chunk1"},
            {"index": 1, "text": "chunk2"},
            {"index": 2, "text": "chunk3"}
        ]
        result = paginate_chunks(chunks, 2, 2)
        expected = {
            "chunks": [{"index": 2, "text": "chunk3"}],
            "next_index": None,
            "total_chunks": 3
        }
        assert result == expected
    
    def test_paginate_chunks_empty_list(self):
        """Test with empty chunks list."""
        result = paginate_chunks([], 0, 5)
        expected = {
            "chunks": [],
            "next_index": None,
            "total_chunks": 0
        }
        assert result == expected
    
    def test_paginate_chunks_negative_start(self):
        """Test with negative start index."""
        chunks = [{"index": 0, "text": "chunk1"}]
        result = paginate_chunks(chunks, -1, 1)
        expected = {
            "chunks": [{"index": 0, "text": "chunk1"}],
            "next_index": None,
            "total_chunks": 1
        }
        assert result == expected
    
    def test_paginate_chunks_start_beyond_length(self):
        """Test with start index beyond chunks length."""
        chunks = [{"index": 0, "text": "chunk1"}]
        result = paginate_chunks(chunks, 5, 1)
        expected = {
            "chunks": [],
            "next_index": None,
            "total_chunks": 1
        }
        assert result == expected


class TestFuncYtbCaption:
    """Test the main Azure Function."""
    
    def create_mock_request(self, body_dict):
        """Helper to create mock HTTP request."""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = body_dict
        return mock_req
    
    def create_mock_transcript_snippet(self, text):
        """Helper to create mock transcript snippet."""
        snippet = Mock()
        snippet.text = text
        return snippet
    
    def create_mock_fetched_transcript(self, snippets, language="English", language_code="en", is_generated=False):
        """Helper to create mock FetchedTranscript."""
        transcript = Mock()
        transcript.__iter__ = Mock(return_value=iter(snippets))
        transcript.language = language
        transcript.language_code = language_code
        transcript.is_generated = is_generated
        return transcript
    
    def create_mock_transcript(self, language="English", language_code="en", is_generated=False, is_translatable=False, translation_languages=None):
        """Helper to create mock Transcript object."""
        transcript = Mock()
        transcript.language = language
        transcript.language_code = language_code
        transcript.is_generated = is_generated
        transcript.is_translatable = is_translatable
        transcript.translation_languages = translation_languages or []
        return transcript
    
    def create_mock_transcript_list(self, transcripts):
        """Helper to create mock TranscriptList."""
        transcript_list = Mock()
        transcript_list.__iter__ = Mock(return_value=iter(transcripts))
        transcript_list.find_transcript = Mock()
        transcript_list.find_manually_created_transcript = Mock()
        transcript_list.find_generated_transcript = Mock()
        return transcript_list
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_success(self, mock_api_class):
        """Test successful transcript retrieval with specified language."""
        # Setup
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        snippets = [
            self.create_mock_transcript_snippet("Hello world"),
            self.create_mock_transcript_snippet("this is a test")
        ]
        mock_fetched_transcript = self.create_mock_fetched_transcript(snippets)
        
        # Mock transcript and transcript list
        mock_transcript = self.create_mock_transcript()
        mock_transcript.fetch.return_value = mock_fetched_transcript
        
        mock_transcript_list = self.create_mock_transcript_list([mock_transcript])
        mock_transcript_list.find_transcript.return_value = mock_transcript
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "chunk_size": 10,
            "max_chunks": 2,
            "start_index": 0,
            "language": "en"
        }
        mock_req = self.create_mock_request(request_body)
        
        # Execute
        response = func_ytb_caption(mock_req)
        
        # Verify
        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        
        assert response_data["video_id"] == "dQw4w9WgXcQ"
        assert response_data["selected_language"] == "English"
        assert response_data["selected_language_code"] == "en"
        assert response_data["is_generated"] == False
        assert response_data["total_characters"] == 26  # "Hello world this is a test" with space
        assert len(response_data["chunks"]) == 2
        assert "available_languages" in response_data
        
        mock_api.list.assert_called_once_with("dQw4w9WgXcQ")
        mock_transcript_list.find_transcript.assert_called_once_with(["en"])
    
    def test_func_ytb_caption_missing_body(self):
        """Test with missing request body."""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = None
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert "Request body is required" in response_data["error"]
    
    def test_func_ytb_caption_missing_url(self):
        """Test with missing URL parameter."""
        request_body = {"chunk_size": 5000}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert "Missing 'url' parameter" in response_data["error"]
    
    def test_func_ytb_caption_invalid_url(self):
        """Test with invalid YouTube URL."""
        request_body = {"url": "https://example.com/video"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert "Invalid YouTube URL" in response_data["error"]
    
    def test_func_ytb_caption_invalid_json(self):
        """Test with invalid JSON payload."""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body())
        assert "Invalid JSON payload" in response_data["error"]
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_no_transcript_found(self, mock_api_class):
        """Test when no transcript is found."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        mock_transcript_list = self.create_mock_transcript_list([])
        mock_transcript_list.find_manually_created_transcript.side_effect = NoTranscriptFound("video_id", [], [])
        mock_transcript_list.find_generated_transcript.side_effect = NoTranscriptFound("video_id", [], [])
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 404
        response_data = json.loads(response.get_body())
        assert "No transcript available" in response_data["error"]
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_video_unavailable(self, mock_api_class):
        """Test when video is unavailable."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_api.list.side_effect = VideoUnavailable("video_id")
        
        request_body = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 404
        response_data = json.loads(response.get_body())
        assert "Video is unavailable" in response_data["error"]
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_transcripts_disabled(self, mock_api_class):
        """Test when transcripts are disabled."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_api.list.side_effect = TranscriptsDisabled("video_id")
        
        request_body = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 403
        response_data = json.loads(response.get_body())
        assert "Transcripts are disabled" in response_data["error"]
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_with_language_list(self, mock_api_class):
        """Test with language parameter as list."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        snippets = [self.create_mock_transcript_snippet("Hello")]
        mock_fetched_transcript = self.create_mock_fetched_transcript(snippets)
        
        mock_transcript = self.create_mock_transcript()
        mock_transcript.fetch.return_value = mock_fetched_transcript
        
        mock_transcript_list = self.create_mock_transcript_list([mock_transcript])
        mock_transcript_list.find_transcript.return_value = mock_transcript
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "language": ["de", "en"]
        }
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 200
        mock_api.list.assert_called_once_with("dQw4w9WgXcQ")
        mock_transcript_list.find_transcript.assert_called_once_with(["de", "en"])
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_default_parameters(self, mock_api_class):
        """Test with default parameters (auto language detection)."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        snippets = [self.create_mock_transcript_snippet("Hello world")]
        mock_fetched_transcript = self.create_mock_fetched_transcript(snippets)
        
        mock_transcript = self.create_mock_transcript()
        mock_transcript.fetch.return_value = mock_fetched_transcript
        
        mock_transcript_list = self.create_mock_transcript_list([mock_transcript])
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        
        # Should use default values
        assert len(response_data["chunks"]) <= 5  # DEFAULT_MAX_CHUNKS
        assert "available_languages" in response_data
        mock_api.list.assert_called_once_with("dQw4w9WgXcQ")
        mock_transcript_list.find_manually_created_transcript.assert_called_once_with(["en"])
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_pagination(self, mock_api_class):
        """Test pagination functionality."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        # Create long text that will be chunked
        long_text = "A" * 100  # 100 character string
        snippets = [self.create_mock_transcript_snippet(long_text)]
        mock_fetched_transcript = self.create_mock_fetched_transcript(snippets)
        
        mock_transcript = self.create_mock_transcript()
        mock_transcript.fetch.return_value = mock_fetched_transcript
        
        mock_transcript_list = self.create_mock_transcript_list([mock_transcript])
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "chunk_size": 10,
            "max_chunks": 2,
            "start_index": 0
        }
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        
        assert len(response_data["chunks"]) == 2
        assert response_data["next_index"] == 2
        assert response_data["total_chunks"] == 10  # 100 chars / 10 chars per chunk
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_cors_headers(self, mock_api_class):
        """Test that CORS headers are set."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        snippets = [self.create_mock_transcript_snippet("Hello")]
        mock_fetched_transcript = self.create_mock_fetched_transcript(snippets)
        
        mock_transcript = self.create_mock_transcript()
        mock_transcript.fetch.return_value = mock_fetched_transcript
        
        mock_transcript_list = self.create_mock_transcript_list([mock_transcript])
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 200
        assert response.headers.get('Access-Control-Allow-Origin') == '*'


    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_auto_language_fallback(self, mock_api_class):
        """Test automatic language fallback when no language specified."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        snippets = [self.create_mock_transcript_snippet("Hola mundo")]
        mock_fetched_transcript = self.create_mock_fetched_transcript(
            snippets, language="Spanish", language_code="es", is_generated=True
        )
        
        # Create mock transcripts - no English manual, but Spanish auto-generated available
        spanish_transcript = self.create_mock_transcript(
            language="Spanish", language_code="es", is_generated=True
        )
        spanish_transcript.fetch.return_value = mock_fetched_transcript
        
        transcripts = [spanish_transcript]
        mock_transcript_list = self.create_mock_transcript_list(transcripts)
        mock_transcript_list.find_manually_created_transcript.side_effect = NoTranscriptFound("video_id", [], [])
        mock_transcript_list.find_generated_transcript.side_effect = NoTranscriptFound("video_id", [], [])
        # Fix iteration to work correctly  
        mock_transcript_list.__iter__ = lambda self: iter(transcripts)
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data["selected_language"] == "Spanish"
        assert response_data["selected_language_code"] == "es"
        assert response_data["is_generated"] == True
    
    @patch('function_app.YouTubeTranscriptApi')
    def test_func_ytb_caption_translation_fallback(self, mock_api_class):
        """Test translation fallback when requested language not directly available."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        snippets = [self.create_mock_transcript_snippet("Hello world translated")]
        mock_fetched_transcript = self.create_mock_fetched_transcript(
            snippets, language="English (auto-translated)", language_code="en"
        )
        
        # Mock original transcript that can be translated
        original_transcript = self.create_mock_transcript(
            language="Vietnamese", language_code="vi", is_generated=True, 
            is_translatable=True, translation_languages=[Mock(language_code="en")]
        )
        
        # Mock translated transcript
        translated_transcript = Mock()
        translated_transcript.fetch.return_value = mock_fetched_transcript
        original_transcript.translate.return_value = translated_transcript
        
        mock_transcript_list = self.create_mock_transcript_list([original_transcript])
        mock_transcript_list.find_transcript.side_effect = NoTranscriptFound("video_id", [], [])
        
        mock_api.list.return_value = mock_transcript_list
        
        request_body = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "language": "en"
        }
        mock_req = self.create_mock_request(request_body)
        
        response = func_ytb_caption(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body())
        assert response_data["selected_language"] == "English (auto-translated)"
        original_transcript.translate.assert_called_once_with("en")


if __name__ == "__main__":
    pytest.main([__file__])