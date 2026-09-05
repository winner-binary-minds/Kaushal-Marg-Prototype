"""
Minimum end-to-end orchestration pipeline for Kaushal Marg.

Connects:
  ConversationManager → ProfileExtractor → recommend_jobs() → skill_gap + pathway
"""

import logging
from ai.conversation import ConversationManager
from ai.profile_extractor import ProfileExtractor
from recommendation.matcher import recommend_jobs
from recommendation.skill_gap import analyze_skill_gap
from recommendation.pathway import generate_skill_pathway

logger = logging.getLogger(__name__)


from database.database import save_assessment_transaction

class AssessmentPipeline:
    """
    Canonical pipeline for processing a verified profile, generating recommendations,
    and persisting results.
    """
    def __init__(self, db_path=None):
        self.db_path = db_path
        
    def process_verified_profile(self, profile_dict: dict, beneficiary_id: str, is_demo: bool = False) -> dict:
        """
        Executes the recommendation logic and gap analysis for a verified profile.
        If not in demo mode, saves the profile and recommendations to the database.
        """
        # 1. Generate recommendations
        recommendations = recommend_jobs(profile_dict, top_n=3)
        if not recommendations:
            # Still save profile even if no recommendations
            if not is_demo and beneficiary_id:
                save_assessment_transaction(beneficiary_id, profile_dict, [], db_path=self.db_path)
            return {
                "profile": profile_dict,
                "recommendations": [],
                "skill_gaps": {},
                "pathway": {}
            }
            
        # 2. Save profile and recommendations atomically if not demo
        if not is_demo and beneficiary_id:
            save_assessment_transaction(beneficiary_id, profile_dict, recommendations, db_path=self.db_path)
            
        # 4. Analyze skill gaps for top recommendation
        top_job = recommendations[0]
        skill_gaps = analyze_skill_gap(profile_dict, top_job)
        
        # 5. Generate pathway for top recommendation
        pathway = generate_skill_pathway(
            profile_dict,
            top_job,
            missing_skills=skill_gaps.get("missing_skills", [])
        )
        
        result = {
            "profile": profile_dict,
            "recommendations": recommendations,
            "skill_gaps": skill_gaps,
            "pathway": pathway
        }
        
        logger.info(f"Pipeline executed: {len(recommendations)} recommendations, pathway generated")
        return result


def run_recommendation_pipeline(conversation_manager: ConversationManager) -> dict:
    """
    Legacy wrapper for end-to-end extraction + pipeline.
    """
    history = conversation_manager.get_history()
    if not history:
        raise ValueError("No conversation history available")
    
    extractor = ProfileExtractor()
    profile = extractor.extract_profile(history)
    
    pipeline = AssessmentPipeline()
    # Using a dummy beneficiary ID since this is a legacy test wrapper
    return pipeline.process_verified_profile(profile, beneficiary_id="dummy", is_demo=True)

