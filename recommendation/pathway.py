"""
Livelihood Pathway Module ("My Skill Journey") for Kaushal Marg.

Generates a structured, deterministic step-by-step skill progression pathway
bridging a beneficiary's current capabilities to their target NSQF job role.
"""

from typing import Dict, List, Any


def generate_skill_pathway(
    beneficiary_profile: Dict[str, Any],
    recommended_job_role: Dict[str, Any],
    missing_skills: List[str] = None
) -> Dict[str, Any]:
    """
    Generates a structured 'Skill Journey' roadmap for a beneficiary.

    Parameters:
    -----------
    beneficiary_profile : dict or object
        Contains beneficiary education, current skills, occupation, etc.
    recommended_job_role : dict or object
        Contains target job role title, sector, nsqf_level, required_skills.
    missing_skills : list, optional
        List of missing skills identified by Skill Gap analysis.

    Returns:
    --------
    dict
        {
            "current_state": str,
            "foundation_skills": list,
            "skills_to_build": list,
            "training_stage": dict,
            "practical_stage": dict,
            "target_role": dict
        }
    """
    # Extract profile attributes safely
    if isinstance(beneficiary_profile, dict):
        b_skills = beneficiary_profile.get("skills", [])
        b_edu = beneficiary_profile.get("education", "Basic Education")
        b_occ = beneficiary_profile.get("occupation", "")
    else:
        b_skills = getattr(beneficiary_profile, "skills", [])
        b_edu = getattr(beneficiary_profile, "education", "Basic Education")
        b_occ = getattr(beneficiary_profile, "occupation", "")

    # Extract job role attributes safely
    if isinstance(recommended_job_role, dict):
        role_title = recommended_job_role.get("job_role", "Target Role")
        sector = recommended_job_role.get("sector", "General")
        nsqf_level = recommended_job_role.get("nsqf_level", "3")
        req_skills_raw = recommended_job_role.get("required_skills", "")
    else:
        role_title = getattr(recommended_job_role, "job_role", "Target Role")
        sector = getattr(recommended_job_role, "sector", "General")
        nsqf_level = getattr(recommended_job_role, "nsqf_level", "3")
        req_skills_raw = getattr(recommended_job_role, "required_skills", "")

    # Resolve skills to build if not explicitly passed
    if missing_skills is None:
        if isinstance(req_skills_raw, str):
            r_skills = [s.strip() for s in req_skills_raw.split("|") if s.strip()]
        else:
            r_skills = req_skills_raw or []

        b_skills_lower = [s.lower() for s in b_skills if isinstance(s, str)]
        matched = [s for s in r_skills if any(b in s.lower() or s.lower() in b for b in b_skills_lower)]
        to_build = [s for s in r_skills if s not in matched]
        foundation = matched if matched else (b_skills if b_skills else ["Basic literacy"])
    else:
        to_build = missing_skills
        foundation = [s for s in b_skills if s] if b_skills else ["Basic literacy"]

    # Current state string summary
    occ_str = f" in {b_occ}" if b_occ else ""
    skills_summary = ", ".join(b_skills) if b_skills else "entry-level experience"
    current_state = f"{b_edu}{occ_str} with experience in {skills_summary}."

    # Classroom & Theory Training Stage
    if to_build:
        theory_modules = [f"Theory & Fundamentals: {skill}" for skill in to_build]
    else:
        theory_modules = ["NSQF Level Advanced Theory & Industry Standards"]

    training_stage = {
        "description": "Classroom & Technical Theory Foundation",
        "learning_modules": theory_modules
    }

    # Workshop & Practical Training Stage
    if to_build:
        practical_tasks = [f"Hands-on Lab Practice: {skill}" for skill in to_build]
    else:
        practical_tasks = [f"On-the-Job Workshop Practice for {role_title}"]

    practical_stage = {
        "description": "Practical Workshop & Hands-on Skill Application",
        "practical_tasks": practical_tasks
    }

    target_role_info = {
        "role": role_title,
        "sector": sector,
        "nsqf_level": f"Level {nsqf_level}"
    }

    return {
        "current_state": current_state,
        "foundation_skills": foundation,
        "skills_to_build": to_build,
        "training_stage": training_stage,
        "practical_stage": practical_stage,
        "target_role": target_role_info
    }
