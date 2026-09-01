"""
Scoring Module for Kaushal Marg.

Provides deterministic, explainable scoring functions to evaluate
how well a job role or opportunity fits a beneficiary's profile.

Total Maximum Score = 100 points
--------------------------------
1. Education Score            : Max 20 points
2. Skill Score                : Max 25 points
3. Interest Score             : Max 20 points
4. Mobility Score             : Max 15 points
5. Employment Preference Score: Max 10 points
6. Local Opportunity Score    : Max 10 points
"""

# Map education levels to numerical ranks for comparison
EDUCATION_RANKS = {
    "no formal education": 0,
    "below 5th pass": 0,
    "primary pass": 1,
    "5th pass": 1,
    "8th pass": 2,
    "10th pass": 3,
    "12th pass": 4,
    "iti": 5,
    "diploma": 5,
    "graduate": 6
}

# Map mobility levels to numerical ranks
MOBILITY_RANKS = {
    "local": 1,
    "local only": 1,
    "district": 2,
    "district level": 2,
    "state": 3,
    "state wide": 3
}

# Common stop words ignored during token-based skill matching
SKILL_STOP_WORDS = {"and", "or", "in", "the", "of", "to", "for", "with", "basic", "general", "setup", "check", "operation", "operating"}


def normalize_skill(skill: str) -> str:
    """
    Normalize a skill string by removing extra spaces and converting to lowercase.
    Example: '  SOLAR   WIRING  ' -> 'solar wiring'
    """
    if not skill or not isinstance(skill, str):
        return ""
    return " ".join(skill.strip().lower().split())


def match_skills(beneficiary_skills, required_skills) -> dict:
    """
    Core Skill Matching Engine.
    Matches beneficiary skills against job requirements, handles normalization,
    deduplication, substring matching, token-level matching, missing skill identification, and coverage calculation.
    """
    if isinstance(beneficiary_skills, str):
        b_raw = beneficiary_skills.split("|") if "|" in beneficiary_skills else beneficiary_skills.split(",")
    else:
        b_raw = beneficiary_skills or []

    if isinstance(required_skills, str):
        r_raw = required_skills.split("|") if "|" in required_skills else required_skills.split(",")
    else:
        r_raw = required_skills or []

    b_norm_map = {}
    for s in b_raw:
        if isinstance(s, str):
            norm = normalize_skill(s)
            if norm and norm not in b_norm_map:
                b_norm_map[norm] = s.strip()

    r_norm_map = {}
    for s in r_raw:
        if isinstance(s, str):
            norm = normalize_skill(s)
            if norm and norm not in r_norm_map:
                r_norm_map[norm] = s.strip()

    r_norm_set = set(r_norm_map.keys())
    b_norm_set = set(b_norm_map.keys())

    if not r_norm_set:
        return {
            "score": 25,
            "max_score": 25,
            "matched_skills": [],
            "missing_skills": [],
            "coverage": 1.0,
            "coverage_percentage": 100.0,
            "explanation": "No specific skills required for this entry-level role."
        }

    matched_norm = set()
    for r_norm in r_norm_set:
        r_tokens = set(r_norm.split()) - SKILL_STOP_WORDS
        for b_norm in b_norm_set:
            b_tokens = set(b_norm.split()) - SKILL_STOP_WORDS

            # 1. Exact or substring match
            if r_norm == b_norm or r_norm in b_norm or b_norm in r_norm:
                matched_norm.add(r_norm)
                break
            # 2. Significant domain token match (e.g. 'tractor' in 'tractor operation' & 'tractor driving')
            elif r_tokens and b_tokens and (r_tokens & b_tokens):
                matched_norm.add(r_norm)
                break

    missing_norm = r_norm_set - matched_norm

    matched_skills = [r_norm_map[m] for m in matched_norm]
    missing_skills = [r_norm_map[m] for m in missing_norm]

    coverage = len(matched_norm) / len(r_norm_set)
    coverage_percentage = round(coverage * 100, 1)
    score = round(coverage * 25)

    explanation = f"Matched {len(matched_skills)} of {len(r_norm_set)} required skills ({coverage_percentage}% coverage)."

    return {
        "score": score,
        "max_score": 25,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "coverage": round(coverage, 4),
        "coverage_percentage": coverage_percentage,
        "explanation": explanation
    }


def calculate_skill_score(beneficiary_skills, required_skills) -> dict:
    """
    Calculate Skill Score (Max 25 points).
    Delegates skill comparison and coverage calculation to match_skills().
    """
    return match_skills(beneficiary_skills, required_skills)


def calculate_education_score(beneficiary_education: str, required_education: str) -> dict:
    """
    Calculate Education Score (Max 20 points).
    Compares beneficiary's formal education level with minimum job requirement.
    """
    b_level = beneficiary_education.strip().lower() if beneficiary_education else ""
    r_level = required_education.strip().lower() if required_education else ""

    b_rank = 0
    for key, val in EDUCATION_RANKS.items():
        if key in b_level:
            b_rank = max(b_rank, val)

    r_rank = 99
    for key, val in EDUCATION_RANKS.items():
        if key in r_level:
            r_rank = min(r_rank, val)
    if r_rank == 99:
        r_rank = 0

    if b_rank >= r_rank:
        score = 20
        explanation = f"Education ({beneficiary_education}) meets or exceeds job requirement ({required_education})."
    elif b_rank == r_rank - 1:
        score = 10
        explanation = f"Education ({beneficiary_education}) is slightly below requirement ({required_education}); bridge training recommended."
    else:
        score = 0
        explanation = f"Education ({beneficiary_education}) does not meet the minimum requirement ({required_education})."

    return {
        "score": score,
        "max_score": 20,
        "explanation": explanation
    }


def calculate_interest_score(beneficiary_interests: list, job_sector: str) -> dict:
    """
    Calculate Interest Score (Max 20 points).
    Checks if the job's sector matches beneficiary's expressed interests.
    """
    if not beneficiary_interests:
        return {
            "score": 10,
            "max_score": 20,
            "explanation": "No specific sector preference listed by beneficiary."
        }

    sector_clean = job_sector.strip().lower() if job_sector else ""
    interests_clean = [i.strip().lower() for i in beneficiary_interests if i.strip()]

    for interest in interests_clean:
        if interest in sector_clean or sector_clean in interest:
            return {
                "score": 20,
                "max_score": 20,
                "explanation": f"Job sector ({job_sector}) matches beneficiary interest ({interest})."
            }

    return {
        "score": 0,
        "max_score": 20,
        "explanation": f"Job sector ({job_sector}) does not align with stated interests ({', '.join(beneficiary_interests)})."
    }


def calculate_mobility_score(beneficiary_mobility: str, job_mobility_req: str) -> dict:
    """
    Calculate Mobility Score (Max 15 points).
    Checks if beneficiary's travel willingness matches job location requirements.
    """
    b_mob = beneficiary_mobility.strip().lower() if beneficiary_mobility else "local"
    j_mob = job_mobility_req.strip().lower() if job_mobility_req else "local"

    b_rank = 1
    for key, val in MOBILITY_RANKS.items():
        if key in b_mob:
            b_rank = max(b_rank, val)

    j_rank = 99
    for key, val in MOBILITY_RANKS.items():
        if key in j_mob:
            j_rank = min(j_rank, val)
    if j_rank == 99:
        j_rank = 1

    if b_rank >= j_rank:
        score = 15
        explanation = f"Beneficiary mobility ({beneficiary_mobility}) satisfies job requirement ({job_mobility_req})."
    elif b_rank == 1 and j_rank == 2:
        score = 8
        explanation = f"Job requires district-level travel ({job_mobility_req}); beneficiary prefers local work."
    else:
        score = 0
        explanation = f"Job mobility ({job_mobility_req}) exceeds beneficiary preference ({beneficiary_mobility})."

    return {
        "score": score,
        "max_score": 15,
        "explanation": explanation
    }


def calculate_employment_preference_score(beneficiary_pref: str, self_emp_suitability: str, wage_emp_suitability: str) -> dict:
    """
    Calculate Employment Preference Score (Max 10 points).
    Matches beneficiary's employment type goal (Self-Emp vs Wage-Emp) with job suitability ratings.
    """
    pref_clean = beneficiary_pref.strip().lower() if beneficiary_pref else "any"
    self_suit = self_emp_suitability.strip().capitalize() if self_emp_suitability else "Low"
    wage_suit = wage_emp_suitability.strip().capitalize() if wage_emp_suitability else "Low"

    suitability_points = {"High": 10, "Medium": 6, "Low": 2}

    if "self" in pref_clean:
        score = suitability_points.get(self_suit, 2)
        explanation = f"Beneficiary prefers self-employment; role self-employment suitability is {self_suit}."
    elif "wage" in pref_clean or "job" in pref_clean or "salaried" in pref_clean:
        score = suitability_points.get(wage_suit, 2)
        explanation = f"Beneficiary prefers wage employment; role wage-employment suitability is {wage_suit}."
    else:
        score = max(suitability_points.get(self_suit, 2), suitability_points.get(wage_suit, 2))
        explanation = f"Beneficiary has flexible preference; role offers High/Medium options (Self: {self_suit}, Wage: {wage_suit})."

    return {
        "score": score,
        "max_score": 10,
        "explanation": explanation
    }


def calculate_local_opportunity_score(has_local_opportunity: bool, district_match: bool = True) -> dict:
    """
    Calculate Local Opportunity Score (Max 10 points).
    Checks if active training centers or local job vacancies exist in beneficiary's district.
    """
    if has_local_opportunity and district_match:
        score = 10
        explanation = "Active local job vacancies or training centers found in beneficiary's district."
    elif has_local_opportunity and not district_match:
        score = 5
        explanation = "Local opportunities found in nearby adjacent districts."
    else:
        score = 0
        explanation = "No active local opportunity listed in beneficiary's district yet."

    return {
        "score": score,
        "max_score": 10,
        "explanation": explanation
    }


def calculate_total_score(
    beneficiary_profile: dict,
    job_role_data: dict,
    has_local_opportunity: bool = True
) -> dict:
    """
    Master Scoring Engine Function.
    Aggregates all 6 component scores out of 100.
    """
    # 1. Education
    edu_res = calculate_education_score(
        beneficiary_profile.get("education", ""),
        job_role_data.get("minimum_education", "")
    )

    # 2. Skills
    req_skills_input = job_role_data.get("required_skills", "")
    b_skills_input = beneficiary_profile.get("skills", [])
    skill_res = calculate_skill_score(b_skills_input, req_skills_input)

    # 3. Interest
    interest_res = calculate_interest_score(
        beneficiary_profile.get("interests", []),
        job_role_data.get("sector", "")
    )

    # 4. Mobility
    mobility_res = calculate_mobility_score(
        beneficiary_profile.get("mobility", "Local"),
        job_role_data.get("mobility_requirement", "Local")
    )

    # 5. Employment Preference
    emp_res = calculate_employment_preference_score(
        beneficiary_profile.get("employment_preference", "Any"),
        job_role_data.get("self_employment_suitability", "Low"),
        job_role_data.get("wage_employment_suitability", "Low")
    )

    # 6. Local Opportunity
    local_res = calculate_local_opportunity_score(has_local_opportunity)

    total_score = (
        edu_res["score"] +
        skill_res["score"] +
        interest_res["score"] +
        mobility_res["score"] +
        emp_res["score"] +
        local_res["score"]
    )

    return {
        "total_score": total_score,
        "max_total_score": 100,
        "breakdown": {
            "education": edu_res,
            "skill": skill_res,
            "interest": interest_res,
            "mobility": mobility_res,
            "employment_preference": emp_res,
            "local_opportunity": local_res
        }
    }
