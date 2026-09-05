"""
Skill Gap Analysis Module for Kaushal Marg.

Analyzes missing skills between a beneficiary's profile and target job roles
to generate actionable training recommendations.
"""

from recommendation.scoring import match_skills


def analyze_skill_gap(beneficiary_profile: dict, job_role_data: dict) -> dict:
    """
    Analyzes skill gaps between beneficiary's profile and job role requirements.

    Parameters:
    -----------
    beneficiary_profile : dict
        Beneficiary information dictionary or object (e.g. {"skills": ["basic wiring", "repair"]})
    job_role_data : dict
        Job role information dictionary or object (e.g. {"job_role": "Electrician", "required_skills": [...]})

    Returns:
    --------
    dict
        {
            "job_role": str,
            "matched_skills": list,
            "missing_skills": list,
            "skill_coverage_percentage": float,
            "summary": str
        }
    """
    # Extract skills supporting both dictionary and object formats
    if isinstance(beneficiary_profile, dict):
        b_skills = beneficiary_profile.get("skills", [])
    else:
        b_skills = getattr(beneficiary_profile, "skills", [])

    if isinstance(job_role_data, dict):
        r_skills_raw = job_role_data.get("required_skills") or job_role_data.get("job_details", {}).get("required_skills", [])
        role_title = job_role_data.get("job_role", "Target Role")
    else:
        r_skills_raw = getattr(job_role_data, "required_skills", [])
        role_title = getattr(job_role_data, "job_role", "Target Role")

    match_result = match_skills(b_skills, r_skills_raw)

    matched_skills = match_result.get("matched_skills", [])
    missing_skills = match_result.get("missing_skills", [])
    coverage_pct = round(match_result.get("coverage", 0.0) * 100, 2)

    if not missing_skills:
        summary = f"Beneficiary possesses 100% of required skills for {role_title}."
    else:
        summary = (
            f"Beneficiary possesses {len(matched_skills)} required skill(s) ({coverage_pct}% coverage). "
            f"Training recommended for {len(missing_skills)} missing skill(s): {', '.join(missing_skills)}."
        )

    return {
        "job_role": role_title,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_coverage_percentage": coverage_pct,
        "summary": summary
    }
