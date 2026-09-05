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
    "below 5th": 0,
    "primary pass": 1,
    "primary": 1,
    "5th pass": 1,
    "5th": 1,
    "8th pass": 2,
    "8th": 2,
    "10th pass": 3,
    "10th": 3,
    "12th pass": 4,
    "12th": 4,
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

SKILL_SYNONYMS = {
    "stitching": "tailoring",
    "driving": "operation",
    "sewing": "tailoring",
    "farming": "agriculture",
    "carpentry": "woodwork",
    "welding": "fabrication",
    "web": "software",
    "development": "software",
    "developer": "software",
    "apparel": "tailoring"
}


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

    if not b_norm_set:
        return {
            "score": 0,
            "max_score": 25,
            "matched_skills": [],
            "missing_skills": list(r_norm_map.values()),
            "coverage": 0.0,
            "coverage_percentage": 0.0,
            "explanation": "Beneficiary skills are unknown or none provided.",
            "evidence_status": "unknown"
        }

    if not r_norm_set:
        return {
            "score": 0,
            "max_score": 25,
            "matched_skills": [],
            "missing_skills": [],
            "coverage": 0.0,
            "coverage_percentage": 0.0,
            "explanation": "Role has no required skills, but beneficiary skills do not strictly match it yet. (Subject to sector alignment)",
            "evidence_status": "mismatched"
        }

    matched_norm = set()
    for r_norm in r_norm_set:
        r_tokens = set(r_norm.split()) - SKILL_STOP_WORDS
        for b_norm in b_norm_set:
            b_tokens = set(b_norm.split()) - SKILL_STOP_WORDS
            
            # Expand beneficiary tokens with synonyms
            expanded_b_tokens = set(b_tokens)
            for t in b_tokens:
                if t in SKILL_SYNONYMS:
                    expanded_b_tokens.add(SKILL_SYNONYMS[t])
                for k, v in SKILL_SYNONYMS.items():
                    if v == t:
                        expanded_b_tokens.add(k)

            # 1. Exact match
            if r_norm == b_norm:
                matched_norm.add(r_norm)
                break
            
            # 2. Token overlap: require at least 50% of required tokens to be present
            if r_tokens and expanded_b_tokens:
                overlap = r_tokens & expanded_b_tokens
                if len(overlap) / len(r_tokens) >= 0.5:
                    matched_norm.add(r_norm)
                    break

    missing_norm = r_norm_set - matched_norm

    matched_skills = [r_norm_map[m] for m in matched_norm]
    missing_skills = [r_norm_map[m] for m in missing_norm]

    coverage = len(matched_norm) / len(r_norm_set)
    coverage_percentage = round(coverage * 100, 1)
    score = round(coverage * 25)

    explanation = f"Matched {len(matched_skills)} of {len(r_norm_set)} required skills ({coverage_percentage}% coverage)."
    evidence_status = "matched" if coverage > 0 else "mismatched"

    return {
        "score": score,
        "max_score": 25,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "coverage": round(coverage, 4),
        "coverage_percentage": coverage_percentage,
        "explanation": explanation,
        "evidence_status": evidence_status
    }


def calculate_skill_score(beneficiary_skills: list, work_experience: str, current_occupation: str, required_skills: str, job_sector: str, job_role: str) -> dict:
    """
    Calculate Skill Score (Max 25 points).
    Delegates skill comparison to match_skills(), and adds boost for relevant experience/occupation.
    """
    b_skills = list(beneficiary_skills) if beneficiary_skills else []
    res = match_skills(b_skills, required_skills)
    
    signals_used = ["skills"]
    if not b_skills:
        signals_used = []
        
    boost_explanation = []
    exp_occ = []
    if work_experience: exp_occ.append(work_experience)
    if current_occupation: exp_occ.append(current_occupation)
    
    if exp_occ:
        combined_text = " ".join(exp_occ).lower()
        role_tokens = set(job_role.lower().split()) | set(job_sector.lower().split()) - SKILL_STOP_WORDS
        b_tokens = set(combined_text.split()) - SKILL_STOP_WORDS
        
        overlap = role_tokens & b_tokens
        # check synonyms too
        for t in b_tokens:
            if t in SKILL_SYNONYMS and SKILL_SYNONYMS[t] in role_tokens:
                overlap.add(SKILL_SYNONYMS[t])
            for k, v in SKILL_SYNONYMS.items():
                if v == t and k in role_tokens:
                    overlap.add(k)
                    
        if overlap:
            if work_experience: signals_used.append("work_experience")
            if current_occupation: signals_used.append("current_occupation")
            
            bonus = min(10, len(overlap) * 5)
            new_score = min(25, res["score"] + bonus)
            if new_score > res["score"]:
                res["score"] = new_score
                boost_explanation.append(f"Past experience/occupation aligns with role (+{bonus} pts).")
                res["evidence_status"] = "matched"
                
    if boost_explanation:
        res["explanation"] += " " + " ".join(boost_explanation)
        
    res["signals_used"] = signals_used
    return res


def calculate_education_score(beneficiary_education: str, required_education: str) -> dict:
    """
    Calculate Education Score (Max 20 points).
    Compares beneficiary's formal education level with minimum job requirement.
    """
    if not beneficiary_education or str(beneficiary_education).strip() in ("", "None", "Unknown"):
        return {
            "score": 0,
            "max_score": 20,
            "explanation": "Education level is unknown. No points awarded.",
            "evidence_status": "unknown"
        }

    b_level = beneficiary_education.strip().lower()
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

    b_display = beneficiary_education
    r_display = required_education if required_education else "None required"
    
    if b_rank >= r_rank:
        score = 20
        explanation = f"Education ({b_display}) meets or exceeds job requirement ({r_display})."
        evidence_status = "matched"
    elif b_rank == r_rank - 1:
        score = 10
        explanation = f"Education ({b_display}) is slightly below requirement ({r_display}); partial match."
        evidence_status = "matched"
    else:
        score = 0
        explanation = f"Education ({b_display}) does not meet the minimum requirement ({r_display})."
        evidence_status = "mismatched"

    return {
        "score": score,
        "max_score": 20,
        "explanation": explanation,
        "evidence_status": evidence_status,
        "signals_used": ["education"] if evidence_status != "unknown" else []
    }


def calculate_interest_score(beneficiary_interests: list, aspirations: str, family_occupation: str, job_sector: str) -> dict:
    """
    Calculate Interest Score (Max 20 points).
    Checks if the job's sector matches beneficiary's expressed interests, aspirations, and family occupation.
    """
    b_interests = list(beneficiary_interests) if beneficiary_interests else []
    
    def _base_interest(b_int, j_sec):
        if not b_int or all(str(i).strip() in ("", "None", "Unknown") for i in b_int):
            return {"score": 0, "max_score": 20, "explanation": "No specific sector preference listed by beneficiary.", "evidence_status": "unknown"}
        sec_clean = j_sec.strip().lower() if j_sec else ""
        int_clean = [i.strip().lower() for i in b_int if i.strip()]
        for interest in int_clean:
            if interest == sec_clean:
                return {"score": 20, "max_score": 20, "explanation": f"Job sector ({j_sec}) exactly matches beneficiary interest ({interest}).", "evidence_status": "matched"}
            int_tokens = set(interest.split()) - SKILL_STOP_WORDS
            sec_tokens = set(sec_clean.split()) - SKILL_STOP_WORDS
            for tok in int_tokens:
                if len(tok) >= 4:
                    for sec_tok in sec_tokens:
                        if len(sec_tok) >= 4 and (tok.startswith(sec_tok[:5]) or sec_tok.startswith(tok[:5])):
                            return {"score": 20, "max_score": 20, "explanation": f"Job sector ({j_sec}) matches beneficiary interest ({interest}).", "evidence_status": "matched"}
                if (tok in ("farm", "farming", "crop", "crops", "agriculture") and any("agri" in st for st in sec_tokens)) or \
                   (tok in ("solar", "electric", "wiring", "energy") and any(st in ("green", "power", "electronics", "energy") for st in sec_tokens)):
                    return {"score": 20, "max_score": 20, "explanation": f"Job sector ({j_sec}) matches beneficiary interest ({interest}).", "evidence_status": "matched"}
        return {"score": 0, "max_score": 20, "explanation": f"Job sector ({j_sec}) does not align with stated interests ({', '.join(b_int)}).", "evidence_status": "mismatched"}

    res = _base_interest(b_interests, job_sector)
    signals_used = ["interests"] if res["evidence_status"] != "unknown" else []
    boost = []
    
    sec_lower = job_sector.lower()
    if aspirations and any(t in sec_lower for t in aspirations.lower().split() if len(t) > 3):
        res["score"] = min(20, res["score"] + 5)
        boost.append("Aspirations match sector.")
        signals_used.append("aspirations")
        res["evidence_status"] = "matched"
        
    if family_occupation and any(t in sec_lower for t in family_occupation.lower().split() if len(t) > 3):
        res["score"] = min(20, res["score"] + 5)
        boost.append("Family occupation provides livelihood continuity.")
        signals_used.append("family_occupation")
        res["evidence_status"] = "matched"
        
    if boost:
        if res["explanation"].startswith("No specific"):
            res["explanation"] = " ".join(boost)
        else:
            res["explanation"] += " " + " ".join(boost)
            
    if res["evidence_status"] == "unknown" and not boost:
        res["explanation"] += " No points awarded."
        
    res["signals_used"] = signals_used
    return res


def calculate_mobility_score(beneficiary_mobility: str, job_mobility_req: str) -> dict:
    """
    Calculate Mobility Score (Max 15 points).
    Checks if beneficiary's travel willingness matches job location requirements.
    """
    if not beneficiary_mobility or str(beneficiary_mobility).strip() in ("", "None", "Unknown"):
        return {
            "score": 0,
            "max_score": 15,
            "explanation": "Mobility preference is unknown. No points awarded.",
            "evidence_status": "unknown"
        }

    b_mob = beneficiary_mobility.strip().lower()
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
        evidence_status = "matched"
    elif b_rank == 1 and j_rank == 2:
        score = 8
        explanation = f"Job requires district-level travel ({job_mobility_req}); beneficiary prefers local work."
        evidence_status = "matched"
    else:
        score = 0
        explanation = f"Job mobility ({job_mobility_req}) exceeds beneficiary preference ({beneficiary_mobility})."
        evidence_status = "mismatched"

    return {
        "score": score,
        "max_score": 15,
        "explanation": explanation,
        "evidence_status": evidence_status,
        "signals_used": ["mobility"] if evidence_status != "unknown" else []
    }


def calculate_employment_preference_score(beneficiary_pref: str, self_emp_suitability: str, wage_emp_suitability: str) -> dict:
    """
    Calculate Employment Preference Score (Max 10 points).
    Matches beneficiary's employment type goal (Self-Emp vs Wage-Emp) with job suitability ratings.
    """
    if not beneficiary_pref or str(beneficiary_pref).strip() in ("", "None", "Any", "Unknown", "any", "unknown"):
        return {
            "score": 0,
            "max_score": 10,
            "explanation": "Employment preference is unknown or flexible; no points awarded.",
            "evidence_status": "unknown"
        }

    pref_clean = beneficiary_pref.strip().lower()
    self_suit = self_emp_suitability.strip().capitalize() if self_emp_suitability else "Low"
    wage_suit = wage_emp_suitability.strip().capitalize() if wage_emp_suitability else "Low"

    suitability_points = {"High": 10, "Medium": 6, "Low": 0}

    if "self" in pref_clean:
        score = suitability_points.get(self_suit, 0)
        explanation = f"Beneficiary prefers self-employment; role self-employment suitability is {self_suit}."
        evidence_status = "matched" if score > 0 else "mismatched"
    elif "wage" in pref_clean or "job" in pref_clean or "salaried" in pref_clean:
        score = suitability_points.get(wage_suit, 0)
        explanation = f"Beneficiary prefers wage employment; role wage-employment suitability is {wage_suit}."
        evidence_status = "matched" if score > 0 else "mismatched"
    else:
        score = 0
        explanation = "Employment preference did not match any known category."
        evidence_status = "mismatched"

    return {
        "score": score,
        "max_score": 10,
        "explanation": explanation,
        "evidence_status": evidence_status,
        "signals_used": ["employment_preference"] if evidence_status != "unknown" else []
    }


def calculate_local_opportunity_score(has_local_opportunity: bool, district_match: bool = True, is_exact: bool = False) -> dict:
    """
    Calculate Local Opportunity Score (Max 10 points).
    Checks if active training centers or local job vacancies exist in beneficiary's district.
    """
    if has_local_opportunity and district_match and is_exact:
        score = 10
        explanation = "Exact matching active local job vacancy or training center found in beneficiary's district."
        evidence_status = "matched"
    elif has_local_opportunity and district_match:
        score = 6
        explanation = "Related sector-level local opportunity found in beneficiary's district."
        evidence_status = "matched"
    elif has_local_opportunity and not district_match:
        score = 3
        explanation = "Local opportunities found in nearby adjacent districts."
        evidence_status = "matched"
    else:
        score = 0
        explanation = "No active local opportunity listed in beneficiary's district yet."
        evidence_status = "unknown"

    return {
        "score": score,
        "max_score": 10,
        "explanation": explanation,
        "evidence_status": evidence_status,
        "signals_used": ["district"] if evidence_status != "unknown" else []
    }

def calculate_constraints_penalty(constraints: str, job_sector: str, job_role: str) -> dict:
    """
    Calculate Constraints Penalty (Negative score).
    Reduces total score if beneficiary constraints conflict with job demands.
    """
    if not constraints or str(constraints).strip() in ("", "None", "Unknown"):
        return {
            "score": 0,
            "max_score": 0,
            "explanation": "",
            "evidence_status": "unknown",
            "signals_used": []
        }
    
    c_lower = constraints.lower()
    r_lower = f"{job_sector} {job_role}".lower()
    
    penalty = 0
    explanation = "Constraints noted but no direct conflict found."
    status = "matched"
    
    if "physical" in c_lower or "heavy" in c_lower or "health" in c_lower:
        if any(w in r_lower for w in ["construction", "plumbing", "mason", "agriculture", "logistics", "heavy"]):
            penalty = -15
            explanation = "Constraint regarding physical/health limitations conflicts with physically demanding role."
            status = "mismatched"
            
    if "travel" in c_lower or "mobility" in c_lower:
        if "field" in r_lower or "delivery" in r_lower or "sales" in r_lower:
            penalty = -10
            explanation = "Constraint regarding travel conflicts with field/delivery role."
            status = "mismatched"
            
    return {
        "score": penalty,
        "max_score": 0,
        "explanation": explanation if penalty < 0 else "",
        "evidence_status": status,
        "signals_used": ["constraints"]
    }


def calculate_total_score(
    beneficiary_profile: dict,
    job_role_data: dict,
    has_local_opportunity: bool = True,
    is_exact_opportunity: bool = False
) -> dict:
    """
    Master Scoring Engine Function.
    Aggregates all 6 component scores out of 100 and computes match confidence.
    """
    # 1. Education
    edu_res = calculate_education_score(
        beneficiary_profile.get("education", ""),
        job_role_data.get("minimum_education", "")
    )

    # 2. Skills
    skill_res = calculate_skill_score(
        beneficiary_skills=beneficiary_profile.get("skills", []),
        work_experience=beneficiary_profile.get("work_experience", ""),
        current_occupation=beneficiary_profile.get("current_occupation", ""),
        required_skills=job_role_data.get("required_skills", ""),
        job_sector=job_role_data.get("sector", ""),
        job_role=job_role_data.get("job_role", "")
    )

    # 3. Interest
    interest_res = calculate_interest_score(
        beneficiary_interests=beneficiary_profile.get("interests", []),
        aspirations=beneficiary_profile.get("aspirations", ""),
        family_occupation=beneficiary_profile.get("family_occupation", ""),
        job_sector=job_role_data.get("sector", "")
    )

    # 4. Mobility
    mobility_res = calculate_mobility_score(
        beneficiary_profile.get("mobility", "Unknown"),
        job_role_data.get("mobility_requirement", "Local")
    )

    # 5. Employment Preference
    emp_res = calculate_employment_preference_score(
        beneficiary_profile.get("employment_preference", "Unknown"),
        job_role_data.get("self_employment_suitability", "Low"),
        job_role_data.get("wage_employment_suitability", "Low")
    )

    # 6. Local Opportunity
    local_res = calculate_local_opportunity_score(has_local_opportunity, is_exact=is_exact_opportunity)

    # 7. Constraints (Penalty)
    constraint_res = calculate_constraints_penalty(
        constraints=beneficiary_profile.get("constraints", ""),
        job_sector=job_role_data.get("sector", ""),
        job_role=job_role_data.get("job_role", "")
    )

    breakdown = {
        "education": edu_res,
        "skill": skill_res,
        "interest": interest_res,
        "mobility": mobility_res,
        "employment_preference": emp_res,
        "local_opportunity": local_res,
        "constraints": constraint_res
    }

    missing_fields_list = [
        key for key in ["education", "skill", "interest", "mobility", "employment_preference"]
        if breakdown[key]["evidence_status"] == "unknown"
    ]
    unknown_count = len(missing_fields_list)

    total_score = sum(res["score"] for res in breakdown.values())
    if total_score < 0:
        total_score = 0

    # Confidence calculation
    if unknown_count >= 3:
        confidence = "Need More Information"
        # Heavily penalize the score if we don't have enough evidence
        if total_score >= 80:
            total_score = 79 # Do not allow 80%+ if we need more info
    elif total_score >= 80:
        confidence = "Strong Match"
    elif total_score >= 50:
        confidence = "Potential Match"
    else:
        confidence = "Weak Match"

    return {
        "total_score": total_score,
        "max_total_score": 100,
        "confidence": confidence,
        "evidence": {
            "unknown_fields": unknown_count,
            "missing_keys": missing_fields_list
        },
        "breakdown": breakdown
    }
