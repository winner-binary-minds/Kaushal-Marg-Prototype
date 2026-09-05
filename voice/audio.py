"""
Voice Audio Backend - Browser-Recorded Audio to Speech-to-Text

Architecture note (critical):
    The Kaushal Marg voice input pipeline uses **browser-side audio recording**
    via the Web MediaRecorder API. The browser captures microphone audio, encodes
    it as WebM/OGG (Opus codec), and passes the raw bytes to the Python backend
    through the Streamlit UI layer.

    This module does NOT:
    - Access the microphone directly (no PyAudio, no sounddevice)
    - Block on real-time audio streams
    - Perform VAD (voice activity detection) in Python
    - Require any audio package beyond what is already installed

    What it DOES:
    - Accept raw audio bytes from any source (browser, file, test fixture)
    - Wrap the bytes in the google-genai multimodal API format
      (``types.Part(inline_data=types.Blob(mime_type=..., data=bytes))``)
    - Send a transcription prompt to Gemini via the existing GeminiClient
    - Return clean, stripped transcribed text
    - Support English (en), Hindi (hi), and Marathi (mr) with language hints

    The UI integration step (browser MediaRecorder → bytes → this module) is
    a separate task for the Streamlit UI layer and is NOT part of this module.

Supported languages:
    - ``"en"`` — English
    - ``"hi"`` — Hindi
    - ``"mr"`` — Marathi

Supported audio MIME types (browser MediaRecorder defaults):
    - ``"audio/webm"``        — Chrome/Edge (Opus codec)
    - ``"audio/webm;codecs=opus"`` — Chrome explicit
    - ``"audio/ogg"``         — Firefox (Opus codec)
    - ``"audio/ogg;codecs=opus"`` — Firefox explicit
    - ``"audio/wav"``         — Safari / fallback
    - ``"audio/mp4"``         — Safari on iOS

Public API:
    - :class:`AudioProcessingError`   — raised when transcription fails
    - :class:`UnsupportedLanguageError` — raised for unknown language codes
    - :class:`UnsupportedMimeTypeError` — raised for unsupported audio formats
    - :class:`TranscriptionResult`    — immutable result dataclass
    - :class:`AudioTranscriber`       — main class; ``transcribe(bytes, lang, mime)``
    - :func:`transcribe_audio`        — module-level convenience wrapper

Does NOT:
    - Access microphone hardware
    - Import PyAudio, sounddevice, speech_recognition, gTTS
    - Import streamlit or any UI framework
    - Log raw audio bytes or beneficiary speech content
    - Require network access beyond what GeminiClient already uses
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Final, Optional

from google import genai
from google.genai import types

from ai.gemini import GeminiClient, GeminiAPIError, GeminiConfigError, GeminiQuotaError
from config import GEMINI_TRANSCRIPTION_MODEL

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Supported Kaushal Marg language codes (matches ConversationManager / TTS).
SUPPORTED_LANGUAGES: Final[frozenset[str]] = frozenset({"en", "hi", "mr"})

#: Human-readable language names for transcription prompts.
_LANGUAGE_NAMES: Final[dict[str, str]] = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

#: MIME types accepted from browser MediaRecorder / fallback sources.
#: Values are the canonical MIME string Gemini expects in types.Blob.
SUPPORTED_MIME_TYPES: Final[dict[str, str]] = {
    "audio/webm": "audio/webm",
    "audio/webm;codecs=opus": "audio/webm",
    "audio/ogg": "audio/ogg",
    "audio/ogg;codecs=opus": "audio/ogg",
    "audio/wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/mp4": "audio/mp4",
    "audio/mpeg": "audio/mpeg",
    "audio/mp3": "audio/mpeg",
}

#: Minimum audio payload size in bytes. Smaller blobs are silently empty.
_MIN_AUDIO_BYTES: Final[int] = 64

#: Transcription prompt template. Instructs Gemini to transcribe only,
#: using the specified language hint.
_TRANSCRIPTION_PROMPT: Final[str] = (
    "You are a speech transcription assistant. "
    "Transcribe the audio recording accurately. "
    "The speaker is using {language_name}. "
    "Output ONLY the transcribed text — no labels, no explanation, "
    "no punctuation corrections beyond what was spoken. "
    "If the audio is silent or unintelligible, output an empty string."
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AudioProcessingError(Exception):
    """
    Raised when audio transcription fails.

    This wraps :class:`~ai.gemini.GeminiAPIError` and other runtime errors
    so callers only need to catch one audio-specific exception type.

    Attributes:
        cause: The underlying exception that triggered this error, or None.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        self.cause = cause
        super().__init__(message)


class UnsupportedLanguageError(ValueError):
    """
    Raised when an unrecognised language code is passed to :class:`AudioTranscriber`.

    Attributes:
        language:  The invalid code supplied.
        supported: Tuple of valid language codes.
    """

    def __init__(self, language: str, supported: frozenset[str]) -> None:
        self.language = language
        self.supported = tuple(sorted(supported))
        super().__init__(
            f"Language code '{language}' is not supported. "
            f"Supported codes: {sorted(supported)}"
        )


class UnsupportedMimeTypeError(ValueError):
    """
    Raised when audio bytes are submitted with an unrecognised MIME type.

    Attributes:
        mime_type: The unrecognised MIME type supplied.
        supported: Tuple of accepted MIME types.
    """

    def __init__(self, mime_type: str, supported: dict[str, str]) -> None:
        self.mime_type = mime_type
        self.supported = tuple(sorted(supported.keys()))
        super().__init__(
            f"MIME type '{mime_type}' is not supported. "
            f"Accepted types: {sorted(supported.keys())}"
        )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TranscriptionResult:
    """
    Immutable result of a single transcription call.

    Attributes:
        text:     Transcribed text, stripped of leading/trailing whitespace.
                  Empty string if audio was silent or unintelligible.
        language: The language code used for the transcription hint.
        is_empty: ``True`` if no speech was detected (text is empty).
    """

    text: str
    language: str

    @property
    def is_empty(self) -> bool:
        """Return ``True`` if no speech content was detected."""
        return len(self.text) == 0

    def __str__(self) -> str:
        return self.text


# ---------------------------------------------------------------------------
# Core transcriber
# ---------------------------------------------------------------------------

class AudioTranscriber:
    """
    Transcribes browser-recorded audio bytes to text using Gemini multimodal.

    This class wraps the Gemini ``models.generate_content`` call with a
    ``types.Part(inline_data=types.Blob(mime_type=..., data=bytes))`` payload,
    which is the standard google-genai SDK approach for inline audio.

    The class is stateless with respect to audio state; each call to
    :meth:`transcribe` is independent.

    .. important::
        **UI integration boundary**: this class receives raw ``bytes`` that
        the browser has already captured and sent to the Python backend.
        It does NOT access the microphone. The Streamlit UI layer is
        responsible for collecting audio bytes from the browser and passing
        them here.

    Args:
        api_key:          Gemini API key. If ``None``, reads from
                          ``GEMINI_API_KEY`` environment variable.
        model:            Gemini model to use. Defaults to the GeminiClient
                          default (``gemini-2.5-flash``).
        max_output_tokens: Token limit for the transcription response.
                          Transcriptions are short; 256 is sufficient.

    Raises:
        :class:`~ai.gemini.GeminiConfigError`: If the API key is missing or
            the client cannot be initialised.
    """

    _DEFAULT_MAX_TOKENS: Final[int] = 1024

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = GEMINI_TRANSCRIPTION_MODEL,
        max_output_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        try:
            self._gemini = GeminiClient(
                api_key=api_key,
                model=model,
                max_output_tokens=max_output_tokens,
            )
            logger.debug("AudioTranscriber initialised: model=%s", model)
        except GeminiConfigError:
            raise
        except Exception as exc:
            raise GeminiConfigError(
                f"Failed to initialise AudioTranscriber: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
        mime_type: str = "audio/webm",
    ) -> TranscriptionResult:
        """
        Transcribe raw audio bytes to text.

        Wraps the audio in the Gemini multimodal inline_data format and sends
        a transcription prompt. Returns the stripped text or an empty-result
        object if the audio was silent/unintelligible.

        Args:
            audio_bytes: Raw audio bytes from the browser MediaRecorder
                         (or any other audio source). Must be non-empty bytes.
            language:    Language code hint — ``"en"``, ``"hi"``, or ``"mr"``.
                         Defaults to English.
            mime_type:   Audio MIME type as reported by the browser.
                         Defaults to ``"audio/webm"`` (Chrome default).

        Returns:
            :class:`TranscriptionResult` with ``.text`` and ``.is_empty``.

        Raises:
            :class:`UnsupportedLanguageError`: If *language* is not supported.
            :class:`UnsupportedMimeTypeError`: If *mime_type* is not in
                :data:`SUPPORTED_MIME_TYPES`.
            :class:`ValueError`: If *audio_bytes* is not bytes, is empty, or
                is below the minimum meaningful size.
            :class:`AudioProcessingError`: If the Gemini API call fails.

        Note:
            Raw audio bytes are never logged. Only byte-count metadata is
            logged at DEBUG level.
        """
        # Validate inputs
        language = self._validate_language(language)
        canonical_mime = self._validate_mime_type(mime_type)
        self._validate_audio_bytes(audio_bytes)

        logger.debug(
            "Transcribing audio: lang=%s, mime=%s, bytes=%d",
            language, canonical_mime, len(audio_bytes),
        )

        try:
            text = self._call_gemini(audio_bytes, canonical_mime, language)
            result = TranscriptionResult(text=text.strip(), language=language)
            logger.debug(
                "Transcription complete: lang=%s, chars=%d, empty=%s",
                language, len(result.text), result.is_empty,
            )
            return result

        except GeminiQuotaError:
            raise
        except GeminiAPIError:
            raise
        except AudioProcessingError:
            raise
        except Exception as exc:
            raise AudioProcessingError(
                f"Unexpected error during transcription: {exc}", cause=exc
            ) from exc

    def supported_languages(self) -> frozenset[str]:
        """
        Return the set of supported language codes.

        Returns:
            Frozenset of valid language code strings (``{'en', 'hi', 'mr'}``).
        """
        return SUPPORTED_LANGUAGES

    def supported_mime_types(self) -> tuple[str, ...]:
        """
        Return the accepted audio MIME types (as supplied by browser/caller).

        Returns:
            Tuple of accepted MIME type strings.
        """
        return tuple(sorted(SUPPORTED_MIME_TYPES.keys()))

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _validate_language(self, language: str) -> str:
        """Validate and return the normalised language code."""
        if not isinstance(language, str):
            raise UnsupportedLanguageError(str(language), SUPPORTED_LANGUAGES)
        normalised = language.strip()
        if normalised not in SUPPORTED_LANGUAGES:
            raise UnsupportedLanguageError(normalised, SUPPORTED_LANGUAGES)
        return normalised

    def _validate_mime_type(self, mime_type: str) -> str:
        """
        Validate MIME type and return the canonical form Gemini expects.

        Args:
            mime_type: Raw MIME type from the browser.

        Returns:
            Canonical MIME type string.

        Raises:
            UnsupportedMimeTypeError: If MIME type is not recognised.
        """
        if not isinstance(mime_type, str):
            raise UnsupportedMimeTypeError(str(mime_type), SUPPORTED_MIME_TYPES)
        normalised = mime_type.strip().lower()
        canonical = SUPPORTED_MIME_TYPES.get(normalised)
        if canonical is None:
            raise UnsupportedMimeTypeError(mime_type, SUPPORTED_MIME_TYPES)
        return canonical

    def _validate_audio_bytes(self, audio_bytes: bytes) -> None:
        """
        Validate that audio_bytes is a non-trivially-small bytes object.

        Raises:
            ValueError: If audio_bytes is not bytes, empty, or too small.
        """
        if not isinstance(audio_bytes, bytes):
            raise ValueError(
                f"audio_bytes must be bytes, got {type(audio_bytes).__name__}"
            )
        if len(audio_bytes) == 0:
            raise ValueError("audio_bytes must not be empty")
        if len(audio_bytes) < _MIN_AUDIO_BYTES:
            raise ValueError(
                f"audio_bytes is too small ({len(audio_bytes)} bytes < "
                f"{_MIN_AUDIO_BYTES} minimum). "
                "Provide a complete audio recording."
            )

    def _build_prompt(self, language: str) -> str:
        """Build the transcription instruction prompt for the given language."""
        return _TRANSCRIPTION_PROMPT.format(
            language_name=_LANGUAGE_NAMES[language]
        )

    @staticmethod
    def _extract_text_from_response(response: Any) -> str:
        """
        Safely and robustly extracts generated text from a Gemini response object.

        Handles:
        - Direct response.text attribute (if populated)
        - Candidates -> content -> parts -> text iteration
        - Logging of safe metadata (finish_reason, candidate count, etc.) when text is absent
        """
        if response is None:
            logger.debug("Gemini response is None")
            return ""

        # 1. Try direct .text attribute
        try:
            if hasattr(response, "text") and response.text is not None:
                text_val = str(response.text).strip()
                if text_val:
                    return text_val
        except Exception as err:
            logger.debug("Accessing response.text raised exception: %s", err)

        # 2. Inspect candidates and content parts
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            logger.debug("Gemini response has 0 candidates")
            return ""

        extracted_chunks: list[str] = []
        for i, cand in enumerate(candidates):
            finish_reason = getattr(cand, "finish_reason", "UNKNOWN")
            logger.debug("Candidate %d finish_reason: %s", i, finish_reason)
            content = getattr(cand, "content", None)
            if content:
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    part_text = getattr(p, "text", None)
                    if part_text:
                        extracted_chunks.append(part_text.strip())
                    
                    audio_transcription = getattr(p, "audio_transcription", None)
                    if audio_transcription:
                        at_text = getattr(audio_transcription, "text", None)
                        if at_text:
                            extracted_chunks.append(at_text.strip())

        if extracted_chunks:
            return " ".join(extracted_chunks).strip()

        logger.debug(
            "Gemini returned %d candidate(s) but no text parts were present.",
            len(candidates),
        )
        return ""

    def _call_gemini(
        self,
        audio_bytes: bytes,
        canonical_mime: str,
        language: str,
    ) -> str:
        """
        Call the Gemini multimodal API with the audio bytes.

        Constructs multimodal payload using ``types.Part.from_bytes`` and
        the language transcription instruction prompt.

        Args:
            audio_bytes:    Validated raw audio bytes.
            canonical_mime: Canonical MIME type for types.Blob.
            language:       Validated language code.

        Returns:
            Raw text from Gemini response (may be empty string).

        Raises:
            GeminiAPIError: If the API call fails or returns no content.
        """
        prompt_text = self._build_prompt(language)

        import tempfile
        import os
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                uploaded_file = self._gemini._client.files.upload(
                    file=tmp_path,
                    config={'mime_type': canonical_mime}
                )
                
                lang_map = {"en": "en-US", "hi": "hi-IN", "mr": "mr-IN"}
                audio_config = None
                if language in lang_map:
                    audio_config = types.AudioTranscriptionConfig(
                        language_codes=[lang_map[language]]
                    )
                    
                response = self._gemini._client.models.generate_content(
                    model=self._gemini.model,
                    contents=[uploaded_file, prompt_text],
                    config=types.GenerateContentConfig(
                        max_output_tokens=self._gemini.max_output_tokens,
                        audio_transcription_config=audio_config
                    ),
                )
                
                # Extract and strip text
                text = self._extract_text_from_response(response).strip()
                if text:
                    return text
                else:
                    raise AudioProcessingError("Gemini returned an empty transcription response.")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                import re
                delay_match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str)
                delay = int(float(delay_match.group(1))) if delay_match else 40
                raise GeminiQuotaError(f"Gemini API Quota Exceeded. {exc}", retry_delay=delay)
            elif "401" in err_str or "403" in err_str or "unauthenticated" in err_str:
                raise GeminiAPIError("API Authentication failed. Please check your GEMINI_API_KEY.")
            elif "404" in err_str or "not found" in err_str:
                raise GeminiAPIError(f"Model '{self._gemini.model}' not found. Please check GEMINI_TRANSCRIPTION_MODEL.")
            elif "503" in err_str or "500" in err_str or "unavailable" in err_str:
                raise GeminiAPIError("Gemini service is temporarily unavailable. Please try again later.")
            raise GeminiAPIError(
                f"Gemini audio transcription API call failed on {self._gemini.model}: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def transcribe_audio(
    audio_bytes: bytes,
    language: str = "en",
    mime_type: str = "audio/webm",
    api_key: Optional[str] = None,
) -> TranscriptionResult:
    """
    Module-level convenience wrapper around :class:`AudioTranscriber`.

    Creates a default :class:`AudioTranscriber` and calls
    :meth:`~AudioTranscriber.transcribe`. Use this for simple one-off calls;
    instantiate :class:`AudioTranscriber` directly when you want to reuse the
    engine across multiple calls.

    Args:
        audio_bytes: Raw audio bytes (e.g. from browser MediaRecorder).
        language:    Language code — ``"en"``, ``"hi"``, or ``"mr"``.
        mime_type:   Audio MIME type (browser-reported).
        api_key:     Gemini API key. If ``None``, reads from environment.

    Returns:
        :class:`TranscriptionResult` with transcribed text.

    Raises:
        :class:`UnsupportedLanguageError`: For unsupported language codes.
        :class:`UnsupportedMimeTypeError`: For unsupported MIME types.
        :class:`ValueError`: For invalid audio bytes.
        :class:`AudioProcessingError`: If transcription fails.
    """
    return AudioTranscriber(api_key=api_key).transcribe(
        audio_bytes, language=language, mime_type=mime_type
    )
