import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.explanation import ExplanationGenerator

class TestExplanationFallback(unittest.TestCase):
    
    def test_deterministic_markdown_fallback_english(self):
        """Ensure that ExplanationGenerator falls back gracefully without Gemini and returns deterministic Markdown."""
        # Initialize with an intentionally invalid API key so it uses fallback
        gen = ExplanationGenerator(api_key="invalid_test_key_that_will_fail")
        
        # Override the internal client explicitly to None to simulate failure or lack of credentials
        gen._gemini_client = None
        
        test_result = {
            "job_role": "Solar PV Installer (Suryamitra)",
            "sector": "Green Jobs",
            "nsqf_level": "Level 4",
            "score": 85,
            "matched_skills": ["Solar wiring", "Safety"],
            "missing_skills": ["Panel mounting"],
            "local_opportunity": "Active training center in Jaipur",
            "employment_type": "Wage-Employment"
        }
        
        # Generate English
        explanation_en = gen.generate_explanation(recommendation_result=test_result, language="en")
        
        # Check that it didn't crash and returns string
        self.assertIsInstance(explanation_en, str)
        
        # Check for presence of deterministic markdown headers
        self.assertIn("**Recommended Role:** Solar PV Installer (Suryamitra)", explanation_en)
        self.assertIn("**Sector:** Green Jobs", explanation_en)
        self.assertIn("**NSQF Level:** Level 4", explanation_en)
        self.assertIn("**Match Score:** 85%", explanation_en)
        self.assertIn("**Matched Skills:** Solar wiring, Safety", explanation_en)
        self.assertIn("**Missing Skills:** Panel mounting", explanation_en)
        self.assertIn("**Local Opportunity:** Active training center in Jaipur", explanation_en)

    def test_deterministic_markdown_fallback_hindi(self):
        """Ensure that Hindi deterministic fallback renders properly."""
        gen = ExplanationGenerator(api_key="invalid_test_key_that_will_fail")
        gen._gemini_client = None
        
        test_result = {
            "job_role": "Plumber",
            "sector": "Construction",
            "nsqf_level": "Level 3",
            "score": 90
        }
        
        explanation_hi = gen.generate_explanation(recommendation_result=test_result, language="hi")
        
        # Check for Hindi properties
        self.assertIn("**अनुशंसित भूमिका:** Plumber", explanation_hi)
        self.assertIn("**स्कोर:** 90%", explanation_hi)
        self.assertIn("**मिलान कौशल्य:** कोई नहीं", explanation_hi)  # Default fallback for missing matched_skills in Hindi

if __name__ == "__main__":
    unittest.main()
