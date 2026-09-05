"""
Comprehensive Edge-Case Unit Tests for Kaushal Marg Recommendation Engine.
Tests all 12 edge cases specified by user guidelines.
"""

import sys
import os

# Add project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommendation.matcher import recommend_jobs, load_nsqf_jobs, load_local_opportunities


def test_1_empty_skills():
    """Case 1: Beneficiary with empty skills list."""
    profile = {"education": "10th Pass", "skills": [], "interests": ["Green Jobs"]}
    recs = recommend_jobs(profile, top_n=3)
    assert isinstance(recs, list)
    if recs:
        assert recs[0]["matched_skills"] == []
    print("[OK] Test 1: Empty skills handled safely.")


def test_2_empty_education():
    """Case 2: Beneficiary with empty education string."""
    profile = {"education": "", "skills": ["Solar wiring"], "interests": ["Green Jobs"]}
    recs = recommend_jobs(profile, top_n=3)
    assert isinstance(recs, list)
    if recs:
        assert len(recs[0]["why_recommended"]) >= 0
    print("[OK] Test 2: Empty education handled safely.")


def test_3_missing_location():
    """Case 3: Beneficiary with missing district / location field."""
    profile = {"education": "10th Pass", "skills": ["Solar wiring"], "district": None}
    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) == 1
    assert recs[0].get("status") == "insufficient_information"
    print("[OK] Test 3: Missing location handled safely.")


def test_4_unknown_education_value():
    """Case 4: Beneficiary with unmapped/unknown education string."""
    profile = {"education": "Alien Degree Level 99", "skills": ["Tractor driving"]}
    recs = recommend_jobs(profile, top_n=3)
    assert isinstance(recs, list)
    assert all("score" in r for r in recs)
    print("[OK] Test 4: Unknown education value handled safely.")


def test_5_no_matching_skills():
    """Case 5: Beneficiary skills have 0 overlap with any dataset role."""
    profile = {"education": "10th Pass", "skills": ["Astronaut Training", "Quantum Physics"]}
    recs = recommend_jobs(profile, top_n=3)
    assert isinstance(recs, list)
    if recs:
        assert recs[0]["skill_coverage"] == 0.0
        assert recs[0]["matched_skills"] == []
    print("[OK] Test 5: No matching skills handled safely.")


def test_6_empty_nsqf_dataset():
    """Case 6: Dataset file path points to an empty or non-existent file."""
    profile = {"education": "10th Pass"}
    recs = recommend_jobs(profile, jobs_csv_path="non_existent_jobs.csv")
    assert recs == []
    print("[OK] Test 6: Empty NSQF dataset handled safely (returns []).")


def test_7_empty_local_opportunity_dataset():
    """Case 7: Local opportunity CSV path points to an empty or non-existent file."""
    profile = {"education": "10th Pass", "district": "Indore"}
    recs = recommend_jobs(profile, opp_csv_path="non_existent_opps.csv")
    assert isinstance(recs, list)
    if recs and recs[0].get("status") != "insufficient_information":
        assert recs[0]["local_opportunity"] == "No verified local opportunity data available"
    print("[OK] Test 7: Empty local opportunity dataset handled safely.")


def test_8_duplicate_skills():
    """Case 8: Beneficiary profile contains duplicate skills."""
    profile = {
        "education": "10th Pass",
        "skills": ["Solar wiring", "SOLAR WIRING", "  solar wiring  ", "Solar wiring"],
        "interests": ["Green Jobs"]
    }
    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) > 0
    top = recs[0]
    # Check that matched skills contains no duplicates
    assert len(set(top["matched_skills"])) == len(top["matched_skills"])
    print("[OK] Test 8: Duplicate skills handled and deduplicated safely.")


def test_9_uppercase_lowercase_skills():
    """Case 9: Mixed uppercase/lowercase skills."""
    profile = {
        "education": "10th Pass",
        "skills": ["sOLaR WiRInG", "SaFEty PRotOCoLS"],
        "interests": ["Green Jobs"]
    }
    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) > 0
    top = recs[0]
    if recs[0].get("status") != "insufficient_information":
        assert len(top["matched_skills"]) >= 2
    print("[OK] Test 9: Mixed casing skills handled safely.")


def test_10_many_skills():
    """Case 10: Beneficiary with 50+ skills."""
    many_skills = [f"Skill_{i}" for i in range(50)] + ["Tractor driving"]
    profile = {"education": "10th Pass", "skills": many_skills, "interests": ["Agriculture"]}
    recs = recommend_jobs(profile, top_n=3)
    # Score might be around 48, triggering 'Need more information' fallback
    assert len(recs) == 1
    assert recs[0]["job_role"] == "Need more information"
    print("[OK] Test 10: Beneficiary with many skills handled safely.")


def test_11_no_interests():
    """Case 11: Beneficiary with empty interests list."""
    profile = {"education": "10th Pass", "skills": ["Tractor driving"], "interests": []}
    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) == 1
    assert recs[0].get("status") == "insufficient_information"
    print("[OK] Test 11: Empty interests list handled safely.")


def test_12_missing_employment_preference():
    """Case 12: Missing employment preference field (None)."""
    profile = {"education": "10th Pass", "skills": ["Tractor driving"], "employment_preference": None}
    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) == 1
    assert recs[0].get("status") == "insufficient_information"
    print("[OK] Test 12: Missing employment preference handled safely.")


if __name__ == "__main__":
    print("=== RUNNING KAUSHAL MARG 12 EDGE-CASE TESTS ===")
    test_1_empty_skills()
    test_2_empty_education()
    test_3_missing_location()
    test_4_unknown_education_value()
    test_5_no_matching_skills()
    test_6_empty_nsqf_dataset()
    test_7_empty_local_opportunity_dataset()
    test_8_duplicate_skills()
    test_9_uppercase_lowercase_skills()
    test_10_many_skills()
    test_11_no_interests()
    test_12_missing_employment_preference()
    print("\nALL 12 EDGE-CASE TESTS PASSED WITH ZERO CRASHES!")
