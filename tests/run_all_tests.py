"""
Master Test Runner for Kaushal Marg Platform.

Executes test suites across all components:
1. database.py           -> tests/test_database.py
2. demo_profiles.py      -> tests/test_demo_profiles.py
3. scoring.py            -> tests/test_scoring.py
4. skill_gap.py          -> tests/test_skill_gap.py
5. pathway.py            -> tests/test_pathway.py
6. matcher.py            -> tests/test_matcher.py & tests/test_edge_cases.py
"""

import sys
import os
import unittest

# Add project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import test_scoring as t_scoring
import test_skill_gap as t_skill_gap
import test_pathway as t_pathway
import test_matcher as t_matcher
import test_edge_cases as t_edge
import test_database as t_database
import test_demo_profiles as t_demo


def run_all():
    print("==================================================")
    print("   KAUSHAL MARG: MASTER TEST SUITE EXECUTION")
    print("==================================================\n")

    print("--- 1. DATABASE TESTS (database/database.py) ---")
    suite1 = unittest.TestLoader().loadTestsFromModule(t_database)
    runner = unittest.TextTestRunner(verbosity=1)
    res1 = runner.run(suite1)
    if not res1.wasSuccessful():
        print("[FAIL] Database tests failed!")
        sys.exit(1)
    print(">>> database.py: All tests PASSED!\n")

    print("--- 2. SYNTHETIC DEMO PROFILES TESTS (data/demo_profiles.py) ---")
    suite2 = unittest.TestLoader().loadTestsFromModule(t_demo)
    res2 = runner.run(suite2)
    if not res2.wasSuccessful():
        print("[FAIL] Demo profile tests failed!")
        sys.exit(1)
    print(">>> demo_profiles.py: All 10 profiles verified & PASSED!\n")

    print("--- 3. SCORING ENGINE TESTS (scoring.py) ---")
    t_scoring.test_education_score_calculation()
    t_scoring.test_skill_score_calculation()
    t_scoring.test_interest_score_calculation()
    t_scoring.test_mobility_score_calculation()
    t_scoring.test_employment_preference_score_calculation()
    t_scoring.test_local_opportunity_score_calculation()
    t_scoring.test_calculate_total_score_sum_to_100()
    print(">>> scoring.py: All tests PASSED!\n")

    print("--- 4. SKILL GAP TESTS (skill_gap.py) ---")
    t_skill_gap.test_normalize_skill_casing_and_spaces()
    t_skill_gap.test_match_skills_full_overlap()
    t_skill_gap.test_match_skills_partial_overlap()
    t_skill_gap.test_analyze_skill_gap_user_example()
    print(">>> skill_gap.py: All tests PASSED!\n")

    print("--- 5. SKILL PATHWAY TESTS (pathway.py) ---")
    t_pathway.test_generate_skill_pathway_user_example()
    t_pathway.test_generate_skill_pathway_full_match()
    t_pathway.test_generate_skill_pathway_empty_profile()
    print(">>> pathway.py: All tests PASSED!\n")

    print("--- 6. MATCHER & LOCAL OPPORTUNITY TESTS (matcher.py) ---")
    t_matcher.test_load_nsqf_jobs_and_opportunities()
    t_matcher.test_matching_district_local_opportunity()
    t_matcher.test_no_matching_district_local_opportunity()
    t_matcher.test_missing_location_field()
    t_matcher.test_empty_opportunity_dataset()
    print(">>> matcher.py: All core tests PASSED!\n")

    print("--- 7. COMPREHENSIVE EDGE-CASE TESTS ---")
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
    print("   SUMMARY: 100% OF ALL MASTER TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_all()
