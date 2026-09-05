"""
Unit tests for the UI integration with ConversationManager.

Covers:
1. Conversation start
2. User message processing
3. History persistence
4. Language switching
5. API Failure handling

Team: Binary Minds | SIH Problem Statement 26097
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pages.beneficiary import get_conversation_manager, restart_interview, init_session_state
from ai.conversation import ConversationManager
from ai.gemini import GeminiAPIError
import streamlit as st


class MockSessionState(dict):
    """Simple mock for Streamlit session state."""
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        self[key] = value


class TestConversationUI(unittest.TestCase):
    """Test suite for Beneficiary UI ConversationManager integration."""

    def setUp(self):
        """Set up a fresh mock session state before each test."""
        self.patcher = patch("pages.beneficiary.st.session_state", new_callable=MockSessionState)
        self.mock_session = self.patcher.start()
        
        # We also need to patch logger to avoid noise, but not strictly necessary

    def tearDown(self):
        """Stop patches."""
        self.patcher.stop()

    @patch("ai.conversation.GeminiClient")
    def test_get_conversation_manager_initialization(self, MockGeminiClient):
        """Test getting and caching the conversation manager."""
        mock_client = MagicMock()
        MockGeminiClient.return_value = mock_client
        
        # Should create a new one
        manager1 = get_conversation_manager("en")
        self.assertIsInstance(manager1, ConversationManager)
        self.assertEqual(manager1.get_language(), "en")
        
        # Should reuse the cached one
        manager2 = get_conversation_manager("en")
        self.assertIs(manager1, manager2)
        
        # Should create a new one for a different language
        manager3 = get_conversation_manager("hi")
        self.assertEqual(manager3.get_language(), "hi")
        self.assertIsNot(manager1, manager3)

    @patch("ai.conversation.GeminiClient")
    def test_restart_interview_starts_conversation(self, MockGeminiClient):
        """Test that restarting the interview calls start_conversation."""
        mock_client = MagicMock()
        mock_client.generate_text.return_value = "Hello! I am ready to help."
        MockGeminiClient.return_value = mock_client
        
        self.mock_session["api_calls"] = 0
        self.mock_session["last_api_error"] = None
        restart_interview("en")
        
        self.assertEqual(self.mock_session["beneficiary_step"], 1)
        self.assertIn("chat_messages", self.mock_session)
        
        messages = self.mock_session["chat_messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["sender"], "assistant")
        self.assertEqual(messages[0]["text"], "Hello! I am ready to help.")

    @patch("ai.conversation.GeminiClient")
    def test_restart_interview_api_failure_fallback(self, MockGeminiClient):
        """Test that API failures during restart fall back to static greetings."""
        mock_client = MagicMock()
        mock_client.generate_text.side_effect = GeminiAPIError("Network error")
        MockGeminiClient.return_value = mock_client
        
        restart_interview("hi")
        
        messages = self.mock_session["chat_messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["sender"], "assistant")
        self.assertIn("नमस्ते", messages[0]["text"])

    @patch("ai.conversation.GeminiClient")
    def test_send_message_updates_history(self, MockGeminiClient):
        """Simulate sending a message and getting a reply."""
        mock_client = MagicMock()
        mock_client.generate_text.side_effect = [
            "Welcome greeting.",
            "That's great. Do you have any prior experience?"
        ]
        MockGeminiClient.return_value = mock_client
        
        manager = get_conversation_manager("en")
        manager.start_conversation()
        
        # Simulate user input logic from beneficiary.py
        user_input = "I am a 12th pass."
        self.mock_session["chat_messages"] = [{"sender": "assistant", "text": "Welcome greeting."}]
        self.mock_session["chat_messages"].append({"sender": "user", "text": user_input})
        
        reply = manager.send_message(user_input)
        self.mock_session["chat_messages"].append({"sender": "assistant", "text": reply})
        
        # Verify history
        hist = manager.get_history()
        self.assertEqual(len(hist), 3) # greeting, user, reply
        self.assertEqual(hist[-1].content, "That's great. Do you have any prior experience?")
        
        # Verify session state
        msgs = self.mock_session["chat_messages"]
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[-1]["sender"], "assistant")
        self.assertEqual(msgs[-1]["text"], "That's great. Do you have any prior experience?")

    def test_init_session_state(self):
        """Test that init_session_state initializes default keys without overwriting existing ones."""
        # Partially initialized state
        self.mock_session["active_nav"] = "🎯 Recommendations"
        self.mock_session["beneficiary_step"] = 2
        
        init_session_state()
        
        # Existing should remain
        self.assertEqual(self.mock_session["active_nav"], "🎯 Recommendations")
        self.assertEqual(self.mock_session["beneficiary_step"], 2)
        
        # New should be created
        self.assertEqual(self.mock_session["selected_lang_code"], "hi")
        self.assertEqual(self.mock_session["is_demo"], False)
        self.assertEqual(self.mock_session["extracted_profile"], {})
        self.assertEqual(self.mock_session["demo_profile"], {})
        self.assertEqual(self.mock_session["chat_messages"], [])
        self.assertIsNone(self.mock_session["current_beneficiary_id"])
        self.assertIsNone(self.mock_session["last_processed_audio_token"])

    @patch("ai.conversation.GeminiClient")
    def test_restart_interview_clears_real_state(self, MockGeminiClient):
        """Test that restart_interview wipes sensitive data and resets state."""
        mock_client = MagicMock()
        MockGeminiClient.return_value = mock_client
        
        # Set some dirty state
        self.mock_session["beneficiary_step"] = 3
        self.mock_session["current_beneficiary_id"] = "KM-IND-1234"
        self.mock_session["extracted_profile"] = {"name": "Test User"}
        self.mock_session["demo_profile"] = {"name": "Demo User"}
        self.mock_session["is_demo"] = True
        self.mock_session["last_processed_audio_token"] = "some_token"
        self.mock_session["conv_manager_lang"] = "hi"
        
        restart_interview("en")
        
        self.assertEqual(self.mock_session["beneficiary_step"], 1)
        self.assertIsNone(self.mock_session["current_beneficiary_id"])
        self.assertEqual(self.mock_session["extracted_profile"], {})
        self.assertEqual(self.mock_session["demo_profile"], {})
        self.assertFalse(self.mock_session["is_demo"])
        self.assertIsNone(self.mock_session["last_processed_audio_token"])
        self.assertEqual(self.mock_session["conv_manager_lang"], "en")


if __name__ == "__main__":
    unittest.main()
