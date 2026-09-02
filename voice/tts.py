"""
Voice TTS Backend - Browser SpeechSynthesis Configuration Layer

Architecture note (important):
    The primary speech output for Kaushal Marg is the **browser's built-in
    Web Speech API** (SpeechSynthesis), which runs entirely client-side in
    JavaScript. This Python module does NOT play audio, synthesise audio bytes,
    or call any cloud TTS service.

    Its single responsibility is to produce a :class:`SpeechSynthesisConfig`
    — a small, serialisable dataclass — that the UI layer (Streamlit via
    ``st.components.v1.html`` or ``components.html``) passes to the browser's
    ``window.speechSynthesis.speak()`` API.

    If Google Cloud TTS is added in future as a server-side fallback, a new
    class (e.g. ``GCPTTSBackend``) should be added here without changing the
    existing public interface.

Supported languages:
    - ``"en"`` — English (India variant, en-IN)
    - ``"hi"`` — Hindi (hi-IN)
    - ``"mr"`` — Marathi (mr-IN)

Public API:
    - :class:`SpeechSynthesisConfig` — configuration object for the browser
    - :class:`UnsupportedLanguageError` — raised for unknown language codes
    - :class:`TTSEngine` — prepares utterance configs; stateless, thread-safe
    - :data:`LANGUAGE_VOICE_MAP` — public mapping of language codes to config
    - :func:`prepare_utterance` — module-level convenience wrapper

Does NOT:
    - Produce audio bytes or .mp3/.wav files
    - Call gTTS, pyttsx3, or any external TTS service
    - Import streamlit or any UI framework
    - Log conversation text or beneficiary data
    - Require network access
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Final

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Mapping from Kaushal Marg language codes to BCP-47 locale tags used by the
#: Web Speech API, plus ordered voice name hints.
#:
#: Voice name hints are passed to the browser as a preference list so that
#: ``SpeechSynthesisUtterance.voice`` can be resolved on the client.  The
#: browser will fall back to any available voice for the locale if none of the
#: named voices are installed.
#:
#: Structure per entry:
#:   ``lang``       — BCP-47 language tag for ``SpeechSynthesisUtterance.lang``
#:   ``voice_hints``— Ordered list of preferred ``SpeechSynthesisVoice.name``
#:                   substrings (case-insensitive prefix match on the client)
#:   ``rate``       — Default speech rate (1.0 = normal; 0.9 recommended for
#:                   Hindi/Marathi for clarity)
#:   ``pitch``      — Default pitch (1.0 = normal)
LANGUAGE_VOICE_MAP: Final[dict[str, dict]] = {
    "en": {
        "lang": "en-IN",
        "voice_hints": ["Google हिन्दी", "Google UK English Female", "en-IN"],
        "rate": 1.0,
        "pitch": 1.0,
    },
    "hi": {
        "lang": "hi-IN",
        "voice_hints": ["Google हिन्दी", "hi-IN", "Hindi India"],
        "rate": 0.9,
        "pitch": 1.0,
    },
    "mr": {
        "lang": "mr-IN",
        "voice_hints": ["Google मराठी", "mr-IN", "Marathi India"],
        "rate": 0.9,
        "pitch": 1.0,
    },
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class UnsupportedLanguageError(ValueError):
    """
    Raised when an unrecognised language code is requested.

    Attributes:
        language: The invalid language code that was supplied.
        supported: Tuple of valid language codes.
    """

    def __init__(self, language: str, supported: tuple[str, ...]) -> None:
        self.language = language
        self.supported = supported
        super().__init__(
            f"Language code '{language}' is not supported. "
            f"Supported codes: {sorted(supported)}"
        )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpeechSynthesisConfig:
    """
    Immutable configuration for a single browser SpeechSynthesis utterance.

    All fields are safe to serialise to JSON and pass directly to the browser
    via ``st.components.v1.html`` or ``components.html``.  No audio data or
    API keys are stored in this object.

    Attributes:
        text:        Cleaned, speech-ready text to be spoken.
        lang:        BCP-47 language tag (e.g. ``"hi-IN"``).
        voice_hints: Ordered list of preferred voice name substrings.
                     The browser picks the first voice whose name contains
                     any of these strings (case-insensitive).
        rate:        Speech rate multiplier (0.1 – 10.0; 1.0 = normal).
        pitch:       Pitch multiplier (0.0 – 2.0; 1.0 = normal).
        volume:      Volume (0.0 – 1.0; 1.0 = full).
    """

    text: str
    lang: str
    voice_hints: tuple[str, ...] = field(default_factory=tuple)
    rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0

    def to_dict(self) -> dict:
        """
        Return a JSON-serialisable dict for passing to browser JavaScript.

        Example usage in Streamlit::

            config = engine.prepare_utterance("Hello", "en")
            js_payload = config.to_dict()
            # pass js_payload to st.components.v1.html(...)
        """
        return {
            "text": self.text,
            "lang": self.lang,
            "voiceHints": list(self.voice_hints),
            "rate": self.rate,
            "pitch": self.pitch,
            "volume": self.volume,
        }


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class TTSEngine:
    """
    Stateless engine that prepares :class:`SpeechSynthesisConfig` objects.

    This class contains no mutable state and is safe to use concurrently.
    It performs no network calls and requires no API keys.

    Primary use-case: called by the Streamlit UI after receiving an AI
    response, to build the config object that is passed to the browser.

    Example::

        engine = TTSEngine()
        config = engine.prepare_utterance(
            "आपके लिए सोलर पैनल तकनीशियन सबसे उपयुक्त है।",
            language="hi",
        )
        # config.to_dict() is ready to serialise and send to browser JS

    Args:
        volume: Default volume for all utterances (0.0 – 1.0).
    """

    _SUPPORTED_LANGUAGES: Final[frozenset[str]] = frozenset(LANGUAGE_VOICE_MAP)

    # Characters/patterns that degrade TTS quality when left in text
    _MARKDOWN_PATTERN: Final = re.compile(
        r"(\*{1,3}|_{1,3}|`{1,3}|#{1,6}\s?|>\s?|\[|\]|\(|\)|~~)"
    )
    # Collapse runs of whitespace (including newlines) to a single space
    _WHITESPACE_PATTERN: Final = re.compile(r"\s+")

    def __init__(self, volume: float = 1.0) -> None:
        if not (0.0 <= volume <= 1.0):
            raise ValueError(f"volume must be between 0.0 and 1.0, got {volume}")
        self._volume = volume

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def prepare_utterance(
        self,
        text: str,
        language: str = "en",
    ) -> SpeechSynthesisConfig:
        """
        Prepare a :class:`SpeechSynthesisConfig` for the given text and language.

        Cleans the text for speech (strips markdown, collapses whitespace,
        normalises Unicode) and assembles the BCP-47 locale, voice hints,
        rate, and pitch from :data:`LANGUAGE_VOICE_MAP`.

        Args:
            text:     The text to be spoken (e.g. an AI assistant response).
                      Must be a non-empty string after cleaning.
            language: Kaushal Marg language code — ``"en"``, ``"hi"``, or
                      ``"mr"``. Defaults to English.

        Returns:
            A frozen :class:`SpeechSynthesisConfig` ready to pass to the
            browser or serialise via :meth:`SpeechSynthesisConfig.to_dict`.

        Raises:
            :class:`UnsupportedLanguageError`: If *language* is not in
                :data:`LANGUAGE_VOICE_MAP`.
            :class:`ValueError`: If *text* is empty, not a string, or reduces
                to empty after cleaning.

        Note:
            The method never logs *text* content to protect beneficiary privacy.
        """
        # Validate language
        language = self._validate_language(language)

        # Validate and clean text
        cleaned = self._clean_text(text)

        # Fetch voice config for this language
        voice_cfg = LANGUAGE_VOICE_MAP[language]

        config = SpeechSynthesisConfig(
            text=cleaned,
            lang=voice_cfg["lang"],
            voice_hints=tuple(voice_cfg["voice_hints"]),
            rate=voice_cfg["rate"],
            pitch=voice_cfg["pitch"],
            volume=self._volume,
        )

        logger.debug(
            "Utterance prepared: lang=%s, chars=%d", language, len(cleaned)
        )
        return config

    def supported_languages(self) -> frozenset[str]:
        """
        Return the set of supported Kaushal Marg language codes.

        Returns:
            Frozenset of valid language code strings (``{'en', 'hi', 'mr'}``).
        """
        return self._SUPPORTED_LANGUAGES

    def is_supported_language(self, language: str) -> bool:
        """
        Return ``True`` if *language* is a supported language code.

        Args:
            language: Language code to check.

        Returns:
            ``True`` if supported, ``False`` otherwise.
        """
        return isinstance(language, str) and language.strip() in self._SUPPORTED_LANGUAGES

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _validate_language(self, language: str) -> str:
        """
        Validate language code and return the normalised value.

        Args:
            language: Raw language code.

        Returns:
            Stripped, lower-cased language code.

        Raises:
            :class:`UnsupportedLanguageError`: If not in LANGUAGE_VOICE_MAP.
        """
        if not isinstance(language, str):
            raise UnsupportedLanguageError(
                str(language), tuple(self._SUPPORTED_LANGUAGES)
            )
        normalised = language.strip()
        if normalised not in self._SUPPORTED_LANGUAGES:
            raise UnsupportedLanguageError(
                normalised, tuple(self._SUPPORTED_LANGUAGES)
            )
        return normalised

    def _clean_text(self, text: str) -> str:
        """
        Clean *text* for speech synthesis.

        Performs:
        1. Type check — must be a string.
        2. Unicode NFC normalisation (important for Devanagari).
        3. Markdown syntax removal (bold, italic, code, headers, links).
        4. Whitespace collapsing.
        5. Strip leading/trailing whitespace.

        Args:
            text: Raw text (may contain markdown).

        Returns:
            Cleaned string ready for browser SpeechSynthesis.

        Raises:
            :class:`ValueError`: If *text* is not a string or empty after
                cleaning.

        Note:
            Text content is never logged to protect beneficiary privacy.
        """
        if not isinstance(text, str):
            raise ValueError(
                f"text must be a string, got {type(text).__name__}"
            )

        # NFC normalise — ensures correct Devanagari glyph composition
        normalised = unicodedata.normalize("NFC", text)

        # Remove common Markdown decorators that TTS would read as symbols
        cleaned = self._MARKDOWN_PATTERN.sub(" ", normalised)

        # Collapse whitespace
        cleaned = self._WHITESPACE_PATTERN.sub(" ", cleaned).strip()

        if not cleaned:
            raise ValueError(
                "text is empty or contains only whitespace/markdown. "
                "Provide non-empty speech content."
            )

        return cleaned


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def prepare_utterance(text: str, language: str = "en") -> SpeechSynthesisConfig:
    """
    Module-level convenience wrapper around :class:`TTSEngine`.

    Creates a default :class:`TTSEngine` (volume=1.0) and calls
    :meth:`TTSEngine.prepare_utterance`.  Use this for simple one-off calls;
    instantiate :class:`TTSEngine` directly when you need custom volume or
    want to reuse the engine across multiple calls.

    Args:
        text:     Text to be spoken.
        language: Language code — ``"en"``, ``"hi"``, or ``"mr"``.

    Returns:
        :class:`SpeechSynthesisConfig` ready to pass to the browser.

    Raises:
        :class:`UnsupportedLanguageError`: If language code is not supported.
        :class:`ValueError`: If text is empty or invalid.
    """
    return TTSEngine().prepare_utterance(text, language)
