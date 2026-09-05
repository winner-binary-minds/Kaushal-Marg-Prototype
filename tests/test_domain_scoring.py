import pytest
from recommendation.matcher import recommend_jobs

class TestRecommendationDomainScoring:
    def test_graduate_web_dev_no_false_matches(self):
        """
        Profile: Graduate + Web Development + Software Engineer
        Expected: Since the 23-role dataset does not contain web/software roles,
        it should NOT falsely recommend unrelated roles (like Data Entry) merely because they are a graduate.
        It should return insufficient_information or need more info.
        """
        profile = {
            "education": "Graduate",
            "skills": ["Web Development", "Python", "React"],
            "interests": ["Software"],
            "district": "Jaipur",
            "employment_preference": "Wage-Employment",
            "current_occupation": "Software Engineer"
        }
        recs = recommend_jobs(profile, top_n=3)
        assert len(recs) > 0
        top_rec = recs[0]
        # Should not falsely match data entry. Should return no_strong_match.
        assert top_rec.get("status") == "no_strong_match"

    def test_tailoring_apparel_match(self):
        """
        Profile: 10th + Tailoring + Self-Employment + Jaipur
        Expected: Tailoring/apparel recommendations should rank strongly.
        """
        profile = {
            "education": "10th pass",
            "skills": ["Tailoring", "Stitching"],
            "interests": ["Apparel"],
            "district": "Jaipur",
            "employment_preference": "Self-Employment"
        }
        recs = recommend_jobs(profile, top_n=3)
        assert len(recs) > 0
        top_rec = recs[0]
        assert top_rec.get("status") != "insufficient_information"
        assert "tailor" in top_rec.get("job_role", "").lower() or "apparel" in top_rec.get("sector", "").lower()

    def test_agriculture_match(self):
        """
        Profile: Agriculture + farming skills + appropriate district
        Expected: Agriculture roles should rank strongly.
        """
        profile = {
            "education": "8th pass",
            "skills": ["Farming", "Crop management"],
            "interests": ["Agriculture"],
            "district": "Ajmer",
            "employment_preference": "Self-Employment"
        }
        recs = recommend_jobs(profile, top_n=3)
        assert len(recs) > 0
        top_rec = recs[0]
        assert top_rec.get("status") != "insufficient_information"
        assert "agriculture" in top_rec.get("sector", "").lower() or "farm" in top_rec.get("job_role", "").lower()

    def test_empty_profile_insufficient_information(self):
        """
        Profile: Empty profile
        Expected: insufficient_information
        """
        profile = {}
        recs = recommend_jobs(profile, top_n=3)
        assert len(recs) > 0
        top_rec = recs[0]
        assert top_rec.get("status") == "insufficient_information"
        assert top_rec.get("missing_information", {}).get("education") == "missing"
