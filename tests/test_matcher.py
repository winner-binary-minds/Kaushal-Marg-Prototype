"""
Unit tests for recommendation/matcher.py including local opportunity integration tests.
"""

import sys
import os

# Add parent project path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommendation.matcher import (
    recommend_jobs,
    load_nsqf_jobs,
    load_local_opportunities,
    find_local_opportunity_match
)


def test_load_nsqf_jobs_and_opportunities():
    """Verify that jobs and local opportunities datasets load properly."""
    jobs = load_nsqf_jobs()
    opportunities = load_local_opportunities()

    assert len(jobs) >= 20
    assert len(opportunities) >= 10
    print("[OK] test_load_nsqf_jobs_and_opportunities passed")


def test_matching_district_local_opportunity():
    """Test 1: Beneficiary in a district with matching local opportunities (Indore)."""
    profile = {
        "education": "10th Pass",
        "skills": ["tractor operation"],
        "interests": ["Agriculture"],
        "mobility": "Low",
        "district": "Indore"
    }

    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) == 3

    top = recs[0]
    assert top["job_role"] == "Tractor Operator"
    assert "available in Indore" in top["local_opportunity"]
    assert top["local_opportunity_details"] is not None
    assert top["local_opportunity_details"]["district"] == "Indore"
    assert top["local_opportunity_details"]["data_source_type"] == "Prototype Demo Data"
    print(f"[OK] test_matching_district_local_opportunity passed (District: Indore, Role: {top['job_role']})")


def test_no_matching_district_local_opportunity():
    """Test 2: Beneficiary in a district with NO local opportunities in dataset."""
    profile = {
        "education": "10th Pass",
        "skills": ["tractor operation"],
        "interests": ["Agriculture"],
        "mobility": "Low",
        "district": "UnknownRemoteDistrict"
    }

    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) == 3

    for r in recs:
        assert r["local_opportunity"] == "No verified local opportunity data available"
        assert r["local_opportunity_details"] is None

    # Score should be 10 points lower (73 instead of 83)
    top = recs[0]
    assert top["score"] == 73
    print("[OK] test_no_matching_district_local_opportunity passed (Fallback handling verified)")


def test_missing_location_field():
    """Test 3: Beneficiary profile with missing or empty district/location field."""
    profile = {
        "education": "10th Pass",
        "skills": ["Solar wiring"],
        "interests": ["Green Jobs"],
        "mobility": "District",
        "district": ""  # Missing location
    }

    recs = recommend_jobs(profile, top_n=3)
    assert len(recs) == 3

    top = recs[0]
    assert top["local_opportunity"] == "No verified local opportunity data available"
    assert top["local_opportunity_details"] is None
    print("[OK] test_missing_location_field passed")


def test_empty_opportunity_dataset():
    """Test 4: System behavior when local_opportunities CSV dataset is empty/missing."""
    profile = {
        "education": "10th Pass",
        "skills": ["Solar wiring"],
        "interests": ["Green Jobs"],
        "district": "Jaipur"
    }

    # Pass non-existent path for opportunity CSV
    recs = recommend_jobs(profile, top_n=3, opp_csv_path="non_existent_opps.csv")
    assert len(recs) == 3

    for r in recs:
        assert r["local_opportunity"] == "No verified local opportunity data available"
        assert r["local_opportunity_details"] is None

    print("[OK] test_empty_opportunity_dataset passed")


if __name__ == "__main__":
    print("=== RUNNING MATCHER & LOCAL OPPORTUNITY UNIT TESTS ===")
    test_load_nsqf_jobs_and_opportunities()
    test_matching_district_local_opportunity()
    test_no_matching_district_local_opportunity()
    test_missing_location_field()
    test_empty_opportunity_dataset()
    print("\nALL MATCHER & LOCAL OPPORTUNITY TESTS PASSED SUCCESSFULLY!")
