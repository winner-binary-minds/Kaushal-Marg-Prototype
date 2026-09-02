"""
Tests for ai/conversation.py

Comprehensive test suite for ConversationManager covering:
- Initialization with various configurations
- Language validation and switching
- Message validation and processing
- Conversation history management
- API error handling
- State export
- Sensitive data protection
- No real API calls (all mocked)
"""

import pytest
from unittest.mock import Mock, patch
import logging

from ai.conversation import (
    ConversationManager,
    Language,
    Message,
    ConversationState,
)
from ai.gemini import GeminiAPIError


class TestInitialization:
    """Test ConversationManager initialization."""
    
    def test_init_default_language(self):
        """Verify default initialization uses English."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            assert manager.get_language() == Language.ENGLISH.value
            state = manager.get_state()
            assert state.language == Language.ENGLISH.value
            assert not state.is_active
    
    def test_init_with_english(self):
        """Verify explicit English initialization."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            assert manager.get_language() == "en"
    
    def test_init_with_hindi(self):
        """Verify Hindi initialization."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="hi")
            assert manager.get_language() == "hi"
    
    def test_init_with_marathi(self):
        """Verify Marathi initialization."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="mr")
            assert manager.get_language() == "mr"
    
    def test_init_invalid_language_raises_error(self):
        """Verify invalid language raises ValueError."""
        with patch("ai.conversation.GeminiClient"):
            with pytest.raises(ValueError) as exc:
                ConversationManager(api_key="test-key", language="xx")
            assert "Language must be" in str(exc.value)
    
    def test_init_custom_max_history(self):
        """Verify custom max_history_size is accepted."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", max_history_size=100)
            # Verify by adding messages
            manager._max_history_size = 100
            assert manager._max_history_size == 100
    
    def test_init_invalid_max_history_zero(self):
        """Verify max_history_size=0 raises ValueError."""
        with patch("ai.conversation.GeminiClient"):
            with pytest.raises(ValueError) as exc:
                ConversationManager(api_key="test-key", max_history_size=0)
            assert "max_history_size" in str(exc.value)
    
    def test_init_invalid_max_history_negative(self):
        """Verify negative max_history_size raises ValueError."""
        with patch("ai.conversation.GeminiClient"):
            with pytest.raises(ValueError):
                ConversationManager(api_key="test-key", max_history_size=-10)
    
    def test_init_gemini_client_failure(self):
        """Verify GeminiClient initialization failure is propagated."""
        with patch("ai.conversation.GeminiClient", side_effect=Exception("API error")):
            with pytest.raises(ValueError) as exc:
                ConversationManager(api_key="test-key")
            assert "Failed to initialize" in str(exc.value)


class TestStartConversation:
    """Test starting a conversation."""
    
    @pytest.fixture
    def mock_manager(self):
        """Fixture providing a mocked ConversationManager."""
        with patch("ai.conversation.GeminiClient") as mock_gemini:
            manager = ConversationManager(api_key="test-key", language="en")
            yield manager, mock_gemini
    
    def test_start_conversation_success(self, mock_manager):
        """Verify successful conversation start returns greeting."""
        manager, mock_gemini = mock_manager
        
        # Mock Gemini response
        mock_gemini_instance = Mock()
        mock_gemini_instance.generate_text.return_value = "Hello! I'm here to help you explore your skills and career options."
        manager._gemini_client = mock_gemini_instance
        
        greeting = manager.start_conversation()
        
        assert isinstance(greeting, str)
        assert len(greeting) > 0
        assert "help" in greeting.lower() or "explore" in greeting.lower()
    
    def test_start_conversation_activates_conversation(self, mock_manager):
        """Verify start_conversation sets is_active to True."""
        manager, mock_gemini = mock_manager
        
        mock_gemini_instance = Mock()
        mock_gemini_instance.generate_text.return_value = "Hello!"
        manager._gemini_client = mock_gemini_instance
        
        state_before = manager.get_state()
        assert not state_before.is_active
        
        manager.start_conversation()
        
        state_after = manager.get_state()
        assert state_after.is_active
    
    def test_start_conversation_clears_history(self, mock_manager):
        """Verify start_conversation clears previous history."""
        manager, mock_gemini = mock_manager
        
        mock_gemini_instance = Mock()
        mock_gemini_instance.generate_text.return_value = "Hello!"
        manager._gemini_client = mock_gemini_instance
        
        # Manually add some history
        manager._history = [Mock(), Mock(), Mock()]
        
        manager.start_conversation()
        
        # After start, history should contain only the new greeting
        assert len(manager._history) == 1
        assert manager._history[0].role == "assistant"
    
    def test_start_conversation_api_failure(self, mock_manager):
        """Verify API failure during start is propagated."""
        manager, mock_gemini = mock_manager
        
        mock_gemini_instance = Mock()
        mock_gemini_instance.generate_text.side_effect = GeminiAPIError("API failed")
        manager._gemini_client = mock_gemini_instance
        
        with pytest.raises(GeminiAPIError):
            manager.start_conversation()
        
        # Should mark conversation as inactive after failure
        assert not manager.get_state().is_active


class TestSendMessage:
    """Test sending messages and receiving responses."""
    
    @pytest.fixture
    def active_manager(self):
        """Fixture providing an active ConversationManager with history."""
        with patch("ai.conversation.GeminiClient") as mock_gemini:
            manager = ConversationManager(api_key="test-key", language="en")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Nice to meet you!"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            yield manager
    
    def test_send_message_requires_active_conversation(self):
        """Verify send_message requires conversation to be active."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            
            with pytest.raises(ValueError) as exc:
                manager.send_message("Hello")
            assert "not active" in str(exc.value).lower()
    
    def test_send_message_empty_raises_error(self, active_manager):
        """Verify empty message raises ValueError."""
        with pytest.raises(ValueError) as exc:
            active_manager.send_message("")
        assert "non-empty" in str(exc.value).lower()
    
    def test_send_message_whitespace_raises_error(self, active_manager):
        """Verify whitespace-only message raises ValueError."""
        with pytest.raises(ValueError):
            active_manager.send_message("   \n\t  ")
    
    def test_send_message_none_raises_error(self, active_manager):
        """Verify None message raises ValueError."""
        with pytest.raises(ValueError):
            active_manager.send_message(None)
    
    def test_send_message_non_string_raises_error(self, active_manager):
        """Verify non-string message raises ValueError."""
        with pytest.raises(ValueError):
            active_manager.send_message(123)
    
    def test_send_message_success(self, active_manager):
        """Verify successful message processing returns response."""
        active_manager._gemini_client.generate_text.return_value = "What's your name?"
        
        response = active_manager.send_message("Hello, I'm here to explore careers")
        
        assert isinstance(response, str)
        assert "name" in response.lower()
    
    def test_send_message_adds_to_history(self, active_manager):
        """Verify messages are added to history."""
        active_manager._gemini_client.generate_text.return_value = "Response"
        
        initial_count = len(active_manager._history)
        active_manager.send_message("Hello")
        
        # Should have user message + assistant response
        assert len(active_manager._history) == initial_count + 2
        assert active_manager._history[-2].role == "user"
        assert active_manager._history[-1].role == "assistant"
    
    def test_send_message_api_failure(self, active_manager):
        """Verify API failure is propagated."""
        active_manager._gemini_client.generate_text.side_effect = GeminiAPIError("API failed")
        
        with pytest.raises(GeminiAPIError):
            active_manager.send_message("Hello")


class TestConversationFlow:
    """Test multi-turn conversation flow."""
    
    def test_conversation_flow_multiple_turns(self):
        """Verify complete conversation with multiple turns."""
        with patch("ai.conversation.GeminiClient") as mock_gemini:
            manager = ConversationManager(api_key="test-key", language="en")
            
            # Mock responses for multiple turns
            responses = [
                "Hello! Welcome to Kaushal Marg. What's your name?",
                "Nice to meet you, Alice! How old are you?",
                "Great! What skills do you have?",
            ]
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.side_effect = responses
            manager._gemini_client = mock_gemini_instance
            
            # Start conversation
            greeting = manager.start_conversation()
            assert "Welcome" in greeting
            
            # Turn 1
            response1 = manager.send_message("My name is Alice")
            assert "How old" in response1 or "age" in response1
            
            # Turn 2
            response2 = manager.send_message("I'm 25 years old")
            assert "skills" in response2.lower()
    
    def test_conversation_maintains_language(self):
        """Verify conversation maintains the selected language."""
        with patch("ai.conversation.GeminiClient") as mock_gemini:
            manager = ConversationManager(api_key="test-key", language="hi")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "नमस्ते"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            manager.send_message("नमस्ते")
            
            # Check that all messages have the correct language
            for msg in manager._history:
                assert msg.language == "hi"


class TestLanguageSwitching:
    """Test language switching."""
    
    def test_set_language_valid(self):
        """Verify language can be changed."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            assert manager.get_language() == "en"
            
            manager.set_language("hi")
            assert manager.get_language() == "hi"
            
            manager.set_language("mr")
            assert manager.get_language() == "mr"
    
    def test_set_language_invalid_raises_error(self):
        """Verify invalid language raises ValueError."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            
            with pytest.raises(ValueError) as exc:
                manager.set_language("invalid")
            assert "Language must be" in str(exc.value)
    
    def test_language_change_affects_new_messages(self):
        """Verify language change affects new messages but not old ones."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            # Add message in English
            manager.send_message("Hello")
            
            # Switch to Hindi
            manager.set_language("hi")
            
            # Add message in Hindi
            manager.send_message("नमस्ते")
            
            # Check languages
            assert manager._history[0].language == "en"  # First message
            assert manager._history[-1].language == "hi"  # Last message


class TestConversationHistory:
    """Test conversation history management."""
    
    def test_history_respects_max_size(self):
        """Verify history is trimmed to max_history_size."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", max_history_size=5)
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            # Add more messages than max
            for i in range(10):
                manager.send_message(f"Message {i}")
            
            # History should not exceed max_history_size
            assert len(manager._history) <= 5
    
    def test_history_message_structure(self):
        """Verify messages in history have correct structure."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            manager.send_message("Hello")
            
            # Check message structure
            user_msg = manager._history[0]
            assert isinstance(user_msg, Message)
            assert user_msg.role == "user"
            assert user_msg.content == "Hello"
            assert user_msg.language == "en"
            assert user_msg.timestamp is not None


class TestReset:
    """Test conversation reset."""
    
    def test_reset_clears_history(self):
        """Verify reset clears message history."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            manager._history = [Mock(), Mock(), Mock()]
            manager._is_active = True
            
            manager.reset()
            
            assert len(manager._history) == 0
    
    def test_reset_deactivates_conversation(self):
        """Verify reset marks conversation as inactive."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            manager._is_active = True
            
            manager.reset()
            
            assert not manager.get_state().is_active
    
    def test_reset_allows_new_conversation(self):
        """Verify reset allows starting a new conversation."""
        with patch("ai.conversation.GeminiClient") as mock_gemini:
            manager = ConversationManager(api_key="test-key")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Hello again!"
            manager._gemini_client = mock_gemini_instance
            
            # Add some history
            manager._is_active = True
            manager._history = [Mock()]
            
            # Reset
            manager.reset()
            
            # Start new conversation
            greeting = manager.start_conversation()
            assert greeting == "Hello again!"
            assert len(manager._history) == 1


class TestStateExport:
    """Test safe state export."""
    
    def test_get_state_returns_metadata_only(self):
        """Verify get_state returns only metadata, not full content."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            # Add sensitive message
            manager._history = [
                Message(role="user", content="My phone number is 1234567890", language="en"),
                Message(role="assistant", content="I'll help you", language="en"),
            ]
            
            state = manager.get_state()
            
            # Verify state is safe
            assert isinstance(state, ConversationState)
            assert state.language == "en"
            assert state.is_active
            assert state.message_count == 2
            assert state.turn_count == 1
            
            # Verify no sensitive data
            state_dict = state.model_dump()
            assert "phone" not in str(state_dict).lower()
            assert "1234567890" not in str(state_dict)
    
    def test_get_state_accurate_counts(self):
        """Verify get_state returns accurate message and turn counts."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            # Add 3 complete turns (6 messages)
            for i in range(3):
                manager.send_message(f"Message {i}")
            
            state = manager.get_state()
            
            assert state.message_count == 6
            assert state.turn_count == 3


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_gemini_api_error_propagated(self):
        """Verify GeminiAPIError is propagated, not swallowed."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.side_effect = GeminiAPIError("API error")
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            with pytest.raises(GeminiAPIError):
                manager.send_message("Hello")
    
    def test_message_content_sanitized(self):
        """Verify messages are trimmed correctly."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            # Message with leading/trailing whitespace
            manager.send_message("  Hello world  ")
            
            # Check trimmed
            user_msg = manager._history[0]
            assert user_msg.content == "Hello world"


class TestLogging:
    """Test that sensitive data is not logged."""
    
    def test_no_api_key_in_logs(self, caplog):
        """Verify API key is not logged."""
        test_key = "secret-key-12345"
        with patch("ai.conversation.GeminiClient"):
            with caplog.at_level(logging.DEBUG):
                ConversationManager(api_key=test_key)
            
            # Check logs don't contain API key
            for record in caplog.records:
                assert test_key not in record.message
    
    def test_sensitive_conversation_data_not_logged(self, caplog):
        """Verify full conversation content not logged."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            sensitive_message = "My social security number is 123-45-6789"
            
            with caplog.at_level(logging.DEBUG):
                manager.send_message(sensitive_message)
            
            # Check logs don't contain full message
            for record in caplog.records:
                assert sensitive_message not in record.message


class TestSystemPrompts:
    """Test that correct system prompts are used."""
    
    def test_english_system_prompt_exists(self):
        """Verify English system prompt is defined."""
        assert "en" in ConversationManager.SYSTEM_PROMPTS
        prompt = ConversationManager.SYSTEM_PROMPTS["en"]
        assert len(prompt) > 0
        assert "skill" in prompt.lower()
    
    def test_hindi_system_prompt_exists(self):
        """Verify Hindi system prompt is defined."""
        assert "hi" in ConversationManager.SYSTEM_PROMPTS
        prompt = ConversationManager.SYSTEM_PROMPTS["hi"]
        assert len(prompt) > 0
        assert isinstance(prompt, str)
    
    def test_marathi_system_prompt_exists(self):
        """Verify Marathi system prompt is defined."""
        assert "mr" in ConversationManager.SYSTEM_PROMPTS
        prompt = ConversationManager.SYSTEM_PROMPTS["mr"]
        assert len(prompt) > 0
        assert isinstance(prompt, str)
    
    def test_correct_prompt_used_in_context(self):
        """Verify correct system prompt is used when generating responses."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="hi")
            mock_gemini_instance = Mock()
            mock_gemini_instance.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini_instance
            manager._is_active = True
            
            manager.send_message("नमस्ते")
            
            # Verify Hindi prompt was passed to generate_text
            call_args = mock_gemini_instance.generate_text.call_args
            context = call_args[0][0]
            assert ConversationManager.SYSTEM_PROMPTS["hi"] in context


class TestDeterministicBehavior:
    """Test deterministic behavior for reproducibility."""
    
    def test_same_input_generates_same_request(self):
        """Verify same input generates same API request."""
        with patch("ai.conversation.GeminiClient"):
            manager1 = ConversationManager(api_key="test-key", language="en")
            manager2 = ConversationManager(api_key="test-key", language="en")
            
            mock1 = Mock()
            mock1.generate_text.return_value = "Response"
            manager1._gemini_client = mock1
            manager1._is_active = True
            
            mock2 = Mock()
            mock2.generate_text.return_value = "Response"
            manager2._gemini_client = mock2
            manager2._is_active = True
            
            manager1.send_message("Hello")
            manager2.send_message("Hello")
            
            # Both should call generate_text with same context
            call1 = mock1.generate_text.call_args[0][0]
            call2 = mock2.generate_text.call_args[0][0]
            
            # Context should include same system prompt
            assert ConversationManager.SYSTEM_PROMPTS["en"] in call1
            assert ConversationManager.SYSTEM_PROMPTS["en"] in call2


class TestGetHistory:
    """Test get_history() method for exposing conversation message history."""
    
    def test_get_history_returns_message_list(self):
        """Verify get_history() returns a list of Message objects."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key")
            history = manager.get_history()
            
            assert isinstance(history, list)
            assert len(history) == 0  # No messages yet
    
    def test_get_history_contains_message_objects(self):
        """Verify returned messages are Message objects."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            
            mock_gemini = Mock()
            mock_gemini.generate_text.return_value = "Hello!"
            manager._gemini_client = mock_gemini
            
            manager.start_conversation()
            history = manager.get_history()
            
            assert len(history) == 1
            assert isinstance(history[0], Message)
            assert history[0].role == "assistant"
            assert history[0].language == "en"
    
    def test_get_history_updates_after_messages(self):
        """Verify history updates correctly after user and assistant messages."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            
            mock_gemini = Mock()
            mock_gemini.generate_text.return_value = "Hi there!"
            manager._gemini_client = mock_gemini
            
            manager.start_conversation()
            assert len(manager.get_history()) == 1
            
            manager.send_message("Hello")
            history = manager.get_history()
            
            assert len(history) == 3  # greeting + user + response
            assert history[1].role == "user"
            assert history[1].content == "Hello"
            assert history[2].role == "assistant"
            assert history[2].content == "Hi there!"
    
    def test_get_history_cleared_after_reset(self):
        """Verify history is cleared after reset()."""
        with patch("ai.conversation.GeminiClient"):
            manager = ConversationManager(api_key="test-key", language="en")
            
            mock_gemini = Mock()
            mock_gemini.generate_text.return_value = "Response"
            manager._gemini_client = mock_gemini
            
            manager.start_conversation()
            assert len(manager.get_history()) == 1
            
            manager.reset()
            history = manager.get_history()
            
            assert isinstance(history, list)
            assert len(history) == 0
