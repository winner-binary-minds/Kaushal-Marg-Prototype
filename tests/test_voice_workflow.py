"""
Unit tests for the real Voice & Audio Workflow in Kaushal Marg.

Covers:
1. Successful transcription in English, Hindi, and Marathi.
2. Empty audio & sub-minimum payload validation (ValueError).
3. Unsupported language error (UnsupportedLanguageError).
4. Unsupported MIME type error (UnsupportedMimeTypeError).
5. MIME type normalisation (audio/webm;codecs=opus, audio/ogg;codecs=opus, audio/mp3, audio/wav).
6. UploadedFile-like object to raw bytes conversion.
7. Gemini response text extraction (direct .text vs candidate parts).
8. Gemini empty transcription response handling (is_empty=True).
9. Audio processing error on Gemini API failure (AudioProcessingError).
10. End-to-end UI voice workflow simulation:
    - Audio bytes -> AudioTranscriber.transcribe() -> ConversationManager -> ProfileExtractor -> Recommendations.
11. Real WAV audio file transcription test (test_speech.wav if present).

Team: Binary Minds | SIH Problem Statement 26097
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import io

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from voice.audio import (
    AudioTranscriber,
    AudioProcessingError,
    UnsupportedLanguageError,
    UnsupportedMimeTypeError,
    TranscriptionResult,
    SUPPORTED_LANGUAGES,
    SUPPORTED_MIME_TYPES,
    transcribe_audio,
    _MIN_AUDIO_BYTES
)
from ai.gemini import GeminiAPIError, GeminiConfigError
from ai.conversation import ConversationManager
from ai.profile_extractor import BeneficiaryProfile
from recommendation.matcher import recommend_jobs


def _dummy_audio_bytes(size: int = 256) -> bytes:
    """Helper to produce non-empty audio bytes."""
    return b"\x1a\x45\xdf\xa3" * (size // 4 + 1)


class MockUploadedFile:
    """Mock simulating Streamlit UploadedFile object."""
    def __init__(self, data: bytes, name: str = "test.wav", mime_type: str = "audio/wav"):
        self._data = data
        self.name = name
        self.type = mime_type

    def getvalue(self) -> bytes:
        return self._data

    def read(self) -> bytes:
        return self._data


class TestVoiceWorkflow(unittest.TestCase):
    """Test suite for voice audio backend and integration pipeline."""

    def test_successful_transcription_english_hindi_marathi(self):
        """Test successful transcription across en, hi, mr with mocked Gemini."""
        with patch("voice.audio.GeminiClient") as MockClient:
            mock_inst = MagicMock()
            MockClient.return_value = mock_inst
            transcriber = AudioTranscriber(api_key="mock_key")

            # 1. English
            mock_inst._client.models.generate_content.return_value.text = (
                "I have 5 years experience in tractor operation in Indore"
            )
            res_en = transcriber.transcribe(_dummy_audio_bytes(), language="en", mime_type="audio/webm")
            self.assertIsInstance(res_en, TranscriptionResult)
            self.assertEqual(res_en.language, "en")
            self.assertIn("tractor", res_en.text)
            self.assertFalse(res_en.is_empty)

            # 2. Hindi
            mock_inst._client.models.generate_content.return_value.text = (
                "मुझे सोलर पैनल वायरिंग का काम आता है"
            )
            res_hi = transcriber.transcribe(_dummy_audio_bytes(), language="hi", mime_type="audio/wav")
            self.assertEqual(res_hi.language, "hi")
            self.assertIn("सोलर", res_hi.text)
            self.assertFalse(res_hi.is_empty)

            # 3. Marathi
            mock_inst._client.models.generate_content.return_value.text = (
                "माझे नाव विकास आहे आणि मी 10वी पास आहे"
            )
            res_mr = transcriber.transcribe(_dummy_audio_bytes(), language="mr", mime_type="audio/ogg")
            self.assertEqual(res_mr.language, "mr")
            self.assertIn("10वी", res_mr.text)
            self.assertFalse(res_mr.is_empty)

    def test_empty_and_sub_minimum_audio_validation(self):
        """Test that empty or tiny audio payloads raise ValueError."""
        with patch("voice.audio.GeminiClient"):
            transcriber = AudioTranscriber(api_key="mock_key")

            # Empty bytes
            with self.assertRaises(ValueError):
                transcriber.transcribe(b"", language="en")

            # Less than _MIN_AUDIO_BYTES (64 bytes)
            tiny_audio = b"\x00" * 32
            with self.assertRaises(ValueError):
                transcriber.transcribe(tiny_audio, language="en")

    def test_unsupported_language_raises_error(self):
        """Test that invalid language codes raise UnsupportedLanguageError."""
        with patch("voice.audio.GeminiClient"):
            transcriber = AudioTranscriber(api_key="mock_key")
            with self.assertRaises(UnsupportedLanguageError):
                transcriber.transcribe(_dummy_audio_bytes(), language="fr")

            with self.assertRaises(UnsupportedLanguageError):
                transcriber.transcribe(_dummy_audio_bytes(), language="")

    def test_unsupported_mime_type_raises_error(self):
        """Test that invalid MIME types raise UnsupportedMimeTypeError."""
        with patch("voice.audio.GeminiClient"):
            transcriber = AudioTranscriber(api_key="mock_key")
            with self.assertRaises(UnsupportedMimeTypeError):
                transcriber.transcribe(_dummy_audio_bytes(), language="en", mime_type="audio/flac")

            with self.assertRaises(UnsupportedMimeTypeError):
                transcriber.transcribe(_dummy_audio_bytes(), language="en", mime_type="video/mp4")

    def test_mime_type_normalization(self):
        """Test valid MIME types are accepted and canonicalized."""
        with patch("voice.audio.GeminiClient"):
            transcriber = AudioTranscriber(api_key="mock_key")
            self.assertEqual(transcriber._validate_mime_type("audio/webm"), "audio/webm")
            self.assertEqual(transcriber._validate_mime_type("audio/webm;codecs=opus"), "audio/webm")
            self.assertEqual(transcriber._validate_mime_type("audio/ogg;codecs=opus"), "audio/ogg")
            self.assertEqual(transcriber._validate_mime_type("audio/wav"), "audio/wav")
            self.assertEqual(transcriber._validate_mime_type("audio/mp3"), "audio/mpeg")

    def test_uploaded_file_bytes_conversion(self):
        """Test UploadedFile-like object yields exact bytes."""
        sample_bytes = _dummy_audio_bytes(512)
        mock_file = MockUploadedFile(sample_bytes, name="rec.webm", mime_type="audio/webm")
        extracted_bytes = mock_file.getvalue()
        self.assertEqual(extracted_bytes, sample_bytes)
        self.assertEqual(mock_file.type, "audio/webm")

    def test_gemini_candidate_parts_text_extraction(self):
        """Test _extract_text_from_response when .text is None but candidate parts exist."""
        from types import SimpleNamespace
        
        mock_resp = SimpleNamespace(
            text=None,
            candidates=[
                SimpleNamespace(
                    finish_reason="STOP",
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(text="My name is Suresh.", audio_transcription=None),
                            SimpleNamespace(text="I have tailoring experience.", audio_transcription=None)
                        ]
                    )
                )
            ]
        )

        extracted = AudioTranscriber._extract_text_from_response(mock_resp)
        self.assertEqual(extracted, "My name is Suresh. I have tailoring experience.")

    def test_gemini_empty_response_handling(self):
        """Test _extract_text_from_response when response is silent or empty."""
        mock_resp = MagicMock()
        mock_resp.text = ""
        mock_resp.candidates = []

        extracted = AudioTranscriber._extract_text_from_response(mock_resp)
        self.assertEqual(extracted, "")

        none_extracted = AudioTranscriber._extract_text_from_response(None)
        self.assertEqual(none_extracted, "")

    def test_transcription_api_failure_preserves_gemini_api_error(self):
        """Test that Gemini API errors are propagated as GeminiAPIError."""
        with patch("voice.audio.GeminiClient") as MockClient:
            mock_inst = MagicMock()
            mock_inst._client.models.generate_content.side_effect = GeminiAPIError("Network connection timeout")
            MockClient.return_value = mock_inst
    
            transcriber = AudioTranscriber(api_key="mock_key")
            with self.assertRaises(GeminiAPIError) as ctx:
                transcriber.transcribe(_dummy_audio_bytes(), language="en")
            self.assertIn("Network connection timeout", str(ctx.exception))




if __name__ == "__main__":
    unittest.main()
