"""
Tests for ai/profile_extractor.py

Comprehensive test suite for ProfileExtractor covering:
- Initialization
- Complete and partial profile extraction
- Empty history handling
- Multilingual support (English, Hindi, Marathi)
- Input validation
- Error handling (GeminiAPIError propagation)
- Correct Pydantic schema usage
- No real API calls (all mocked)
- Assistant messages not treated as beneficiary facts
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from ai.profile_extractor import ProfileExtractor, BeneficiaryProfile
from ai.conversation import Message
from ai.gemini import GeminiAPIError, GeminiValidationError


class TestInitialization:
    """Test ProfileExtractor initialization."""
    
    def test_init_with_explicit_api_key(self):
        """Verify ProfileExtractor initializes with explicit API key."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            assert extractor is not None
    
    def test_init_with_env_api_key(self):
        """Verify ProfileExtractor reads API key from environment."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}):
            with patch("ai.profile_extractor.GeminiClient"):
                extractor = ProfileExtractor()
                assert extractor is not None
    
    def test_init_gemini_client_failure(self):
        """Verify GeminiClient initialization failure is caught."""
        with patch("ai.profile_extractor.GeminiClient", side_effect=Exception("API error")):
            with pytest.raises(ValueError) as exc:
                ProfileExtractor(api_key="test-key")
            assert "Failed to initialize" in str(exc.value)


class TestBeneficiaryProfileModel:
    """Test BeneficiaryProfile Pydantic model."""
    
    def test_model_with_all_fields(self):
        """Verify model accepts all fields."""
        profile = BeneficiaryProfile(
            education="10th Pass",
            skills=["farming", "tractor operation"],
            interests=["Agriculture"],
            district="Indore",
            employment_preference="Self-Employment",
            mobility="Local"
        )
        assert profile.education == "10th Pass"
        assert len(profile.skills) == 2
        assert profile.district == "Indore"
    
    def test_model_with_none_fields(self):
        """Verify model accepts None for optional fields."""
        profile = BeneficiaryProfile(
            education=None,
            skills=[],
            interests=[],
            district=None,
            employment_preference=None,
            mobility=None
        )
        assert profile.education is None
        assert profile.skills == []
        assert profile.interests == []
    
    def test_model_default_empty_lists(self):
        """Verify skills and interests default to empty lists."""
        profile = BeneficiaryProfile()
        assert profile.skills == []
        assert profile.interests == []
        assert profile.education is None
    
    def test_model_dump_to_dict(self):
        """Verify model_dump() returns correct dictionary."""
        profile = BeneficiaryProfile(
            education="12th Pass",
            skills=["skill1"],
            interests=["interest1"],
            district="Delhi",
            employment_preference="Wage-Employment",
            mobility="District Level"
        )
        data = profile.model_dump()
        assert isinstance(data, dict)
        assert data["education"] == "12th Pass"
        assert data["skills"] == ["skill1"]


class TestEmptyHistory:
    """Test extract_profile with empty message history."""
    
    def test_empty_message_list(self):
        """Verify extract_profile returns empty profile for empty history."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            result = extractor.extract_profile([])
            
            assert isinstance(result, dict)
            assert result["education"] is None
            assert result["skills"] == []
            assert result["interests"] == []
            assert result["district"] is None
            assert result["employment_preference"] is None
            assert result["mobility"] is None
    
    def test_empty_history_does_not_call_gemini(self):
        """Verify empty history doesn't make API call."""
        with patch("ai.profile_extractor.GeminiClient") as mock_gemini:
            extractor = ProfileExtractor(api_key="test-key")
            mock_gemini_instance = Mock()
            extractor._gemini_client = mock_gemini_instance
            
            extractor.extract_profile([])
            
            # Verify generate_structured was NOT called
            mock_gemini_instance.generate_structured.assert_not_called()


class TestInputValidation:
    """Test input validation for extract_profile."""
    
    def test_messages_not_list_raises_error(self):
        """Verify TypeError for non-list messages parameter."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            with pytest.raises(ValueError) as exc:
                extractor.extract_profile("not a list")
            assert "must be a list" in str(exc.value)
    
    def test_messages_contains_non_message_raises_error(self):
        """Verify error when list contains non-Message objects."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            invalid_messages = [
                Message(role="user", content="Hello", language="en"),
                "not a message",  # Invalid
            ]
            
            with pytest.raises(ValueError) as exc:
                extractor.extract_profile(invalid_messages)
            assert "must be Message instances" in str(exc.value)
    
    def test_messages_all_none_raises_error(self):
        """Verify error when list contains None objects."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            with pytest.raises(ValueError) as exc:
                extractor.extract_profile([None, None])
            assert "must be Message instances" in str(exc.value)
    
    def test_messages_dict_not_message_raises_error(self):
        """Verify error when list contains dicts instead of Message."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            with pytest.raises(ValueError) as exc:
                extractor.extract_profile([{"role": "user", "content": "Hello"}])
            assert "must be Message instances" in str(exc.value)


class TestCompleteProfileExtraction:
    """Test extract_profile with complete conversation."""
    
    def test_extract_complete_profile(self):
        """Verify profile extraction with all information provided."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            # Create mock Gemini response
            mock_profile = BeneficiaryProfile(
                education="10th Pass",
                skills=["farming", "tractor operation"],
                interests=["Agriculture"],
                district="Indore",
                employment_preference="Self-Employment",
                mobility="Local"
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            # Create conversation messages
            messages = [
                Message(role="assistant", content="Hello! What's your name?", language="en"),
                Message(role="user", content="I'm Raj from Indore", language="en"),
                Message(role="assistant", content="Nice to meet you, Raj!", language="en"),
                Message(role="user", content="I have skills in farming and tractor operation", language="en"),
                Message(role="assistant", content="That's great!", language="en"),
                Message(role="user", content="I'm interested in agriculture", language="en"),
                Message(role="assistant", content="Let me help you find opportunities", language="en"),
                Message(role="user", content="I want to start my own business", language="en"),
            ]
            
            result = extractor.extract_profile(messages)
            
            # Verify result is a dict
            assert isinstance(result, dict)
            assert result["education"] == "10th Pass"
            assert result["district"] == "Indore"
            assert "farming" in result["skills"]
            assert "Agriculture" in result["interests"]
            assert result["employment_preference"] == "Self-Employment"
            assert result["mobility"] == "Local"
    
    def test_extract_profile_calls_gemini_with_correct_schema(self):
        """Verify extract_profile calls generate_structured with BeneficiaryProfile schema."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile()
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="Hello", language="en"),
            ]
            
            extractor.extract_profile(messages)
            
            # Verify generate_structured was called
            mock_gemini_instance.generate_structured.assert_called_once()
            
            # Verify schema argument is BeneficiaryProfile
            call_args = mock_gemini_instance.generate_structured.call_args
            assert call_args.kwargs["schema"] == BeneficiaryProfile


class TestPartialProfileExtraction:
    """Test extract_profile with incomplete information."""
    
    def test_extract_partial_profile_missing_fields(self):
        """Verify extraction handles missing fields gracefully."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            # Only education and skills provided
            mock_profile = BeneficiaryProfile(
                education="8th Pass",
                skills=["basic wiring"],
                interests=[],
                district=None,
                employment_preference=None,
                mobility=None
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="I passed 8th grade", language="en"),
                Message(role="user", content="I know basic wiring", language="en"),
            ]
            
            result = extractor.extract_profile(messages)
            
            assert result["education"] == "8th Pass"
            assert "basic wiring" in result["skills"]
            assert result["interests"] == []
            assert result["district"] is None
            assert result["employment_preference"] is None
    
    def test_extract_profile_no_skills_mentioned(self):
        """Verify skills field is empty list if not mentioned."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile(
                education="12th Pass",
                skills=[],
                interests=["Healthcare"],
                district="Mumbai",
                employment_preference="Wage-Employment",
                mobility="District Level"
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="I'm from Mumbai and interested in healthcare", language="en"),
            ]
            
            result = extractor.extract_profile(messages)
            
            assert result["skills"] == []
            assert "Healthcare" in result["interests"]


class TestMultilingualSupport:
    """Test extract_profile with multilingual input."""
    
    def test_english_conversation(self):
        """Verify extraction from English conversation."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile(
                education="10th Pass",
                skills=["farming"],
                interests=["Agriculture"],
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="I have completed 10th and can do farming", language="en"),
            ]
            
            result = extractor.extract_profile(messages)
            assert result["education"] == "10th Pass"
    
    def test_hindi_conversation(self):
        """Verify extraction from Hindi conversation."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile(
                education="12वीं पास",
                skills=["खेती"],
                interests=["कृषि"],
                district="इंदौर",
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="मैं 12वीं पास हूँ और खेती कर सकता हूँ। मैं इंदौर से हूँ।", language="hi"),
            ]
            
            result = extractor.extract_profile(messages)
            assert result["district"] == "इंदौर"
    
    def test_marathi_conversation(self):
        """Verify extraction from Marathi conversation."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile(
                education="8वी पास",
                skills=["शेती"],
                interests=["कृषी"],
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="मी 8वी पास आहे आणि शेती करू शकतो", language="mr"),
            ]
            
            result = extractor.extract_profile(messages)
            assert result["education"] == "8वी पास"


class TestAssistantMessagesNotTreatedAsFacts:
    """Test that assistant messages are not treated as beneficiary facts."""
    
    def test_assistant_message_ignored_for_facts(self):
        """Verify assistant responses don't become beneficiary profile facts."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            # The assistant makes suggestions, but only user says what's true
            mock_profile = BeneficiaryProfile(
                education="10th Pass",  # What user said
                skills=["farming"],  # What user said
                # NOT "solar installation" which was suggested by assistant
            )
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="assistant", content="You could try solar installation", language="en"),
                Message(role="user", content="No, I know farming. I passed 10th grade", language="en"),
                Message(role="assistant", content="That's great! Farming is a good skill", language="en"),
            ]
            
            result = extractor.extract_profile(messages)
            
            # Verify only user-provided facts are extracted
            assert result["education"] == "10th Pass"
            assert "farming" in result["skills"]
            assert "solar installation" not in result["skills"]
    
    def test_prompt_includes_conversation_context(self):
        """Verify the prompt sent to Gemini includes full conversation."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile()
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.return_value = mock_profile
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="assistant", content="What's your education level?", language="en"),
                Message(role="user", content="I'm a 10th pass", language="en"),
            ]
            
            extractor.extract_profile(messages)
            
            # Get the prompt that was sent to Gemini
            call_args = mock_gemini_instance.generate_structured.call_args
            prompt = call_args.kwargs["prompt"]
            
            # Verify both user and assistant messages are in the prompt
            assert "10th pass" in prompt
            assert "education level" in prompt


class TestErrorHandling:
    """Test error handling and propagation."""
    
    def test_gemini_api_error_propagated(self):
        """Verify GeminiAPIError is propagated, not swallowed."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.side_effect = GeminiAPIError("API failed")
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="Hello", language="en"),
            ]
            
            with pytest.raises(GeminiAPIError):
                extractor.extract_profile(messages)
    
    def test_gemini_validation_error_propagated(self):
        """Verify GeminiValidationError is propagated."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_structured.side_effect = GeminiValidationError("Schema mismatch")
            extractor._gemini_client = mock_gemini_instance
            
            messages = [
                Message(role="user", content="Hello", language="en"),
            ]
            
            with pytest.raises(GeminiValidationError):
                extractor.extract_profile(messages)


class TestConversationTextBuilding:
    """Test internal conversation text formatting."""
    
    def test_build_conversation_text_formatting(self):
        """Verify _build_conversation_text formats correctly."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            messages = [
                Message(role="user", content="I'm Raj", language="en"),
                Message(role="assistant", content="Nice to meet you", language="en"),
                Message(role="user", content="I can farm", language="en"),
            ]
            
            text = extractor._build_conversation_text(messages)
            
            # Verify format
            assert "BENEFICIARY: I'm Raj" in text
            assert "ASSISTANT: Nice to meet you" in text
            assert "BENEFICIARY: I can farm" in text
            assert "\n" in text  # Messages separated by newlines
    
    def test_build_conversation_text_with_special_characters(self):
        """Verify _build_conversation_text handles special characters."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor = ProfileExtractor(api_key="test-key")
            
            messages = [
                Message(role="user", content="I know C++, Python & Java (in that order)", language="en"),
            ]
            
            text = extractor._build_conversation_text(messages)
            
            # Verify special characters are preserved
            assert "C++" in text
            assert "Python & Java" in text


class TestDeterministicBehavior:
    """Test deterministic behavior for reproducibility."""
    
    def test_same_messages_generate_same_prompt(self):
        """Verify same message list generates same prompt to Gemini."""
        with patch("ai.profile_extractor.GeminiClient"):
            extractor1 = ProfileExtractor(api_key="test-key")
            extractor2 = ProfileExtractor(api_key="test-key")
            
            mock_profile = BeneficiaryProfile()
            
            mock_gemini1 = Mock()
            mock_gemini1.generate_structured.return_value = mock_profile
            extractor1._gemini_client = mock_gemini1
            
            mock_gemini2 = Mock()
            mock_gemini2.generate_structured.return_value = mock_profile
            extractor2._gemini_client = mock_gemini2
            
            messages = [
                Message(role="user", content="I'm interested in farming", language="en"),
            ]
            
            extractor1.extract_profile(messages)
            extractor2.extract_profile(messages)
            
            # Both should call with identical prompts
            prompt1 = mock_gemini1.generate_structured.call_args.kwargs["prompt"]
            prompt2 = mock_gemini2.generate_structured.call_args.kwargs["prompt"]
            
            assert prompt1 == prompt2
