"""
Master Test Runner for Kaushal Marg Recommendation Module.

Executes test suites across all 4 core recommendation files:
1. scoring.py    -> tests/test_scoring.py
2. skill_gap.py  -> tests/test_skill_gap.py
3. pathway.py    -> tests/test_pathway.py
4. matcher.py    -> tests/test_matcher.py & tests/test_edge_cases.py
"""

import sys
import os

# Add project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import test_scoring as t_scoring
import test_skill_gap as t_skill_gap
import test_pathway as t_pathway
import test_matcher as t_matcher
import test_edge_cases as t_edge


def run_all():
    print("==================================================")
    print("   KAUSHAL MARG: MASTER TEST SUITE EXECUTION")
    print("==================================================\n")

    print("--- 1. SCORING ENGINE TESTS (scoring.py) ---")
    t_scoring.test_education_score_calculation()
    t_scoring.test_skill_score_calculation()
    t_scoring.test_interest_score_calculation()
    t_scoring.test_mobility_score_calculation()
    t_scoring.test_employment_preference_score_calculation()
    t_scoring.test_local_opportunity_score_calculation()
    t_scoring.test_calculate_total_score_sum_to_100()
    print(">>> scoring.py: All tests PASSED!\n")

    print("--- 2. SKILL GAP TESTS (skill_gap.py) ---")
    t_skill_gap.test_normalize_skill_casing_and_spaces()
    t_skill_gap.test_match_skills_full_overlap()
    t_skill_gap.test_match_skills_partial_overlap()
    t_skill_gap.test_analyze_skill_gap_user_example()
    print(">>> skill_gap.py: All tests PASSED!\n")

    print("--- 3. SKILL PATHWAY TESTS (pathway.py) ---")
    t_pathway.test_generate_skill_pathway_user_example()
    t_pathway.test_generate_skill_pathway_full_match()
    t_pathway.test_generate_skill_pathway_empty_profile()
    print(">>> pathway.py: All tests PASSED!\n")

    print("--- 4. MATCHER & LOCAL OPPORTUNITY TESTS (matcher.py) ---")
    t_matcher.test_load_nsqf_jobs_and_opportunities()
    t_matcher.test_matching_district_local_opportunity()
    t_matcher.test_no_matching_district_local_opportunity()
    t_matcher.test_missing_location_field()
    t_matcher.test_empty_opportunity_dataset()
    print(">>> matcher.py: All core tests PASSED!\n")

    print("--- 5. COMPREHENSIVE EDGE-CASE TESTS ---")
    t_edge.test_1_empty_skills()
    t_edge.test_2_empty_education()
    t_edge.test_3_missing_location()
    t_edge.test_4_unknown_education_value()
    t_edge.test_5_no_matching_skills()
    t_edge.test_6_empty_nsqf_dataset()
    t_edge.test_7_empty_local_opportunity_dataset()
    t_edge.test_8_duplicate_skills()
    t_edge.test_9_uppercase_lowercase_skills()
    t_edge.test_10_many_skills()
    t_edge.test_11_no_interests()
    t_edge.test_12_missing_employment_preference()
    print(">>> Edge Cases: All 12 edge cases PASSED!\n")

    print("==================================================")
    print("   SUMMARY: 100% OF RECOMMENDATION TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_all()
