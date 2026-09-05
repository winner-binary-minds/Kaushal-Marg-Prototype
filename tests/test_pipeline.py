"""Tests for integration/pipeline.py"""

import pytest
from unittest.mock import Mock, patch

from integration.pipeline import run_recommendation_pipeline


class TestRecommendationPipeline:
    """Test end-to-end recommendation pipeline."""
    
    def test_pipeline_successful_flow(self):
        """Test successful pipeline execution."""
        with patch("integration.pipeline.ProfileExtractor"):
            with patch("integration.pipeline.recommend_jobs"):
                with patch("integration.pipeline.analyze_skill_gap"):
                    with patch("integration.pipeline.generate_skill_pathway"):
                        # Setup mocks
                        mock_manager = Mock()
                        from ai.conversation import Message
                        mock_manager.get_history.return_value = [
                            Message(role="user", content="I want to farm", language="en"),
                        ]
                        
                        # Mock components
                        with patch("integration.pipeline.ProfileExtractor") as mock_extractor_class:
                            mock_extractor = Mock()
                            mock_extractor_class.return_value = mock_extractor
                            mock_extractor.extract_profile.return_value = {
                                "education": "10th Pass",
                                "skills": ["farming"],
                                "interests": ["agriculture"],
                                "district": "Indore",
                                "employment_preference": "Self-Employment",
                                "mobility": "Local"
                            }
                            
                            with patch("integration.pipeline.recommend_jobs") as mock_recommend:
                                mock_recommend.return_value = [
                                    {"job_role": "Farmer", "sector": "Agriculture", "score": 85},
                                ]
                                
                                with patch("integration.pipeline.analyze_skill_gap") as mock_gap:
                                    mock_gap.return_value = {
                                        "matched_skills": ["farming"],
                                        "missing_skills": [],
                                        "skill_coverage_percentage": 100.0
                                    }
                                    
                                    with patch("integration.pipeline.generate_skill_pathway") as mock_pathway:
                                        mock_pathway.return_value = {
                                            "current_state": "10th Pass with farming experience",
                                            "skills_to_build": []
                                        }
                                        
                                        result = run_recommendation_pipeline(mock_manager)
                                        
                                        assert result["profile"]["education"] == "10th Pass"
                                        assert len(result["recommendations"]) == 1
                                        assert result["skill_gaps"]["skill_coverage_percentage"] == 100.0
                                        assert "pathway" in result
    
    def test_pipeline_empty_history_raises_error(self):
        """Test pipeline fails gracefully with empty history."""
        mock_manager = Mock()
        mock_manager.get_history.return_value = []
        
        with pytest.raises(ValueError) as exc:
            run_recommendation_pipeline(mock_manager)
        
        assert "No conversation history" in str(exc.value)
    
    def test_pipeline_no_recommendations_returns_empty(self):
        """Test pipeline returns empty structures if no recommendations generated."""
        from ai.conversation import Message
        mock_manager = Mock()
        mock_manager.get_history.return_value = [
            Message(role="user", content="Hello", language="en"),
        ]
        
        with patch("integration.pipeline.ProfileExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.extract_profile.return_value = {"education": None, "skills": [], "interests": [], "district": None, "employment_preference": None, "mobility": None}
            
            with patch("integration.pipeline.recommend_jobs") as mock_recommend:
                mock_recommend.return_value = []  # Empty recommendations
                
                result = run_recommendation_pipeline(mock_manager)
                
                assert result["recommendations"] == []
                assert result["skill_gaps"] == {}
                assert result["pathway"] == {}
