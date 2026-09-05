import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.gemini import GeminiClient, GeminiQuotaError, GeminiConfigError
from ai.profile_extractor import ProfileExtractor
from recommendation.matcher import recommend_jobs
from voice.audio import AudioTranscriber, TranscriptionResult

class TestFailures(unittest.TestCase):
    def test_gemini_429_quota(self):
        """Test how the application handles a 429 quota exhaustion from Gemini."""
        client = GeminiClient(api_key="mock_key")
        
        with patch('ai.gemini.GeminiClient._call_generate_content') as mock_generate:
            mock_generate.side_effect = GeminiQuotaError(message="429 RESOURCE_EXHAUSTED", retry_delay=40)
            
            with self.assertRaises(GeminiQuotaError):
                client.generate_text("Hello")

    def test_empty_transcription(self):
        """Test how empty audio/transcription is handled."""
        transcriber = AudioTranscriber(api_key="mock_key")
        with patch('voice.audio.AudioTranscriber._call_gemini') as mock_call:
            mock_call.return_value = ""
            
            result = transcriber.transcribe(b"x" * 64, mime_type="audio/wav")
            self.assertTrue(result.is_empty)
            self.assertEqual(result.text, "")

    def test_no_local_opportunities(self):
        """Test recommendation behavior when no local opportunities exist."""
        # Using a district not in the demo CSVs
        profile = {
            "name": "Test",
            "education": "10th Pass",
            "skills": ["Tractor operation"],
            "district": "UnknownDistrictX",
            "employment_preference": "Self-Employment"
        }
        
        recs = recommend_jobs(profile, top_n=1)
        self.assertIsNotNone(recs)
        
        if len(recs) > 0 and recs[0]["status"] not in ("insufficient_information", "no_strong_match"):
            # the score should be lower because opportunity score is 0
            # opportunity_info should say no verified data
            self.assertEqual(recs[0]["local_opportunity_details"], None)
            self.assertEqual(recs[0]["local_opportunity"], "No verified local opportunity data available")
        elif len(recs) > 0:
            self.assertEqual(recs[0]["status"], "no_strong_match")

if __name__ == '__main__':
    unittest.main()
