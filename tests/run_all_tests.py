"""
Master Test Runner for Kaushal Marg Platform.

Executes test suites across all components:
1. database.py              -> tests/test_database.py
2. demo_profiles.py         -> tests/test_demo_profiles.py
3. test_voice_workflow.py   -> tests/test_voice_workflow.py
4. test_full_integration.py -> tests/test_full_integration.py
5. scoring.py               -> tests/test_scoring.py
6. skill_gap.py             -> tests/test_skill_gap.py
7. pathway.py               -> tests/test_pathway.py
9. test_conversation_ui.py  -> tests/test_conversation_ui.py
10. test_profile_extraction.py -> tests/test_profile_extraction.py
11. test_database_error_handling.py -> tests/test_database_error_handling.py
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
import test_full_integration as t_integration
import test_voice_workflow as t_voice
import test_conversation_ui as t_conv_ui
import test_profile_extraction as t_prof_ext
import test_database_error_handling as t_db_err
import test_explanation as t_expl
import test_user_journey as t_journey


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

    print("--- 1.5. DATABASE ERROR HANDLING TESTS (test_database_error_handling.py) ---")
    suite1_5 = unittest.TestLoader().loadTestsFromModule(t_db_err)
    res1_5 = runner.run(suite1_5)
    if not res1_5.wasSuccessful():
        print("[FAIL] Database Error Handling tests failed!")
        sys.exit(1)
    print(">>> test_database_error_handling.py: All Database Error tests PASSED!\n")

    print("--- 2. SYNTHETIC DEMO PROFILES TESTS (data/demo_profiles.py) ---")
    suite2 = unittest.TestLoader().loadTestsFromModule(t_demo)
    res2 = runner.run(suite2)
    if not res2.wasSuccessful():
        print("[FAIL] Demo profile tests failed!")
        sys.exit(1)
    print(">>> demo_profiles.py: All 10 profiles verified & PASSED!\n")

    print("--- 3. REAL VOICE & AUDIO WORKFLOW TESTS (voice/audio.py) ---")
    suite3 = unittest.TestLoader().loadTestsFromModule(t_voice)
    res3 = runner.run(suite3)
    if not res3.wasSuccessful():
        print("[FAIL] Voice workflow tests failed!")
        sys.exit(1)
    print(">>> voice/audio.py: Real voice transcription & error handling tests PASSED!\n")

    print("--- 4. FULL SYSTEM INTEGRATION TESTS (AI + Voice + Rec Engine + SQLite) ---")
    suite4 = unittest.TestLoader().loadTestsFromModule(t_integration)
    res4 = runner.run(suite4)
    if not res4.wasSuccessful():
        print("[FAIL] Full system integration tests failed!")
        sys.exit(1)
    print(">>> Full System Integration: All 17-step flow tests PASSED!\n")

    print("--- 4.1. REAL USER JOURNEY INTEGRATION TESTS (test_user_journey.py) ---")
    suite4_1 = unittest.TestLoader().loadTestsFromModule(t_journey)
    res4_1 = runner.run(suite4_1)
    if not res4_1.wasSuccessful():
        print("[FAIL] Real User Journey tests failed!")
        sys.exit(1)
    print(">>> test_user_journey.py: All 5 Scenarios PASSED!\n")

    print("--- 4.5. UI CONVERSATION MANAGER INTEGRATION TESTS (test_conversation_ui.py) ---")
    suite4_5 = unittest.TestLoader().loadTestsFromModule(t_conv_ui)
    res4_5 = runner.run(suite4_5)
    if not res4_5.wasSuccessful():
        print("[FAIL] UI Conversation Manager tests failed!")
        sys.exit(1)
    print(">>> test_conversation_ui.py: All Conversation UI tests PASSED!\n")

    print("--- 4.6. AI PROFILE EXTRACTION TESTS (test_profile_extraction.py) ---")
    suite4_6 = unittest.TestLoader().loadTestsFromModule(t_prof_ext)
    res4_6 = runner.run(suite4_6)
    if not res4_6.wasSuccessful():
        print("[FAIL] AI Profile Extraction tests failed!")
        sys.exit(1)
    print(">>> test_profile_extraction.py: All Profile Extraction tests PASSED!\n")

    print("--- 4.7. AI EXPLANATION TESTS (test_explanation.py) ---")
    suite4_7 = unittest.TestLoader().loadTestsFromModule(t_expl)
    res4_7 = runner.run(suite4_7)
    if not res4_7.wasSuccessful():
        print("[FAIL] AI Explanation tests failed!")
        sys.exit(1)
    print(">>> test_explanation.py: All Explanation tests PASSED!\n")

    print("--- 5. SCORING ENGINE TESTS (scoring.py) ---")
    t_scoring.test_education_score_calculation()
    t_scoring.test_skill_score_calculation()
    t_scoring.test_interest_score_calculation()
    t_scoring.test_mobility_score_calculation()
    t_scoring.test_employment_preference_score_calculation()
    t_scoring.test_local_opportunity_score_calculation()
    t_scoring.test_calculate_total_score_sum_to_100()
    print(">>> scoring.py: All tests PASSED!\n")

    print("--- 6. SKILL GAP TESTS (skill_gap.py) ---")
    t_skill_gap.test_normalize_skill_casing_and_spaces()
    t_skill_gap.test_match_skills_full_overlap()
    t_skill_gap.test_match_skills_partial_overlap()
    t_skill_gap.test_analyze_skill_gap_user_example()
    print(">>> skill_gap.py: All tests PASSED!\n")

    print("--- 7. SKILL PATHWAY TESTS (pathway.py) ---")
    t_pathway.test_generate_skill_pathway_user_example()
    t_pathway.test_generate_skill_pathway_full_match()
    t_pathway.test_generate_skill_pathway_empty_profile()
    print(">>> pathway.py: All tests PASSED!\n")

    print("--- 8. MATCHER & LOCAL OPPORTUNITY TESTS (matcher.py) ---")
    t_matcher.test_load_nsqf_jobs_and_opportunities()
    t_matcher.test_matching_district_local_opportunity()
    t_matcher.test_no_matching_district_local_opportunity()
    t_matcher.test_missing_location_field()
    t_matcher.test_empty_opportunity_dataset()
    print(">>> matcher.py: All core tests PASSED!\n")

    print("--- 9. COMPREHENSIVE EDGE-CASE TESTS ---")
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
