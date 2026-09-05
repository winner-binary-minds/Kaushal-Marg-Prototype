"""
Unit Tests for Kaushal Marg Database Layer (database/database.py)
Tests schema initialization, CRUD operations, parameterized SQL safety, and dashboard metrics.

Team: Binary Minds | SIH Problem Statement 26097
"""

import os
import tempfile
import unittest
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
    get_dashboard_statistics,
    generate_beneficiary_id
)


class TestDatabaseModule(unittest.TestCase):
    """Test suite for SQLite database management."""

    def setUp(self):
        """Creates a fresh temporary database file for each test."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

    def tearDown(self):
        """Closes and removes the temporary database after each test."""
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    def test_init_db(self):
        """Verifies tables and schema are created properly."""
        stats = get_dashboard_statistics(self.temp_db_path)
        self.assertEqual(stats["total_beneficiaries"], 0)
        self.assertEqual(stats["total_profiles"], 0)

    def test_generate_beneficiary_id(self):
        """Verifies format of generated beneficiary IDs."""
        id_indore = generate_beneficiary_id("Indore")
        self.assertTrue(id_indore.startswith("KM-IND-"))
        self.assertEqual(len(id_indore), 11)

        id_generic = generate_beneficiary_id()
        self.assertTrue(id_generic.startswith("KM-GIA-"))

    def test_create_beneficiary_and_profile(self):
        """Verifies creating a beneficiary and saving their skilling profile."""
        ben_id = create_beneficiary(
            name="Ramesh Kumar",
            preferred_language="hi",
            district="Indore",
            db_path=self.temp_db_path
        )
        self.assertTrue(ben_id.startswith("KM-IND-"))

        profile_id = save_profile(
            beneficiary_id=ben_id,
            age=25,
            education="10th Pass",
            current_occupation="Farm helper",
            work_experience="3 years",
            family_occupation="Farming",
            skills=["Tractor operation", "Basic farming"],
            interests=["Agriculture", "Machinery"],
            aspirations="Own a tractor",
            district="Indore",
            local_context="Rural village outside Indore",
            mobility="Low",
            employment_preference="Self-Employment",
            constraints="None",
            db_path=self.temp_db_path
        )
        self.assertIsInstance(profile_id, int)

        # Retrieve profile
        profile = get_profile(ben_id, self.temp_db_path)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "Ramesh Kumar")
        self.assertEqual(profile["age"], 25)
        self.assertEqual(profile["education"], "10th Pass")
        self.assertEqual(profile["current_occupation"], "Farm helper")
        self.assertEqual(profile["work_experience"], "3 years")
        self.assertEqual(profile["family_occupation"], "Farming")
        self.assertEqual(profile["aspirations"], "Own a tractor")
        self.assertEqual(profile["local_context"], "Rural village outside Indore")
        self.assertEqual(profile["constraints"], "None")
        self.assertEqual(len(profile["skills"]), 2)
        self.assertIn("Tractor operation", profile["skills"])
        self.assertEqual(profile["district"], "Indore")

    def test_save_and_retrieve_conversations(self):
        """Verifies saving voice/text conversation messages in order."""
        ben_id = create_beneficiary(name="Sunita Devi", district="Jaipur", db_path=self.temp_db_path)

        c1 = save_conversation(
            beneficiary_id=ben_id,
            sender="assistant",
            message_text="नमस्ते! आपकी क्या पढ़ाई हुई है?",
            input_mode="voice",
            db_path=self.temp_db_path
        )
        c2 = save_conversation(
            beneficiary_id=ben_id,
            sender="user",
            message_text="मैं 12वीं पास हूँ और मुझे बिजली वायरिंग का काम आता है।",
            input_mode="voice",
            db_path=self.temp_db_path
        )

        history = get_conversation_history(ben_id, self.temp_db_path)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["sender"], "assistant")
        self.assertEqual(history[1]["sender"], "user")
        self.assertIn("12वीं पास", history[1]["message_text"])

    def test_save_and_get_recommendations(self):
        """Verifies saving single and batch NSQF recommendations."""
        ben_id = create_beneficiary(name="Pooja Verma", district="Bhopal", db_path=self.temp_db_path)

        recs = [
            {
                "job_role": "Self Employed Tailor",
                "sector": "Apparel & Home Furnishing",
                "nsqf_level": 4,
                "total_score": 85.0,
                "skill_gap": {"matched_skills": ["Hand embroidery"], "missing_skills": ["Pattern drafting"]},
                "local_opportunity": "Bhopal SHG Cluster"
            },
            {
                "job_role": "Hand Embroiderer",
                "sector": "Handicrafts",
                "nsqf_level": 3,
                "total_score": 78.0,
                "skill_gap": {"matched_skills": ["Hand embroidery"], "missing_skills": []},
                "local_opportunity": "Bhopal Handicraft Kendra"
            }
        ]

        inserted_ids = save_recommendations_batch(ben_id, recs, self.temp_db_path)
        self.assertEqual(len(inserted_ids), 2)

        stored_recs = get_recommendations(ben_id, self.temp_db_path)
        self.assertEqual(len(stored_recs), 2)
        self.assertEqual(stored_recs[0]["rank_position"], 1)
        self.assertEqual(stored_recs[0]["job_role"], "Self Employed Tailor")
        self.assertEqual(stored_recs[0]["match_score"], 85.0)
        self.assertIn("Hand embroidery", stored_recs[0]["skill_gap"]["matched_skills"])

    def test_dashboard_statistics(self):
        """Verifies analytics computation for the dashboard."""
        # Create 2 beneficiaries with profiles and recommendations
        b1 = create_beneficiary("User One", district="Indore", db_path=self.temp_db_path)
        save_profile(b1, education="10th Pass", skills=["Farming"], district="Indore", employment_preference="Self-Employment", db_path=self.temp_db_path)
        save_recommendation(b1, "Tractor Operator", "Agriculture", 4, 82.0, rank_position=1, db_path=self.temp_db_path)

        b2 = create_beneficiary("User Two", district="Jaipur", db_path=self.temp_db_path)
        save_profile(b2, education="12th Pass", skills=["Solar"], district="Jaipur", employment_preference="Wage Employment", db_path=self.temp_db_path)
        save_recommendation(b2, "Solar PV Installer", "Green Jobs", 4, 76.0, rank_position=1, db_path=self.temp_db_path)

        stats = get_dashboard_statistics(self.temp_db_path)
        self.assertEqual(stats["total_beneficiaries"], 2)
        self.assertEqual(stats["total_profiles"], 2)
        self.assertEqual(stats["average_match_score"], 79.0)
        self.assertEqual(stats["self_employment_percentage"], 50.0)
        self.assertIn("Indore", stats["district_distribution"])
        self.assertIn("Agriculture", stats["sector_distribution"])
        self.assertEqual(len(stats["recent_beneficiaries"]), 2)

    def test_parameterized_query_safety(self):
        """Verifies SQL injection strings and apostrophes are safely escaped."""
        tricky_name = "O'Connor'; DROP TABLE beneficiaries; --"
        ben_id = create_beneficiary(name=tricky_name, district="Indore", db_path=self.temp_db_path)
        
        profile = get_profile(ben_id, self.temp_db_path)
        # Profile should be empty/created without SQL corruption
        stats = get_dashboard_statistics(self.temp_db_path)
        self.assertEqual(stats["total_beneficiaries"], 1)


if __name__ == "__main__":
    unittest.main()
