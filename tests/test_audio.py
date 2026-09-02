"""
Tests for voice/audio.py

Covers (zero real API calls, zero microphone, zero browser):
- AudioTranscriber initialisation (valid / invalid)
- transcribe(): English, Hindi, Marathi
- TranscriptionResult fields and is_empty property
- _call_gemini() constructs correct types.Part / types.Blob multimodal payload
- UnsupportedLanguageError for invalid language codes
- UnsupportedMimeTypeError for unsupported MIME types
- ValueError for invalid audio bytes (empty, too small, wrong type)
- AudioProcessingError wraps GeminiAPIError correctly
- Supported MIME type normalisation (strips codec suffix, lowercases)
- Module-level transcribe_audio() convenience function
- Raw audio bytes are never logged
- GeminiClient mock: all calls go through mock, no real network traffic
"""

import logging
import pytest
from unittest.mock import MagicMock, patch, call

from voice.audio import (
    AudioTranscriber,
    AudioProcessingError,
    UnsupportedLanguageError,
    UnsupportedMimeTypeError,
    TranscriptionResult,
    SUPPORTED_LANGUAGES,
    SUPPORTED_MIME_TYPES,
    transcribe_audio,
    _MIN_AUDIO_BYTES,
)
from ai.gemini import GeminiAPIError, GeminiConfigError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio_bytes(size: int = 200) -> bytes:
    """Return a dummy bytes payload large enough to pass validation."""
    return b"\x00\x01\x02" * (size // 3 + 1)


def _make_transcriber(mock_client=None) -> AudioTranscriber:
    """Return an AudioTranscriber with a mocked GeminiClient."""
    with patch("voice.audio.GeminiClient") as MockClient:
        instance = MockClient.return_value
        if mock_client is not None:
            instance = mock_client
        transcriber = AudioTranscriber(api_key="test-key")
        transcriber._gemini = instance
        return transcriber


@pytest.fixture
def mock_gemini():
    """A MagicMock standing in for a GeminiClient instance."""
    m = MagicMock()
    m.model = "gemini-1.5-flash"
    m.max_output_tokens = 256
    # Simulate a successful response
    response = MagicMock()
    response.text = "Hello, I want to learn solar panel work."
    m._client.models.generate_content.return_value = response
    return m


@pytest.fixture
def transcriber(mock_gemini) -> AudioTranscriber:
    """AudioTranscriber with mocked Gemini client."""
    with patch("voice.audio.GeminiClient"):
        t = AudioTranscriber(api_key="test-key")
        t._gemini = mock_gemini
        return t


# ---------------------------------------------------------------------------
# TestSupportedConstants
# ---------------------------------------------------------------------------

class TestSupportedConstants:
    """Verify public constants are correct."""

    def test_supported_languages_has_en_hi_mr(self):
        assert SUPPORTED_LANGUAGES == {"en", "hi", "mr"}

    def test_supported_languages_is_frozenset(self):
        assert isinstance(SUPPORTED_LANGUAGES, frozenset)

    def test_supported_mime_types_has_webm(self):
        assert "audio/webm" in SUPPORTED_MIME_TYPES

    def test_supported_mime_types_has_ogg(self):
        assert "audio/ogg" in SUPPORTED_MIME_TYPES

    def test_supported_mime_types_has_wav(self):
        assert "audio/wav" in SUPPORTED_MIME_TYPES

    def test_supported_mime_types_has_mp4(self):
        assert "audio/mp4" in SUPPORTED_MIME_TYPES

    def test_supported_mime_types_has_codec_variants(self):
        assert "audio/webm;codecs=opus" in SUPPORTED_MIME_TYPES
        assert "audio/ogg;codecs=opus" in SUPPORTED_MIME_TYPES

    def test_min_audio_bytes_is_positive(self):
        assert _MIN_AUDIO_BYTES > 0


# ---------------------------------------------------------------------------
# TestAudioTranscriberInit
# ---------------------------------------------------------------------------

class TestAudioTranscriberInit:
    """Test AudioTranscriber initialisation."""

    def test_init_with_explicit_api_key(self):
        with patch("voice.audio.GeminiClient"):
            t = AudioTranscriber(api_key="test-key")
            assert t is not None

    def test_init_reads_from_env(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}):
            with patch("voice.audio.GeminiClient"):
                t = AudioTranscriber()
                assert t is not None

    def test_init_raises_gemini_config_error_on_bad_key(self):
        with patch("voice.audio.GeminiClient", side_effect=GeminiConfigError("no key")):
            with pytest.raises(GeminiConfigError):
                AudioTranscriber(api_key="")

    def test_init_passes_model_to_gemini_client(self):
        with patch("voice.audio.GeminiClient") as MockClient:
            AudioTranscriber(api_key="test-key", model="gemini-1.5-pro")
            kwargs = MockClient.call_args.kwargs
            assert kwargs.get("model") == "gemini-1.5-pro"

    def test_init_passes_max_output_tokens_to_gemini_client(self):
        with patch("voice.audio.GeminiClient") as MockClient:
            AudioTranscriber(api_key="test-key", max_output_tokens=128)
            kwargs = MockClient.call_args.kwargs
            assert kwargs.get("max_output_tokens") == 128

    def test_supported_languages_method(self, transcriber):
        assert transcriber.supported_languages() == frozenset({"en", "hi", "mr"})

    def test_supported_mime_types_method_returns_tuple(self, transcriber):
        result = transcriber.supported_mime_types()
        assert isinstance(result, tuple)
        assert "audio/webm" in result


# ---------------------------------------------------------------------------
# TestTranscriptionResultDataclass
# ---------------------------------------------------------------------------

class TestTranscriptionResultDataclass:
    """Test TranscriptionResult fields and properties."""

    def test_is_empty_false_for_non_empty_text(self):
        r = TranscriptionResult(text="Hello", language="en")
        assert r.is_empty is False

    def test_is_empty_true_for_empty_text(self):
        r = TranscriptionResult(text="", language="en")
        assert r.is_empty is True

    def test_str_returns_text(self):
        r = TranscriptionResult(text="नमस्ते", language="hi")
        assert str(r) == "नमस्ते"

    def test_language_stored(self):
        r = TranscriptionResult(text="test", language="mr")
        assert r.language == "mr"

    def test_frozen_cannot_mutate_text(self):
        r = TranscriptionResult(text="test", language="en")
        with pytest.raises((AttributeError, TypeError)):
            r.text = "changed"

    def test_frozen_cannot_mutate_language(self):
        r = TranscriptionResult(text="test", language="en")
        with pytest.raises((AttributeError, TypeError)):
            r.language = "hi"


# ---------------------------------------------------------------------------
# TestTranscribeEnglish
# ---------------------------------------------------------------------------

class TestTranscribeEnglish:
    """Test transcribe() with English language."""

    def test_returns_transcription_result(self, transcriber):
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert isinstance(result, TranscriptionResult)

    def test_language_stored_in_result(self, transcriber):
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert result.language == "en"

    def test_text_stripped(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value.text = (
            "  hello world  "
        )
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert result.text == "hello world"

    def test_gemini_called_once(self, transcriber):
        transcriber.transcribe(_make_audio_bytes(), language="en")
        transcriber._gemini._client.models.generate_content.assert_called_once()

    def test_result_not_empty_for_non_silent_audio(self, transcriber):
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert not result.is_empty


# ---------------------------------------------------------------------------
# TestTranscribeHindi
# ---------------------------------------------------------------------------

class TestTranscribeHindi:
    """Test transcribe() with Hindi language."""

    def test_hindi_language_accepted(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value.text = (
            "नमस्ते मेरा नाम अर्जुन है।"
        )
        result = transcriber.transcribe(_make_audio_bytes(), language="hi")
        assert isinstance(result, TranscriptionResult)
        assert result.language == "hi"

    def test_hindi_prompt_contains_hindi_language_name(self, transcriber):
        transcriber.transcribe(_make_audio_bytes(), language="hi")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        # Safely extract the contents list from kwargs
        contents = call_args.kwargs.get("contents", [])
        # Find the text part that contains the language hint
        found_hindi = False
        for content_item in contents:
            for part in getattr(content_item, "parts", []):
                text = getattr(part, "text", None)
                if text and "Hindi" in text:
                    found_hindi = True
        assert found_hindi, "Prompt should mention 'Hindi' for hi language"

    def test_hindi_text_returned_verbatim(self, transcriber):
        expected = "मुझे सोलर पैनल का काम पसंद है।"
        transcriber._gemini._client.models.generate_content.return_value.text = expected
        result = transcriber.transcribe(_make_audio_bytes(), language="hi")
        assert result.text == expected


# ---------------------------------------------------------------------------
# TestTranscribeMarathi
# ---------------------------------------------------------------------------

class TestTranscribeMarathi:
    """Test transcribe() with Marathi language."""

    def test_marathi_language_accepted(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value.text = (
            "माझे नाव विकास आहे."
        )
        result = transcriber.transcribe(_make_audio_bytes(), language="mr")
        assert isinstance(result, TranscriptionResult)
        assert result.language == "mr"

    def test_marathi_prompt_contains_marathi_language_name(self, transcriber):
        transcriber.transcribe(_make_audio_bytes(), language="mr")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or []
        found_marathi = False
        for content_item in contents:
            for part in content_item.parts:
                if part.text and "Marathi" in part.text:
                    found_marathi = True
        assert found_marathi, "Prompt should mention 'Marathi' for mr language"


# ---------------------------------------------------------------------------
# TestMultimodalPayload
# ---------------------------------------------------------------------------

class TestMultimodalPayload:
    """
    Verify the exact multimodal payload structure sent to Gemini.
    These tests validate the critical contract with the Gemini API.
    """

    def test_generate_content_receives_content_list(self, transcriber):
        """Gemini must receive a list of Content objects."""
        transcriber.transcribe(_make_audio_bytes(), language="en")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        assert isinstance(contents, list)
        assert len(contents) == 1

    def test_content_has_user_role(self, transcriber):
        transcriber.transcribe(_make_audio_bytes(), language="en")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        assert contents[0].role == "user"

    def test_content_has_two_parts(self, transcriber):
        """Content must have audio_part and text_part."""
        transcriber.transcribe(_make_audio_bytes(), language="en")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        assert len(contents[0].parts) == 2

    def test_first_part_has_inline_data(self, transcriber):
        """First part must be the audio blob (inline_data)."""
        audio = _make_audio_bytes()
        transcriber.transcribe(audio, language="en", mime_type="audio/webm")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        audio_part = contents[0].parts[0]
        assert audio_part.inline_data is not None
        assert audio_part.inline_data.data == audio
        assert audio_part.inline_data.mime_type == "audio/webm"

    def test_second_part_has_transcription_prompt_text(self, transcriber):
        """Second part must be the text prompt."""
        transcriber.transcribe(_make_audio_bytes(), language="en")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        text_part = contents[0].parts[1]
        assert text_part.text is not None
        assert "transcri" in text_part.text.lower()

    def test_ogg_mime_type_passed_to_blob(self, transcriber):
        transcriber.transcribe(
            _make_audio_bytes(), language="en", mime_type="audio/ogg"
        )
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        assert contents[0].parts[0].inline_data.mime_type == "audio/ogg"

    def test_codec_suffix_normalised_in_blob(self, transcriber):
        """'audio/webm;codecs=opus' should be normalised to 'audio/webm'."""
        transcriber.transcribe(
            _make_audio_bytes(), language="en", mime_type="audio/webm;codecs=opus"
        )
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        assert contents[0].parts[0].inline_data.mime_type == "audio/webm"

    def test_model_name_passed_to_generate_content(self, transcriber):
        transcriber.transcribe(_make_audio_bytes(), language="en")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        model_arg = call_args.kwargs.get("model") or call_args.args[0]
        assert model_arg == transcriber._gemini.model

    def test_generate_content_config_has_max_output_tokens(self, transcriber):
        transcriber.transcribe(_make_audio_bytes(), language="en")
        call_args = transcriber._gemini._client.models.generate_content.call_args
        config = call_args.kwargs.get("config")
        assert config is not None
        assert config.max_output_tokens == transcriber._gemini.max_output_tokens


# ---------------------------------------------------------------------------
# TestUnsupportedLanguageError
# ---------------------------------------------------------------------------

class TestUnsupportedLanguageError:
    """Test UnsupportedLanguageError raised for bad language codes."""

    def test_unsupported_code_raises(self, transcriber):
        with pytest.raises(UnsupportedLanguageError):
            transcriber.transcribe(_make_audio_bytes(), language="fr")

    def test_error_contains_bad_code(self, transcriber):
        with pytest.raises(UnsupportedLanguageError) as exc:
            transcriber.transcribe(_make_audio_bytes(), language="de")
        assert "de" in str(exc.value)

    def test_error_lists_supported_codes(self, transcriber):
        with pytest.raises(UnsupportedLanguageError) as exc:
            transcriber.transcribe(_make_audio_bytes(), language="es")
        msg = str(exc.value)
        assert "en" in msg and "hi" in msg and "mr" in msg

    def test_empty_string_raises(self, transcriber):
        with pytest.raises(UnsupportedLanguageError):
            transcriber.transcribe(_make_audio_bytes(), language="")

    def test_none_raises(self, transcriber):
        with pytest.raises(UnsupportedLanguageError):
            transcriber.transcribe(_make_audio_bytes(), language=None)

    def test_int_raises(self, transcriber):
        with pytest.raises(UnsupportedLanguageError):
            transcriber.transcribe(_make_audio_bytes(), language=1)

    def test_error_has_language_attribute(self, transcriber):
        try:
            transcriber.transcribe(_make_audio_bytes(), language="zz")
        except UnsupportedLanguageError as e:
            assert e.language == "zz"

    def test_error_has_supported_attribute(self, transcriber):
        try:
            transcriber.transcribe(_make_audio_bytes(), language="zz")
        except UnsupportedLanguageError as e:
            assert isinstance(e.supported, tuple)
            assert "en" in e.supported

    def test_is_value_error_subclass(self):
        assert issubclass(UnsupportedLanguageError, ValueError)

    def test_no_api_call_when_language_invalid(self, transcriber):
        with pytest.raises(UnsupportedLanguageError):
            transcriber.transcribe(_make_audio_bytes(), language="xx")
        transcriber._gemini._client.models.generate_content.assert_not_called()


# ---------------------------------------------------------------------------
# TestUnsupportedMimeTypeError
# ---------------------------------------------------------------------------

class TestUnsupportedMimeTypeError:
    """Test UnsupportedMimeTypeError raised for bad MIME types."""

    def test_unsupported_mime_raises(self, transcriber):
        with pytest.raises(UnsupportedMimeTypeError):
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="audio/flac")

    def test_error_contains_bad_mime(self, transcriber):
        with pytest.raises(UnsupportedMimeTypeError) as exc:
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="video/mp4")
        assert "video/mp4" in str(exc.value)

    def test_error_lists_accepted_types(self, transcriber):
        with pytest.raises(UnsupportedMimeTypeError) as exc:
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="image/png")
        msg = str(exc.value)
        assert "audio/webm" in msg

    def test_none_mime_raises(self, transcriber):
        with pytest.raises(UnsupportedMimeTypeError):
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type=None)

    def test_empty_string_mime_raises(self, transcriber):
        with pytest.raises(UnsupportedMimeTypeError):
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="")

    def test_error_has_mime_type_attribute(self, transcriber):
        try:
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="audio/flac")
        except UnsupportedMimeTypeError as e:
            assert e.mime_type == "audio/flac"

    def test_error_has_supported_attribute(self, transcriber):
        try:
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="audio/flac")
        except UnsupportedMimeTypeError as e:
            assert isinstance(e.supported, tuple)
            assert "audio/webm" in e.supported

    def test_is_value_error_subclass(self):
        assert issubclass(UnsupportedMimeTypeError, ValueError)

    def test_no_api_call_when_mime_invalid(self, transcriber):
        with pytest.raises(UnsupportedMimeTypeError):
            transcriber.transcribe(_make_audio_bytes(), language="en", mime_type="audio/flac")
        transcriber._gemini._client.models.generate_content.assert_not_called()


# ---------------------------------------------------------------------------
# TestInvalidAudioBytes
# ---------------------------------------------------------------------------

class TestInvalidAudioBytes:
    """Test ValueError raised for bad audio bytes."""

    def test_empty_bytes_raises(self, transcriber):
        with pytest.raises(ValueError):
            transcriber.transcribe(b"", language="en")

    def test_too_small_bytes_raises(self, transcriber):
        """Bytes below _MIN_AUDIO_BYTES must raise ValueError."""
        tiny = b"\x00" * (_MIN_AUDIO_BYTES - 1)
        with pytest.raises(ValueError):
            transcriber.transcribe(tiny, language="en")

    def test_none_raises(self, transcriber):
        with pytest.raises(ValueError):
            transcriber.transcribe(None, language="en")

    def test_string_raises(self, transcriber):
        with pytest.raises(ValueError):
            transcriber.transcribe("audio data", language="en")

    def test_list_raises(self, transcriber):
        with pytest.raises(ValueError):
            transcriber.transcribe([1, 2, 3], language="en")

    def test_int_raises(self, transcriber):
        with pytest.raises(ValueError):
            transcriber.transcribe(12345, language="en")

    def test_exactly_min_bytes_accepted(self, transcriber):
        """Exactly _MIN_AUDIO_BYTES should NOT raise."""
        exact = b"\x00" * _MIN_AUDIO_BYTES
        result = transcriber.transcribe(exact, language="en")
        assert isinstance(result, TranscriptionResult)

    def test_no_api_call_for_empty_bytes(self, transcriber):
        with pytest.raises(ValueError):
            transcriber.transcribe(b"", language="en")
        transcriber._gemini._client.models.generate_content.assert_not_called()


# ---------------------------------------------------------------------------
# TestSilentAudio
# ---------------------------------------------------------------------------

class TestSilentAudio:
    """Test handling of silent / unintelligible audio."""

    def test_empty_string_response_returns_empty_result(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value.text = ""
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert result.is_empty is True
        assert result.text == ""

    def test_none_response_text_returns_empty_result(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value.text = None
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert result.is_empty is True

    def test_whitespace_only_response_returns_empty(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value.text = "   "
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert result.is_empty is True

    def test_none_response_object_returns_empty(self, transcriber):
        transcriber._gemini._client.models.generate_content.return_value = None
        result = transcriber.transcribe(_make_audio_bytes(), language="en")
        assert result.is_empty is True


# ---------------------------------------------------------------------------
# TestAudioProcessingError
# ---------------------------------------------------------------------------

class TestAudioProcessingError:
    """Test AudioProcessingError wraps Gemini errors."""

    def test_gemini_api_error_wrapped_as_audio_processing_error(self, transcriber):
        transcriber._gemini._client.models.generate_content.side_effect = (
            GeminiAPIError("rate limit")
        )
        with pytest.raises(AudioProcessingError):
            transcriber.transcribe(_make_audio_bytes(), language="en")

    def test_audio_processing_error_has_cause(self, transcriber):
        original = GeminiAPIError("network error")
        transcriber._gemini._client.models.generate_content.side_effect = original
        with pytest.raises(AudioProcessingError) as exc:
            transcriber.transcribe(_make_audio_bytes(), language="en")
        # _call_gemini re-wraps the original GeminiAPIError into a new one
        # before it surfaces as AudioProcessingError.cause. Check that the
        # original error message is preserved somewhere in the chain.
        assert exc.value.cause is not None
        assert "network error" in str(exc.value)

    def test_generic_exception_wrapped(self, transcriber):
        transcriber._gemini._client.models.generate_content.side_effect = (
            RuntimeError("unexpected")
        )
        with pytest.raises(AudioProcessingError):
            transcriber.transcribe(_make_audio_bytes(), language="en")

    def test_error_message_contains_context(self, transcriber):
        transcriber._gemini._client.models.generate_content.side_effect = (
            GeminiAPIError("quota exceeded")
        )
        with pytest.raises(AudioProcessingError) as exc:
            transcriber.transcribe(_make_audio_bytes(), language="en")
        assert "quota exceeded" in str(exc.value)

    def test_is_exception_subclass(self):
        assert issubclass(AudioProcessingError, Exception)


# ---------------------------------------------------------------------------
# TestMimeTypeNormalisation
# ---------------------------------------------------------------------------

class TestMimeTypeNormalisation:
    """Test MIME type normalisation in _validate_mime_type."""

    @pytest.mark.parametrize("raw_mime,expected_canonical", [
        ("audio/webm", "audio/webm"),
        ("audio/webm;codecs=opus", "audio/webm"),
        ("AUDIO/WEBM", "audio/webm"),
        ("audio/ogg", "audio/ogg"),
        ("audio/ogg;codecs=opus", "audio/ogg"),
        ("audio/wav", "audio/wav"),
        ("audio/wave", "audio/wav"),
        ("audio/mp4", "audio/mp4"),
        ("audio/mpeg", "audio/mpeg"),
        ("audio/mp3", "audio/mpeg"),
    ])
    def test_mime_normalisation(self, transcriber, raw_mime, expected_canonical):
        transcriber.transcribe(_make_audio_bytes(), language="en", mime_type=raw_mime)
        call_args = transcriber._gemini._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents")
        actual_mime = contents[0].parts[0].inline_data.mime_type
        assert actual_mime == expected_canonical, (
            f"Expected '{expected_canonical}' for input '{raw_mime}', got '{actual_mime}'"
        )


# ---------------------------------------------------------------------------
# TestPrivacyLogging
# ---------------------------------------------------------------------------

class TestPrivacyLogging:
    """Verify raw audio bytes and transcribed text are not logged."""

    def test_audio_bytes_not_in_log_messages(self, transcriber, caplog):
        audio = _make_audio_bytes(200)
        audio_str = audio.hex()[:20]  # First 20 hex chars

        with caplog.at_level(logging.DEBUG, logger="voice.audio"):
            transcriber.transcribe(audio, language="en")

        for record in caplog.records:
            assert audio_str not in record.message, (
                f"Audio byte content found in log: {record.message}"
            )

    def test_transcribed_text_not_in_log_messages(self, transcriber, caplog):
        secret_text = "my-private-speech-content-xyz"
        transcriber._gemini._client.models.generate_content.return_value.text = secret_text

        with caplog.at_level(logging.DEBUG, logger="voice.audio"):
            transcriber.transcribe(_make_audio_bytes(), language="en")

        for record in caplog.records:
            assert secret_text not in record.message


# ---------------------------------------------------------------------------
# TestModuleLevelTranscribeAudio
# ---------------------------------------------------------------------------

class TestModuleLevelTranscribeAudio:
    """Test the module-level transcribe_audio() convenience function."""

    def test_returns_transcription_result(self):
        with patch("voice.audio.AudioTranscriber") as MockTranscriber:
            instance = MockTranscriber.return_value
            instance.transcribe.return_value = TranscriptionResult(
                text="hello", language="en"
            )
            result = transcribe_audio(_make_audio_bytes(), language="en")
        assert isinstance(result, TranscriptionResult)
        assert result.text == "hello"

    def test_passes_language_through(self):
        with patch("voice.audio.AudioTranscriber") as MockTranscriber:
            instance = MockTranscriber.return_value
            instance.transcribe.return_value = TranscriptionResult(
                text="नमस्ते", language="hi"
            )
            result = transcribe_audio(_make_audio_bytes(), language="hi")
        assert result.language == "hi"

    def test_passes_mime_type_through(self):
        with patch("voice.audio.AudioTranscriber") as MockTranscriber:
            instance = MockTranscriber.return_value
            instance.transcribe.return_value = TranscriptionResult(
                text="ok", language="en"
            )
            transcribe_audio(
                _make_audio_bytes(), language="en", mime_type="audio/ogg"
            )
            call_kwargs = instance.transcribe.call_args.kwargs
            assert call_kwargs.get("mime_type") == "audio/ogg"

    def test_unsupported_language_propagates(self):
        with patch("voice.audio.AudioTranscriber") as MockTranscriber:
            instance = MockTranscriber.return_value
            instance.transcribe.side_effect = UnsupportedLanguageError(
                "fr", SUPPORTED_LANGUAGES
            )
            with pytest.raises(UnsupportedLanguageError):
                transcribe_audio(_make_audio_bytes(), language="fr")

    def test_default_language_is_english(self):
        with patch("voice.audio.AudioTranscriber") as MockTranscriber:
            instance = MockTranscriber.return_value
            instance.transcribe.return_value = TranscriptionResult(
                text="ok", language="en"
            )
            transcribe_audio(_make_audio_bytes())
            call_kwargs = instance.transcribe.call_args.kwargs
            assert call_kwargs.get("language") == "en"

    def test_default_mime_type_is_webm(self):
        with patch("voice.audio.AudioTranscriber") as MockTranscriber:
            instance = MockTranscriber.return_value
            instance.transcribe.return_value = TranscriptionResult(
                text="ok", language="en"
            )
            transcribe_audio(_make_audio_bytes())
            call_kwargs = instance.transcribe.call_args.kwargs
            assert call_kwargs.get("mime_type") == "audio/webm"
