"""
Unit tests for recommendation/pathway.py ("My Skill Journey" feature).
"""

import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommendation.pathway import generate_skill_pathway


def test_generate_skill_pathway_user_example():
    """Test skill pathway generation using the exact user-provided scenario."""
    profile = {
        "education": "10th Pass",
        "occupation": "Farming",
        "skills": ["basic farming"]
    }

    job_role = {
        "job_role": "Solar PV Installer (Suryamitra)",
        "sector": "Green Jobs",
        "nsqf_level": 4,
        "required_skills": "Basic electrical knowledge|Safety|Solar fundamentals"
    }

    missing_skills = ["Basic electrical knowledge", "Safety", "Solar fundamentals"]

    pathway = generate_skill_pathway(profile, job_role, missing_skills)

    assert "10th Pass" in pathway["current_state"]
    assert "basic farming" in pathway["current_state"]
    assert pathway["foundation_skills"] == ["basic farming"]
    assert pathway["skills_to_build"] == missing_skills
    assert len(pathway["training_stage"]["learning_modules"]) == 3
    assert len(pathway["practical_stage"]["practical_tasks"]) == 3
    assert pathway["target_role"]["role"] == "Solar PV Installer (Suryamitra)"
    assert pathway["target_role"]["sector"] == "Green Jobs"
    assert pathway["target_role"]["nsqf_level"] == "Level 4"

    print("[OK] test_generate_skill_pathway_user_example passed")


def test_generate_skill_pathway_full_match():
    """Test pathway generation when candidate already possesses all required skills."""
    profile = {
        "education": "8th Pass",
        "skills": ["Tractor driving", "Implement hitching", "Routine maintenance"]
    }

    job_role = {
        "job_role": "Tractor Operator",
        "sector": "Agriculture",
        "nsqf_level": 4,
        "required_skills": "Tractor driving|Implement hitching|Routine maintenance"
    }

    pathway = generate_skill_pathway(profile, job_role, missing_skills=[])

    assert pathway["skills_to_build"] == []
    assert len(pathway["foundation_skills"]) == 3
    assert "Advanced" in pathway["training_stage"]["learning_modules"][0]
    assert pathway["target_role"]["role"] == "Tractor Operator"

    print("[OK] test_generate_skill_pathway_full_match passed")


def test_generate_skill_pathway_empty_profile():
    """Safety test: Empty profile should generate a valid fallback pathway."""
    profile = {}
    job_role = {"job_role": "Mason General", "sector": "Construction", "nsqf_level": 3}

    pathway = generate_skill_pathway(profile, job_role)

    assert "current_state" in pathway
    assert "foundation_skills" in pathway
    assert pathway["target_role"]["role"] == "Mason General"

    print("[OK] test_generate_skill_pathway_empty_profile passed")


if __name__ == "__main__":
    print("=== RUNNING SKILL PATHWAY UNIT TESTS ===")
    test_generate_skill_pathway_user_example()
    test_generate_skill_pathway_full_match()
    test_generate_skill_pathway_empty_profile()
    print("\nALL SKILL PATHWAY UNIT TESTS PASSED SUCCESSFULLY!")
