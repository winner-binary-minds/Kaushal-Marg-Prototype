"""
Unit tests for recommendation/scoring.py module.
"""

import sys
import os

# Add project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommendation.scoring import (
    calculate_education_score,
    calculate_skill_score,
    calculate_interest_score,
    calculate_mobility_score,
    calculate_employment_preference_score,
    calculate_local_opportunity_score,
    calculate_total_score
)


def test_education_score_calculation():
    """Verify education score ranks and boundary conditions."""
    res_full = calculate_education_score("10th Pass", "8th Pass")
    assert res_full["score"] == 20

    res_exact = calculate_education_score("10th Pass", "10th Pass")
    assert res_exact["score"] == 20

    res_below = calculate_education_score("8th Pass", "10th Pass")
    assert res_below["score"] == 10  # 1 rank below -> partial

    res_far_below = calculate_education_score("5th Pass", "10th Pass")
    assert res_far_below["score"] == 0
    print("[OK] test_education_score_calculation passed")


def test_skill_score_calculation():
    """Verify skill score calculation out of max 25 points."""
    res_full = calculate_skill_score(["Solar wiring", "Safety protocols"], "", "", "Solar wiring|Safety protocols", "", "")
    assert res_full["score"] == 25

    res_half = calculate_skill_score(["Solar wiring"], "", "", "Solar wiring|PV module installation", "", "")
    assert res_half["score"] in [12, 13]  # (1/2)*25 = 12.5 -> 12 or 13 depending on rounding
    print("[OK] test_skill_score_calculation passed")


def test_interest_score_calculation():
    """Verify interest score calculation out of max 20 points."""
    res_match = calculate_interest_score(["Green Jobs"], "", "", "Green Jobs")
    assert res_match["score"] == 20

    res_no_match = calculate_interest_score(["Apparel"], "", "", "Green Jobs")
    assert res_no_match["score"] == 0

    res_empty = calculate_interest_score([], "", "", "Green Jobs")
    assert res_empty["score"] == 0  # Changed to 0 since unknown should not award points
    print("[OK] test_interest_score_calculation passed")


def test_mobility_score_calculation():
    """Verify mobility score calculation out of max 15 points."""
    res_match = calculate_mobility_score("District Level", "Local / District")
    assert res_match["score"] == 15

    res_strict = calculate_mobility_score("Local Only", "State Wide")
    assert res_strict["score"] == 0
    print("[OK] test_mobility_score_calculation passed")


def test_employment_preference_score_calculation():
    """Verify employment preference score calculation out of max 10 points."""
    res_self = calculate_employment_preference_score("Self-Employment", self_emp_suitability="High", wage_emp_suitability="Low")
    assert res_self["score"] == 10

    res_wage = calculate_employment_preference_score("Wage-Employment", self_emp_suitability="High", wage_emp_suitability="Medium")
    assert res_wage["score"] == 6

    res_any = calculate_employment_preference_score("Any", self_emp_suitability="High", wage_emp_suitability="Low")
    assert res_any["score"] == 0 # Changed to 0 because "any" preference is now penalized for lack of explicit match
    print("[OK] test_employment_preference_score_calculation passed")


def test_local_opportunity_score_calculation():
    """Verify local opportunity score calculation out of max 10 points."""
    res_valid = calculate_local_opportunity_score(has_local_opportunity=True, district_match=True, is_exact=True)
    assert res_valid["score"] == 10

    res_invalid = calculate_local_opportunity_score(has_local_opportunity=False)
    assert res_invalid["score"] == 0
    print("[OK] test_local_opportunity_score_calculation passed")


def test_calculate_total_score_sum_to_100():
    """Verify master scoring engine sums component weights to 100 max."""
    profile = {
        "education": "10th Pass",
        "skills": ["Solar wiring", "PV module installation"],
        "interests": ["Green Jobs"],
        "mobility": "District Level",
        "employment_preference": "Wage-Employment"
    }

    job = {
        "job_role": "Solar PV Installer (Suryamitra)",
        "sector": "Green Jobs",
        "minimum_education": "10th Pass",
        "required_skills": "Solar wiring|PV module installation",
        "mobility_requirement": "District",
        "self_employment_suitability": "Medium",
        "wage_employment_suitability": "High"
    }

    res = calculate_total_score(profile, job, has_local_opportunity=True, is_exact_opportunity=True)
    assert res["max_total_score"] == 100
    assert res["total_score"] == 100  # Perfect match scenario
    print("[OK] test_calculate_total_score_sum_to_100 passed (Max 100 score verified)")


if __name__ == "__main__":
    print("=== RUNNING SCORING MODULE UNIT TESTS ===")
    test_education_score_calculation()
    test_skill_score_calculation()
    test_interest_score_calculation()
    test_mobility_score_calculation()
    test_employment_preference_score_calculation()
    test_local_opportunity_score_calculation()
    test_calculate_total_score_sum_to_100()
    print("\nALL SCORING MODULE TESTS PASSED SUCCESSFULLY!")
