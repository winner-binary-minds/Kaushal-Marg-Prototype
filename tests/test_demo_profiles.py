"""
Unit Tests for Kaushal Marg 10 Synthetic Demo Beneficiary Profiles
Tests recommendation matching, skill gap evaluation, pathway generation,
and SQLite persistence for all 10 profiles.

Team: Binary Minds | SIH Problem Statement 26097
"""

import unittest
import tempfile
import os
from data.demo_profiles import SYNTHETIC_BENEFICIARY_PROFILES, get_demo_profile_by_id
from recommendation.matcher import recommend_jobs
from recommendation.pathway import generate_skill_pathway
from database.database import (
    init_db,
    create_beneficiary,
    save_profile,
    get_profile,
    save_recommendations_batch,
    get_recommendations,
    get_filtered_dashboard_data
)


class TestSyntheticDemoProfiles(unittest.TestCase):
    """Test suite for the 10 fictional demonstration profiles."""

    def test_all_10_profiles_exist(self):
        """Verifies exactly 10 synthetic profiles covering the target domains."""
        self.assertEqual(len(SYNTHETIC_BENEFICIARY_PROFILES), 10)
        
        # Verify coverage tags
        domains = [p["domain_tag"] for p in SYNTHETIC_BENEFICIARY_PROFILES]
        self.assertTrue(any("Agri" in d for d in domains))
        self.assertTrue(any("Elec" in d for d in domains))
        self.assertTrue(any("Tail" in d for d in domains))
        self.assertTrue(any("Cons" in d for d in domains))
        self.assertTrue(any("Retail" in d for d in domains))
        self.assertTrue(any("Food" in d for d in domains))
        self.assertTrue(any("Auto" in d for d in domains))

        # Verify employment preferences
        prefs = [p["employment_preference"] for p in SYNTHETIC_BENEFICIARY_PROFILES]
        self.assertIn("Self-Employment", prefs)
        self.assertIn("Wage-Employment", prefs)

        # Verify low mobility coverage
        mobilities = [p["mobility"] for p in SYNTHETIC_BENEFICIARY_PROFILES]
        self.assertTrue(all("Low" in m or "Moderate" in m for m in mobilities))

    def test_recommendations_for_each_demo_profile(self):
        """Tests that each of the 10 profiles receives valid top-3 NSQF recommendations."""
        for p in SYNTHETIC_BENEFICIARY_PROFILES:
            recs = recommend_jobs(p, top_n=3)
            self.assertEqual(len(recs), 3, f"Profile {p['id']} ({p['name']}) did not receive 3 recommendations.")
            
            top_rec = recs[0]
            self.assertGreaterEqual(top_rec["score"], 50.0, f"Profile {p['id']} top score too low: {top_rec['score']}")
            self.assertTrue(top_rec["job_role"])
            self.assertTrue(top_rec["sector"])
            self.assertIsInstance(top_rec["matched_skills"], list)
            self.assertIsInstance(top_rec["missing_skills"], list)

            # Test Pathway generation for top role
            pathway = generate_skill_pathway(
                beneficiary_profile=p,
                recommended_job_role={"job_role": top_rec["job_role"], "sector": top_rec["sector"], "nsqf_level": 4},
                missing_skills=top_rec["missing_skills"]
            )
            self.assertIsNotNone(pathway)
            self.assertIn("current_state", pathway)
            self.assertIn("training_stage", pathway)
            self.assertIn("practical_stage", pathway)

    def test_database_persistence_for_all_10_profiles(self):
        """Verifies storing and retrieving all 10 profiles in a clean SQLite database."""
        fd, temp_db = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            init_db(temp_db)
            for p in SYNTHETIC_BENEFICIARY_PROFILES:
                b_id = create_beneficiary(
                    name=p["name"],
                    preferred_language="hi",
                    district=p["district"],
                    db_path=temp_db
                )
                self.assertTrue(b_id.startswith("KM-"))

                prof_id = save_profile(
                    beneficiary_id=b_id,
                    education=p["education"],
                    skills=p["skills"],
                    interests=p["interests"],
                    district=p["district"],
                    mobility=p["mobility"],
                    employment_preference=p["employment_preference"],
                    db_path=temp_db
                )
                self.assertIsInstance(prof_id, int)

                # Generate and save recommendations
                recs = recommend_jobs(p, top_n=3)
                batch_ids = save_recommendations_batch(b_id, recs, db_path=temp_db)
                self.assertEqual(len(batch_ids), 3)

                stored_profile = get_profile(b_id, db_path=temp_db)
                self.assertEqual(stored_profile["education"], p["education"])
                self.assertEqual(len(stored_profile["skills"]), len(p["skills"]))

            # Verify aggregated dashboard metrics on the 10 profiles
            dash_data = get_filtered_dashboard_data(db_path=temp_db)
            self.assertEqual(dash_data["total_beneficiaries"], 10)
            self.assertGreater(dash_data["average_match_score"], 60.0)
            self.assertGreater(len(dash_data["sector_distribution"]), 3)
            self.assertEqual(len(dash_data["records"]), 10)

        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except PermissionError:
                    pass


if __name__ == "__main__":
    unittest.main()
