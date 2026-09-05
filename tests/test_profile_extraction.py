"""
Tests for the AI ProfileExtractor and new BeneficiaryProfile schema.

Covers:
1. Pydantic validation for new fields (name, occupation, constraints, etc.)
2. Multilingual extraction without inventing fields.
3. Fallback/empty field handling.
4. Edge cases with multiple conversation turns.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.profile_extractor import ProfileExtractor, BeneficiaryProfile
from ai.conversation import Message
from pydantic import ValidationError


class TestProfileExtractor(unittest.TestCase):
    """Test suite for ProfileExtractor with the new SIH PS 26097 fields."""

    def test_beneficiary_profile_schema(self):
        """Test the extended Pydantic schema validation."""
        # Empty profile should be valid
        empty_profile = BeneficiaryProfile()
        self.assertIsNone(empty_profile.name)
        self.assertIsNone(empty_profile.age)
        self.assertIsNone(empty_profile.education)
        self.assertEqual(empty_profile.skills, [])
        self.assertIsNone(empty_profile.constraints)
        self.assertIsNone(empty_profile.family_occupation)
        self.assertIsNone(empty_profile.local_context)

        # Valid populated profile
        full_profile = BeneficiaryProfile(
            name="Sunita",
            age=30,
            education="10th Pass",
            current_occupation="Tailor Assistant",
            work_experience="2 years",
            family_occupation="Weaving",
            skills=["Stitching", "Embroidery"],
            interests=["Fashion"],
            aspirations="Start a boutique",
            district="Patna",
            local_context="Rural village near city",
            employment_preference="Self-Employment",
            mobility="Local",
            constraints="Takes care of children at home",
            preferred_language="hi"
        )
        self.assertEqual(full_profile.name, "Sunita")
        self.assertEqual(full_profile.age, 30)
        self.assertEqual(len(full_profile.skills), 2)
        self.assertEqual(full_profile.constraints, "Takes care of children at home")
        self.assertEqual(full_profile.family_occupation, "Weaving")

    @patch("ai.profile_extractor.GeminiClient")
    def test_extract_profile_basic(self, MockGeminiClient):
        """Test extracting a profile from conversation messages."""
        mock_client = MagicMock()
        
        # Mock Gemini returning a structured BeneficiaryProfile
        mock_response = BeneficiaryProfile(
            name="Rahul",
            district="Indore",
            skills=["Tractor operation"]
        )
        mock_client.generate_structured.return_value = mock_response
        MockGeminiClient.return_value = mock_client

        extractor = ProfileExtractor(api_key="test_key")
        messages = [
            Message(role="assistant", content="What is your name?", language="en"),
            Message(role="user", content="I am Rahul from Indore. I can drive a tractor.", language="en")
        ]
        
        profile_dict = extractor.extract_profile(messages)
        self.assertEqual(profile_dict["name"], "Rahul")
        self.assertEqual(profile_dict["district"], "Indore")
        self.assertIn("Tractor operation", profile_dict["skills"])
        self.assertIsNone(profile_dict["education"]) # Ensure it doesn't invent missing fields
        self.assertIsNone(profile_dict["constraints"])

    @patch("ai.profile_extractor.GeminiClient")
    def test_extract_profile_missing_fields_no_invention(self, MockGeminiClient):
        """Ensure missing fields are returned as None/empty lists, not default values."""
        mock_client = MagicMock()
        mock_response = BeneficiaryProfile()
        mock_client.generate_structured.return_value = mock_response
        MockGeminiClient.return_value = mock_client

        extractor = ProfileExtractor(api_key="test_key")
        messages = [Message(role="user", content="Hello.", language="en")]
        
        profile_dict = extractor.extract_profile(messages)
        # Verify it doesn't default to Ramesh Kumar / Indore / 10th pass
        self.assertIsNone(profile_dict["name"])
        self.assertIsNone(profile_dict["district"])
        self.assertIsNone(profile_dict["education"])
        self.assertIsNone(profile_dict["employment_preference"])
        self.assertEqual(profile_dict["skills"], [])
        
    @patch("ai.profile_extractor.GeminiClient")
    def test_extract_profile_multilingual(self, MockGeminiClient):
        """Test processing non-English conversations."""
        mock_client = MagicMock()
        mock_response = BeneficiaryProfile(
            name="Sunita",
            skills=["Sewing"],
            district="Pune"
        )
        mock_client.generate_structured.return_value = mock_response
        MockGeminiClient.return_value = mock_client

        extractor = ProfileExtractor(api_key="test_key")
        messages = [
            Message(role="assistant", content="तुमचे नाव काय आहे?", language="mr"),
            Message(role="user", content="मी सुनीता, पुण्याहून आहे. मला शिवणकाम येते.", language="mr")
        ]
        
        profile_dict = extractor.extract_profile(messages)
        self.assertEqual(profile_dict["name"], "Sunita")
        self.assertEqual(profile_dict["district"], "Pune")
        self.assertEqual(profile_dict["skills"], ["Sewing"])

    def test_extract_profile_empty_history(self):
        """Test extracting from empty message history."""
        extractor = ProfileExtractor(api_key="test_key")
        profile_dict = extractor.extract_profile([])
        self.assertIsNone(profile_dict["name"])
        self.assertEqual(profile_dict["skills"], [])


if __name__ == "__main__":
    unittest.main()
