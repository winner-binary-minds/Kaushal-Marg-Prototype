"""
Unit tests for skill matching and skill gap analysis in Kaushal Marg.
"""

import sys
import os

# Add parent project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommendation.scoring import normalize_skill, match_skills
from recommendation.skill_gap import analyze_skill_gap


def test_normalize_skill_casing_and_spaces():
    """Test that uppercase letters and extra spaces are cleaned properly."""
    assert normalize_skill("  SOLAR   wiring  ") == "solar wiring"
    assert normalize_skill("Safety Protocols") == "safety protocols"
    assert normalize_skill("") == ""
    assert normalize_skill(None) == ""
    print("[OK] test_normalize_skill_casing_and_spaces passed")


def test_match_skills_full_overlap():
    """Test when beneficiary possesses all required skills."""
    b_skills = ["Solar wiring", "PV module installation", "Battery maintenance"]
    r_skills = "solar wiring|pv module installation|battery maintenance"

    res = match_skills(b_skills, r_skills)
    assert res["score"] == 25
    assert res["coverage_percentage"] == 100.0
    assert len(res["matched_skills"]) == 3
    assert len(res["missing_skills"]) == 0
    print("[OK] test_match_skills_full_overlap passed")


def test_match_skills_partial_overlap():
    """Test partial skill coverage and missing skill detection."""
    b_skills = ["Solar wiring"]
    r_skills = ["Solar wiring", "PV module installation", "Battery maintenance", "Safety protocols"]

    res = match_skills(b_skills, r_skills)
    assert res["score"] == 6  # (1/4)*25 = 6.25 -> 6
    assert res["coverage_percentage"] == 25.0
    assert len(res["matched_skills"]) == 1
    assert len(res["missing_skills"]) == 3
    assert "PV module installation" in res["missing_skills"]
    print("[OK] test_match_skills_partial_overlap passed")


def test_analyze_skill_gap_user_example():
    """Test analyze_skill_gap using the exact user-provided scenario."""
    beneficiary = {
        "skills": ["basic wiring", "repair"]
    }
    job = {
        "job_role": "Assistant Electrician",
        "required_skills": ["basic wiring", "electrical safety", "testing"]
    }

    result = analyze_skill_gap(beneficiary, job)

    assert result["matched_skills"] == ["basic wiring"]
    assert set(result["missing_skills"]) == {"electrical safety", "testing"}
    assert result["skill_coverage_percentage"] == 33.33
    assert "training recommended" in result["summary"].lower()
    print("[OK] test_analyze_skill_gap_user_example passed (33.33% coverage)")


if __name__ == "__main__":
    print("=== RUNNING SKILL GAP UNIT TESTS ===")
    test_normalize_skill_casing_and_spaces()
    test_match_skills_full_overlap()
    test_match_skills_partial_overlap()
    test_analyze_skill_gap_user_example()
    print("\nALL SKILL GAP UNIT TESTS PASSED SUCCESSFULLY!")
