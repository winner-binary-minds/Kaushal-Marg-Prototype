"""
Tests for voice/tts.py

Covers:
- TTSEngine initialisation (valid / invalid volume)
- prepare_utterance() for English, Hindi, Marathi
- SpeechSynthesisConfig field correctness (lang, voice_hints, rate, pitch)
- SpeechSynthesisConfig.to_dict() output shape and key names
- Text cleaning (markdown removal, whitespace collapse, Unicode NFC)
- UnsupportedLanguageError raised for bad language codes
- ValueError raised for empty / whitespace-only / non-string text
- is_supported_language() helper
- supported_languages() returns correct set
- Module-level prepare_utterance() convenience function
- No real network calls, no audio output, no API keys required
"""

import pytest
import unicodedata

from voice.tts import (
    TTSEngine,
    SpeechSynthesisConfig,
    UnsupportedLanguageError,
    LANGUAGE_VOICE_MAP,
    prepare_utterance,
)


# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> TTSEngine:
    """Default TTSEngine (volume=1.0)."""
    return TTSEngine()


SAMPLE_TEXTS = {
    "en": "You are well-suited for a Solar Panel Technician role.",
    "hi": "आपके लिए सोलर पैनल तकनीशियन सबसे उपयुक्त है।",
    "mr": "तुमच्यासाठी सोलर पॅनल तंत्रज्ञ सर्वात योग्य आहे.",
}


# ---------------------------------------------------------------------------
# TestLanguageVoiceMap — validate the public constant
# ---------------------------------------------------------------------------

class TestLanguageVoiceMap:
    """Verify the LANGUAGE_VOICE_MAP structure is correct."""

    def test_map_has_three_entries(self):
        assert len(LANGUAGE_VOICE_MAP) == 3

    def test_all_required_codes_present(self):
        assert set(LANGUAGE_VOICE_MAP.keys()) == {"en", "hi", "mr"}

    def test_each_entry_has_lang_field(self):
        for code, cfg in LANGUAGE_VOICE_MAP.items():
            assert "lang" in cfg, f"Missing 'lang' key for '{code}'"

    def test_each_entry_has_voice_hints(self):
        for code, cfg in LANGUAGE_VOICE_MAP.items():
            assert "voice_hints" in cfg
            assert isinstance(cfg["voice_hints"], list)
            assert len(cfg["voice_hints"]) > 0

    def test_each_entry_has_rate_and_pitch(self):
        for code, cfg in LANGUAGE_VOICE_MAP.items():
            assert "rate" in cfg
            assert "pitch" in cfg

    def test_english_lang_tag_is_en_in(self):
        assert LANGUAGE_VOICE_MAP["en"]["lang"] == "en-IN"

    def test_hindi_lang_tag_is_hi_in(self):
        assert LANGUAGE_VOICE_MAP["hi"]["lang"] == "hi-IN"

    def test_marathi_lang_tag_is_mr_in(self):
        assert LANGUAGE_VOICE_MAP["mr"]["lang"] == "mr-IN"

    def test_hindi_rate_is_slower_than_english(self):
        """Hindi/Marathi should have rate <= English for clarity."""
        assert LANGUAGE_VOICE_MAP["hi"]["rate"] <= LANGUAGE_VOICE_MAP["en"]["rate"]

    def test_marathi_rate_is_slower_than_english(self):
        assert LANGUAGE_VOICE_MAP["mr"]["rate"] <= LANGUAGE_VOICE_MAP["en"]["rate"]


# ---------------------------------------------------------------------------
# TestTTSEngineInit
# ---------------------------------------------------------------------------

class TestTTSEngineInit:
    """Test TTSEngine initialisation."""

    def test_default_volume_is_1(self):
        eng = TTSEngine()
        assert eng._volume == 1.0

    def test_custom_volume_stored(self):
        eng = TTSEngine(volume=0.7)
        assert eng._volume == 0.7

    def test_volume_zero_allowed(self):
        eng = TTSEngine(volume=0.0)
        assert eng._volume == 0.0

    def test_volume_above_1_raises_value_error(self):
        with pytest.raises(ValueError):
            TTSEngine(volume=1.1)

    def test_volume_below_0_raises_value_error(self):
        with pytest.raises(ValueError):
            TTSEngine(volume=-0.1)


# ---------------------------------------------------------------------------
# TestSupportedLanguages
# ---------------------------------------------------------------------------

class TestSupportedLanguages:
    """Test language-support query methods."""

    def test_supported_languages_returns_frozenset(self, engine):
        result = engine.supported_languages()
        assert isinstance(result, frozenset)

    def test_supported_languages_contains_en_hi_mr(self, engine):
        assert engine.supported_languages() == frozenset({"en", "hi", "mr"})

    def test_is_supported_en(self, engine):
        assert engine.is_supported_language("en") is True

    def test_is_supported_hi(self, engine):
        assert engine.is_supported_language("hi") is True

    def test_is_supported_mr(self, engine):
        assert engine.is_supported_language("mr") is True

    def test_is_not_supported_fr(self, engine):
        assert engine.is_supported_language("fr") is False

    def test_is_not_supported_empty_string(self, engine):
        assert engine.is_supported_language("") is False

    def test_is_not_supported_none(self, engine):
        assert engine.is_supported_language(None) is False

    def test_is_not_supported_int(self, engine):
        assert engine.is_supported_language(42) is False


# ---------------------------------------------------------------------------
# TestPrepareUtteranceEnglish
# ---------------------------------------------------------------------------

class TestPrepareUtteranceEnglish:
    """Test prepare_utterance() for English."""

    def test_returns_speech_synthesis_config(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert isinstance(result, SpeechSynthesisConfig)

    def test_lang_is_en_in(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.lang == "en-IN"

    def test_text_is_preserved(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.text == SAMPLE_TEXTS["en"]

    def test_voice_hints_is_tuple(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert isinstance(result.voice_hints, tuple)
        assert len(result.voice_hints) > 0

    def test_rate_matches_map(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.rate == LANGUAGE_VOICE_MAP["en"]["rate"]

    def test_pitch_matches_map(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.pitch == LANGUAGE_VOICE_MAP["en"]["pitch"]

    def test_volume_matches_engine_default(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.volume == 1.0

    def test_custom_volume_reflected(self):
        eng = TTSEngine(volume=0.5)
        result = eng.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.volume == 0.5

    def test_default_language_is_english(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"])
        assert result.lang == "en-IN"

    def test_config_is_frozen(self, engine):
        """SpeechSynthesisConfig is immutable (frozen dataclass)."""
        result = engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")
        with pytest.raises((AttributeError, TypeError)):
            result.text = "modified"


# ---------------------------------------------------------------------------
# TestPrepareUtteranceHindi
# ---------------------------------------------------------------------------

class TestPrepareUtteranceHindi:
    """Test prepare_utterance() for Hindi."""

    def test_returns_config(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        assert isinstance(result, SpeechSynthesisConfig)

    def test_lang_is_hi_in(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        assert result.lang == "hi-IN"

    def test_hindi_text_preserved(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        assert result.text == SAMPLE_TEXTS["hi"]

    def test_rate_is_0_9(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        assert result.rate == 0.9

    def test_voice_hints_non_empty(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        assert len(result.voice_hints) > 0


# ---------------------------------------------------------------------------
# TestPrepareUtteranceMarathi
# ---------------------------------------------------------------------------

class TestPrepareUtteranceMarathi:
    """Test prepare_utterance() for Marathi."""

    def test_returns_config(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["mr"], "mr")
        assert isinstance(result, SpeechSynthesisConfig)

    def test_lang_is_mr_in(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["mr"], "mr")
        assert result.lang == "mr-IN"

    def test_marathi_text_preserved(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["mr"], "mr")
        assert result.text == SAMPLE_TEXTS["mr"]

    def test_rate_is_0_9(self, engine):
        result = engine.prepare_utterance(SAMPLE_TEXTS["mr"], "mr")
        assert result.rate == 0.9


# ---------------------------------------------------------------------------
# TestTextCleaning
# ---------------------------------------------------------------------------

class TestTextCleaning:
    """Test that _clean_text removes markdown and normalises whitespace."""

    def test_bold_markdown_stripped(self, engine):
        result = engine.prepare_utterance("**Solar Panel Technician**", "en")
        assert "**" not in result.text
        assert "Solar Panel Technician" in result.text

    def test_italic_markdown_stripped(self, engine):
        result = engine.prepare_utterance("*important role*", "en")
        assert "*" not in result.text
        assert "important role" in result.text

    def test_triple_backtick_stripped(self, engine):
        result = engine.prepare_utterance("```code block```", "en")
        assert "```" not in result.text

    def test_inline_code_stripped(self, engine):
        result = engine.prepare_utterance("`skill`", "en")
        assert "`" not in result.text

    def test_heading_hash_stripped(self, engine):
        result = engine.prepare_utterance("## Your Skills", "en")
        assert "#" not in result.text
        assert "Your Skills" in result.text

    def test_multiple_spaces_collapsed(self, engine):
        result = engine.prepare_utterance("hello   world", "en")
        assert "  " not in result.text
        assert "hello world" in result.text

    def test_newlines_collapsed_to_space(self, engine):
        result = engine.prepare_utterance("hello\nworld", "en")
        assert "\n" not in result.text
        assert "hello world" in result.text

    def test_mixed_newlines_collapsed(self, engine):
        result = engine.prepare_utterance("line1\r\nline2\nline3", "en")
        assert "\r" not in result.text
        assert "\n" not in result.text

    def test_leading_trailing_whitespace_stripped(self, engine):
        result = engine.prepare_utterance("  hello  ", "en")
        assert result.text == "hello"

    def test_devanagari_text_not_corrupted(self, engine):
        hindi_text = "आपके लिए यह अच्छा है।"
        result = engine.prepare_utterance(hindi_text, "hi")
        # Core content must survive cleaning
        assert "आपके" in result.text
        assert "अच्छा" in result.text

    def test_unicode_nfc_normalised(self, engine):
        """Devanagari in NFD form should be normalised to NFC."""
        # Create NFD text by decomposing
        nfc_text = "अच्छा"
        nfd_text = unicodedata.normalize("NFD", nfc_text)
        result = engine.prepare_utterance(nfd_text, "hi")
        assert unicodedata.is_normalized("NFC", result.text)

    def test_plain_text_unchanged(self, engine):
        plain = "You are good at solar work."
        result = engine.prepare_utterance(plain, "en")
        assert result.text == plain


# ---------------------------------------------------------------------------
# TestUnsupportedLanguageError
# ---------------------------------------------------------------------------

class TestUnsupportedLanguageError:
    """Test UnsupportedLanguageError is raised correctly."""

    def test_unsupported_language_code_raises(self, engine):
        with pytest.raises(UnsupportedLanguageError):
            engine.prepare_utterance("Hello", "fr")

    def test_error_message_contains_bad_code(self, engine):
        with pytest.raises(UnsupportedLanguageError) as exc:
            engine.prepare_utterance("Hello", "de")
        assert "de" in str(exc.value)

    def test_error_message_lists_supported_codes(self, engine):
        with pytest.raises(UnsupportedLanguageError) as exc:
            engine.prepare_utterance("Hello", "es")
        error_msg = str(exc.value)
        assert "en" in error_msg
        assert "hi" in error_msg
        assert "mr" in error_msg

    def test_empty_string_language_raises(self, engine):
        with pytest.raises(UnsupportedLanguageError):
            engine.prepare_utterance("Hello", "")

    def test_none_language_raises(self, engine):
        with pytest.raises(UnsupportedLanguageError):
            engine.prepare_utterance("Hello", None)

    def test_integer_language_raises(self, engine):
        with pytest.raises(UnsupportedLanguageError):
            engine.prepare_utterance("Hello", 1)

    def test_error_attributes(self):
        """UnsupportedLanguageError has .language and .supported attributes."""
        try:
            TTSEngine().prepare_utterance("Hello", "zz")
        except UnsupportedLanguageError as e:
            assert e.language == "zz"
            assert isinstance(e.supported, tuple)
            assert "en" in e.supported

    def test_unsupported_language_is_value_error_subclass(self):
        """UnsupportedLanguageError must be a ValueError subclass."""
        assert issubclass(UnsupportedLanguageError, ValueError)

    def test_is_supported_language_false_for_same_bad_code(self, engine):
        assert engine.is_supported_language("fr") is False


# ---------------------------------------------------------------------------
# TestInvalidText
# ---------------------------------------------------------------------------

class TestInvalidText:
    """Test ValueError is raised for invalid text inputs."""

    def test_empty_string_raises(self, engine):
        with pytest.raises(ValueError):
            engine.prepare_utterance("", "en")

    def test_whitespace_only_raises(self, engine):
        with pytest.raises(ValueError):
            engine.prepare_utterance("   ", "en")

    def test_newline_only_raises(self, engine):
        with pytest.raises(ValueError):
            engine.prepare_utterance("\n\n", "en")

    def test_markdown_only_raises(self, engine):
        """Text that is only markdown decorators becomes empty after cleaning."""
        with pytest.raises(ValueError):
            engine.prepare_utterance("**", "en")

    def test_none_text_raises(self, engine):
        with pytest.raises(ValueError):
            engine.prepare_utterance(None, "en")

    def test_integer_text_raises(self, engine):
        with pytest.raises(ValueError):
            engine.prepare_utterance(42, "en")

    def test_list_text_raises(self, engine):
        with pytest.raises(ValueError):
            engine.prepare_utterance(["hello"], "en")


# ---------------------------------------------------------------------------
# TestSpeechSynthesisConfigToDict
# ---------------------------------------------------------------------------

class TestSpeechSynthesisConfigToDict:
    """Test SpeechSynthesisConfig.to_dict() output."""

    @pytest.fixture
    def config(self, engine) -> SpeechSynthesisConfig:
        return engine.prepare_utterance(SAMPLE_TEXTS["en"], "en")

    def test_to_dict_returns_dict(self, config):
        assert isinstance(config.to_dict(), dict)

    def test_to_dict_has_text_key(self, config):
        assert "text" in config.to_dict()

    def test_to_dict_has_lang_key(self, config):
        assert "lang" in config.to_dict()

    def test_to_dict_has_voice_hints_key(self, config):
        """Key uses camelCase for JS consumption."""
        assert "voiceHints" in config.to_dict()

    def test_to_dict_has_rate_key(self, config):
        assert "rate" in config.to_dict()

    def test_to_dict_has_pitch_key(self, config):
        assert "pitch" in config.to_dict()

    def test_to_dict_has_volume_key(self, config):
        assert "volume" in config.to_dict()

    def test_to_dict_voice_hints_is_list(self, config):
        """voiceHints must be a list (JSON array), not a tuple."""
        assert isinstance(config.to_dict()["voiceHints"], list)

    def test_to_dict_text_matches_config(self, config):
        assert config.to_dict()["text"] == config.text

    def test_to_dict_lang_matches_config(self, config):
        assert config.to_dict()["lang"] == config.lang

    def test_to_dict_for_hindi(self, engine):
        config = engine.prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        d = config.to_dict()
        assert d["lang"] == "hi-IN"
        assert d["rate"] == 0.9

    def test_to_dict_for_marathi(self, engine):
        config = engine.prepare_utterance(SAMPLE_TEXTS["mr"], "mr")
        d = config.to_dict()
        assert d["lang"] == "mr-IN"


# ---------------------------------------------------------------------------
# TestModuleLevelPrepareUtterance
# ---------------------------------------------------------------------------

class TestModuleLevelPrepareUtterance:
    """Test the module-level prepare_utterance() convenience function."""

    def test_returns_config(self):
        result = prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert isinstance(result, SpeechSynthesisConfig)

    def test_english_lang_tag(self):
        result = prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.lang == "en-IN"

    def test_hindi_lang_tag(self):
        result = prepare_utterance(SAMPLE_TEXTS["hi"], "hi")
        assert result.lang == "hi-IN"

    def test_marathi_lang_tag(self):
        result = prepare_utterance(SAMPLE_TEXTS["mr"], "mr")
        assert result.lang == "mr-IN"

    def test_default_language_is_english(self):
        result = prepare_utterance(SAMPLE_TEXTS["en"])
        assert result.lang == "en-IN"

    def test_unsupported_language_raises(self):
        with pytest.raises(UnsupportedLanguageError):
            prepare_utterance("Hello", "ja")

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            prepare_utterance("", "en")

    def test_volume_is_1_by_default(self):
        result = prepare_utterance(SAMPLE_TEXTS["en"], "en")
        assert result.volume == 1.0
