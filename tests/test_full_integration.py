"""
Full System Integration Test Suite for Kaushal Marg
Validates the complete 17-step end-to-end workflow across:
- Person 1: AI, Conversation, Profile Extraction, Explanation, Audio, TTS
- Person 2: NSQF Matching, Scoring, Skill Gap Analysis, My Skill Journey Pathway
- Person 3: Platform SQLite Database, Seeding, and Admin Dashboard Analytics

Team: Binary Minds | SIH Problem Statement 26097
"""

import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch

# Person 1 Modules
from ai.conversation import ConversationManager, Language, Message
from ai.profile_extractor import ProfileExtractor, BeneficiaryProfile
from ai.explanation import ExplanationGenerator
from voice.tts import TTSEngine, prepare_utterance
from voice.audio import AudioTranscriber, UnsupportedLanguageError, UnsupportedMimeTypeError

# Person 2 Modules
from recommendation.matcher import recommend_jobs, load_nsqf_jobs
from recommendation.scoring import calculate_total_score, match_skills
from recommendation.skill_gap import analyze_skill_gap
from recommendation.pathway import generate_skill_pathway

# Person 3 Modules
from database.database import (
    init_db,
    create_beneficiary,
    save_profile,
    get_profile,
    save_conversation,
    get_conversation_history,
    save_recommendation,
    save_recommendations_batch,
    get_recommendations,
    get_filtered_dashboard_data
)
from data.demo_profiles import SYNTHETIC_BENEFICIARY_PROFILES


class TestFullSystemIntegration(unittest.TestCase):
    """End-to-End Integration Test Suite."""

    def setUp(self):
        """Set up temporary SQLite database for each test."""
        self.fd, self.temp_db = tempfile.mkstemp(suffix=".db")
        os.close(self.fd)
        init_db(self.temp_db)

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db):
            try:
                os.remove(self.temp_db)
            except PermissionError:
                pass

    def test_trilingual_conversation_and_profile_extraction(self):
        """Tests conversational management across English, Hindi, and Marathi."""
        for lang_code in ["en", "hi", "mr"]:
            cm = ConversationManager(api_key="mock_key", language=lang_code)
            self.assertEqual(cm.get_language(), lang_code)
            self.assertEqual(cm.get_state().turn_count, 0)

            # Test BeneficiaryProfile validation
            prof = BeneficiaryProfile(
                education="10th Pass",
                skills=["Tractor operation", "Basic farming"],
                interests=["Agriculture"],
                district="Indore",
                employment_preference="Self-Employment",
                mobility="Low"
            )
            prof_dict = prof.model_dump()
            self.assertEqual(prof_dict["education"], "10th Pass")
            self.assertEqual(len(prof_dict["skills"]), 2)

    def test_deterministic_recommendation_and_skill_journey_pipeline(self):
        """Tests the complete deterministic matching, skill gap, and pathway flow."""
        candidate = {
            "name": "Ramesh Kumar",
            "education": "10th Pass",
            "skills": ["Tractor operation"],
            "interests": ["Agriculture", "Machinery"],
            "district": "Indore",
            "mobility": "Low",
            "employment_preference": "Self-Employment"
        }

        # Step 1: NSQF Recommendations
        recs = recommend_jobs(candidate, top_n=3)
        self.assertEqual(len(recs), 3)
        
        top_1 = recs[0]
        self.assertEqual(top_1["job_role"], "Tractor Operator")
        self.assertGreaterEqual(top_1["score"], 70.0)
        self.assertEqual(top_1["employment_type"], "Self-Employment")

        # Step 2: Skill Gap Analysis
        gap = analyze_skill_gap(candidate, top_1)
        self.assertIn("Tractor driving", gap["matched_skills"])
        self.assertIn("Implement hitching", gap["missing_skills"])
        self.assertGreater(gap["skill_coverage_percentage"], 0.0)

        # Step 3: "My Skill Journey" Pathway Roadmap
        pathway = generate_skill_pathway(
            beneficiary_profile=candidate,
            recommended_job_role=top_1,
            missing_skills=gap["missing_skills"]
        )
        self.assertIn("current_state", pathway)
        self.assertIn("training_stage", pathway)
        self.assertIn("practical_stage", pathway)
        self.assertIn("target_role", pathway)
        self.assertEqual(pathway["target_role"]["role"], "Tractor Operator")

    def test_voice_tts_and_explanation_narrative(self):
        """Tests TTS utterance config and plain-language explanation generation."""
        # Test TTS Engine across languages
        tts = TTSEngine()
        cfg_hi = tts.prepare_utterance("नमस्ते, आपका स्वागत है", language="hi")
        self.assertEqual(cfg_hi.lang, "hi-IN")
        
        cfg_en = tts.prepare_utterance("Welcome to Kaushal Marg", language="en")
        self.assertEqual(cfg_en.lang, "en-IN")

        cfg_mr = prepare_utterance("नमस्कार, कौशल्य मार्गात आपले स्वागत आहे", language="mr")
        self.assertEqual(cfg_mr.lang, "mr-IN")

        # Test Explanation Generator with fallback safety
        exp_gen = ExplanationGenerator()
        rec_data = {
            "job_role": "Tractor Operator",
            "sector": "Agriculture",
            "score": 83.0,
            "matched_skills": ["Tractor driving"],
            "missing_skills": ["Implement hitching"],
            "local_opportunity": "Indore Cluster"
        }
        for l_code in ["en", "hi", "mr"]:
            explanation = exp_gen.generate_explanation(rec_data, language=l_code)
            self.assertTrue(len(explanation) > 10)

    def test_end_to_end_sqlite_storage_and_dashboard_aggregation(self):
        """Tests full SQLite persistence of beneficiary, conversation, and recommendations."""
        # 1. Create Beneficiary
        b_id = create_beneficiary(
            name="Suresh Bunkar",
            preferred_language="hi",
            district="Udaipur",
            db_path=self.temp_db
        )
        self.assertTrue(b_id.startswith("KM-"))

        # 2. Save Profile
        prof_id = save_profile(
            beneficiary_id=b_id,
            education="8th Pass",
            skills=["Organic composting"],
            interests=["Agriculture"],
            district="Udaipur",
            mobility="Low",
            employment_preference="Self-Employment",
            db_path=self.temp_db
        )
        self.assertIsInstance(prof_id, int)

        # 3. Save Conversation Turns
        save_conversation(b_id, "user", "मुझे जैविक खेती पसंद है।", "voice", db_path=self.temp_db)
        save_conversation(b_id, "assistant", "उदयपुर में जैविक खेती के अवसर उपलब्ध हैं।", "text", db_path=self.temp_db)
        history = get_conversation_history(b_id, db_path=self.temp_db)
        self.assertEqual(len(history), 2)

        # 4. Save Top Recommendations Batch
        recs = recommend_jobs({
            "education": "8th Pass",
            "skills": ["Organic composting"],
            "interests": ["Agriculture"],
            "district": "Udaipur",
            "mobility": "Low",
            "employment_preference": "Self-Employment"
        }, top_n=3)
        batch_ids = save_recommendations_batch(b_id, recs, db_path=self.temp_db)
        self.assertEqual(len(batch_ids), 3)

        # 5. Verify Real-time Dashboard Aggregation
        dash_stats = get_filtered_dashboard_data(db_path=self.temp_db)
        self.assertEqual(dash_stats["total_beneficiaries"], 1)
        self.assertGreater(dash_stats["average_match_score"], 50.0)
        self.assertIn("Udaipur", dash_stats["district_distribution"])


if __name__ == "__main__":
    unittest.main()
