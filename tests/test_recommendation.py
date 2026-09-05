import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommendation.matcher import recommend_jobs
from recommendation.scoring import (
    calculate_education_score,
    calculate_skill_score,
    calculate_interest_score,
    calculate_total_score
)

class TestRecommendationAdversarial(unittest.TestCase):
    
    def test_empty_profile_rejection(self):
        """An empty profile should get very low scores and be rejected (score < 45)."""
        empty_profile = {}
        recs = recommend_jobs(empty_profile, top_n=3)
        self.assertEqual(len(recs), 1, "Empty profile should yield 1 fallback recommendation due to threshold.")
        self.assertEqual(recs[0].get("status"), "insufficient_information")

    def test_unrelated_skills_rejection(self):
        """A profile with completely unrelated skills should score poorly."""
        profile = {
            "skills": ["cooking", "baking"],
            "education": "8th Pass",
            "interests": ["food"],
            "district": "Unknown"
        }
        recs = recommend_jobs(profile, top_n=3)
        # Even if education matches a low-level job, skill score will be 0, interest 0. 
        # Max expected score: Edu (20) + Mob (15) + Emp (6) = 41 < 45.
        self.assertEqual(len(recs), 1, "Profile with unrelated skills should fallback to no_strong_match.")
        self.assertEqual(recs[0].get("status"), "no_strong_match")

    def test_insufficient_education(self):
        """Test education scoring for insufficient education."""
        res = calculate_education_score("5th Pass", "12th Pass")
        self.assertEqual(res["score"], 0)
        
    def test_skill_substring_exploit_prevented(self):
        """Ensure 'car' doesn't match 'carpentry'."""
        res = calculate_skill_score(["car"], "", "", "carpentry", "", "")
        self.assertEqual(res["score"], 0)

    def test_print_adversarial_table(self):
        """Print a test table showing Profile -> Top Roles -> Scores -> Reasons."""
        print("\n" + "="*80)
        print(" ADVERSARIAL TEST TABLE: RECOMMENDATION ENGINE")
        print("="*80)
        
        test_cases = [
            ("Empty Profile", {}),
            ("Unrelated Skills (Cook)", {"skills": ["cooking", "baking"], "education": "10th"}),
            ("Partial Match (Helper)", {"skills": ["wiring"], "education": "8th Pass"}),
            ("Very High Match (Electrician)", {"skills": ["solar", "wiring", "electrical"], "education": "12th Pass", "interests": ["green energy"], "district": "Jaipur"})
        ]
        
        for name, profile in test_cases:
            recs = recommend_jobs(profile, top_n=3)
            print(f"\n[Profile: {name}]")
            if not recs:
                print("  -> REJECTED: No jobs met the minimum confidence threshold of 45.")
            else:
                for i, r in enumerate(recs):
                    print(f"  {i+1}. {r['job_role']} (Score: {r['score']})")
                    print(f"     Edu: {r.get('score_breakdown', {}).get('education', {}).get('score', 0)} | "
                          f"Skill: {r.get('score_breakdown', {}).get('skill', {}).get('score', 0)} | "
                          f"Int: {r.get('score_breakdown', {}).get('interest', {}).get('score', 0)} | "
                          f"Opp: {r.get('score_breakdown', {}).get('local_opportunity', {}).get('score', 0)}")
                    for reason in r["why_recommended"][:2]:
                        print(f"     - {reason}")
        print("="*80 + "\n")


if __name__ == "__main__":
    unittest.main()
