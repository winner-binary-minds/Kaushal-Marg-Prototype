import pytest
from unittest.mock import patch, MagicMock
from voice.audio import AudioTranscriber
from ai.gemini import GeminiQuotaError
from google.genai import errors

class TestAudioTranscription:

    @patch('google.genai.models.Models.generate_content')
    @patch('google.genai.files.Files.upload')
    def test_transcription_success_fixture(self, mock_upload, mock_generate):
        """Verify the test_speech.wav fixture correctly transcribes using mock API logic."""
        with open("tests/fixtures/test_speech.wav", "rb") as f:
            audio_bytes = f.read()

        # Mock the file upload to return a dummy file object
        mock_upload.return_value = MagicMock()
        
        # Mock the generate_content response to return known text
        mock_response = MagicMock()
        mock_response.text = "Suresh is looking for tailoring opportunities."
        mock_generate.return_value = mock_response

        transcriber = AudioTranscriber()
        result = transcriber.transcribe(audio_bytes, "en", "audio/wav")
        
        assert not result.is_empty, "Result should not be empty"
        assert "Suresh" in result.text or "tailoring" in result.text.lower(), "Should contain expected words"
        mock_upload.assert_called_once()
        mock_generate.assert_called_once()

    @patch('google.genai.models.Models.generate_content')
    @patch('google.genai.files.Files.upload')
    def test_429_quota_no_retries(self, mock_upload, mock_generate):
        """Verify that a 429 error throws immediately and does not retry."""
        mock_upload.return_value = MagicMock()
        mock_generate.side_effect = Exception("429 Resource Exhausted. Please retry in 40s.")
        
        transcriber = AudioTranscriber()
        
        with pytest.raises(GeminiQuotaError) as exc_info:
            transcriber.transcribe(b'dummy_bytes_1234567890_pad_to_64_bytes' + b'0'*40, "en", "audio/wav")
            
        assert exc_info.value.retry_delay == 40
        assert mock_generate.call_count == 1, "Should only be called exactly ONCE (no retries)"
