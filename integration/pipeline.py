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


def run_recommendation_pipeline(conversation_manager: ConversationManager) -> dict:
    """
    Execute the full recommendation pipeline.
    
    Flow:
    1. Extract profile from conversation history
    2. Generate job recommendations
    3. Analyze skill gaps for top recommendation
    4. Generate skill pathway for top recommendation
    
    Args:
        conversation_manager: ConversationManager with active conversation
    
    Returns:
        dict with keys:
        - profile: Extracted beneficiary profile (dict)
        - recommendations: List of recommended jobs (list[dict])
        - skill_gaps: Skill gap analysis for top recommendation (dict)
        - pathway: Skill pathway for top recommendation (dict)
    
    Raises:
        ValueError: If history is empty or profile extraction fails
    """
    # Get conversation history
    history = conversation_manager.get_history()
    if not history:
        raise ValueError("No conversation history available")
    
    # Extract beneficiary profile
    extractor = ProfileExtractor()
    profile = extractor.extract_profile(history)
    
    # Generate recommendations
    recommendations = recommend_jobs(profile, top_n=3)
    if not recommendations:
        raise ValueError("No job recommendations could be generated")
    
    # Analyze skill gaps for top recommendation
    top_job = recommendations[0]
    skill_gaps = analyze_skill_gap(profile, top_job)
    
    # Generate pathway for top recommendation
    pathway = generate_skill_pathway(
        profile,
        top_job,
        missing_skills=skill_gaps.get("missing_skills", [])
    )
    
    result = {
        "profile": profile,
        "recommendations": recommendations,
        "skill_gaps": skill_gaps,
        "pathway": pathway
    }
    
    logger.info(f"Pipeline executed: {len(recommendations)} recommendations, pathway generated")
    return result
