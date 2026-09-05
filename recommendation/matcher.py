"""
Matcher Module for Kaushal Marg.

Primary recommendation engine that matches a BeneficiaryProfile against
all job roles in data/nsqf_jobs.csv and local opportunities in data/local_opportunities.csv,
ranks them deterministically, and returns top recommendations with transparent explanations.
"""

import csv
import os
from typing import List, Dict, Any

from recommendation.scoring import calculate_total_score, calculate_local_opportunity_score
from recommendation.skill_gap import analyze_skill_gap

DEFAULT_JOBS_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "nsqf_jobs.csv")
)

DEFAULT_OPPORTUNITIES_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "local_opportunities.csv")
)


def load_nsqf_jobs(csv_path: str = DEFAULT_JOBS_CSV) -> List[Dict[str, Any]]:
    """
    Safely loads the NSQF job dataset from CSV.
    Returns an empty list if file is missing or unreadable.
    """
    if not os.path.exists(csv_path):
        return []

    jobs = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get("job_role"):
                    jobs.append(row)
    except Exception:
        return []

    return jobs


def load_local_opportunities(csv_path: str = DEFAULT_OPPORTUNITIES_CSV) -> List[Dict[str, Any]]:
    """
    Safely loads local opportunities from CSV.
    Returns an empty list if file is missing or unreadable.
    """
    if not os.path.exists(csv_path):
        return []

    opportunities = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get("district") and row.get("job_role"):
                    opportunities.append(row)
    except Exception:
        return []

    return opportunities


def find_local_opportunity_match(
    beneficiary_district: str,
    job_role: str,
    sector: str,
    opportunities_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Finds matching local opportunity record for a district and job role/sector.
    """
    if not beneficiary_district or not isinstance(beneficiary_district, str) or not beneficiary_district.strip():
        return {
            "has_opportunity": False,
            "opportunity_score": 0,
            "opportunity_info": "No verified local opportunity data available",
            "details": None
        }

    b_dist = beneficiary_district.strip().lower()
    j_role = job_role.strip().lower() if job_role else ""
    j_sector = sector.strip().lower() if sector else ""

    matched_opp = None

    is_exact = False
    # Priority 1: Exact district AND job_role match
    for opp in opportunities_list:
        o_dist = opp.get("district", "").strip().lower() if opp.get("district") else ""
        o_role = opp.get("job_role", "").strip().lower() if opp.get("job_role") else ""
        if o_dist == b_dist and (o_role in j_role or j_role in o_role):
            matched_opp = opp
            is_exact = True
            break

    # Priority 2: District AND sector match
    if not matched_opp:
        for opp in opportunities_list:
            o_dist = opp.get("district", "").strip().lower() if opp.get("district") else ""
            o_sec = opp.get("sector", "").strip().lower() if opp.get("sector") else ""
            if o_dist == b_dist and (o_sec in j_sector or j_sector in o_sec):
                matched_opp = opp
                break

    if matched_opp:
        source_val = matched_opp.get("source", "").lower()
        if "live" in source_val or "verified" in source_val:
            source_tag = "Verified Live Data"
        else:
            source_tag = "Prototype Demo Data"

        return {
            "has_opportunity": True,
            "is_exact": is_exact,
            "opportunity_score": 10 if is_exact else 6,
            "opportunity_info": f"Local {matched_opp.get('opportunity_type', 'opportunity')} available in {matched_opp.get('district')} ({matched_opp.get('demand_level', 'Medium')} Demand)",
            "details": {
                "district": matched_opp.get("district"),
                "opportunity_type": matched_opp.get("opportunity_type"),
                "demand_level": matched_opp.get("demand_level"),
                "source": matched_opp.get("source"),
                "data_source_type": source_tag,
                "last_updated": matched_opp.get("last_updated")
            }
        }
    else:
        return {
            "has_opportunity": False,
            "is_exact": False,
            "opportunity_score": 0,
            "opportunity_info": "No verified local opportunity data available",
            "details": None
        }


def recommend_jobs(
    beneficiary_profile: Dict[str, Any],
    top_n: int = 3,
    jobs_csv_path: str = DEFAULT_JOBS_CSV,
    opp_csv_path: str = DEFAULT_OPPORTUNITIES_CSV
) -> List[Dict[str, Any]]:
    """
    Generates top N job role recommendations for a beneficiary profile,
    integrating local opportunity data safely.
    """
    jobs = load_nsqf_jobs(jobs_csv_path)
    if not jobs:
        return []

    opportunities = load_local_opportunities(opp_csv_path)

    # Normalize profile dictionary safely handling None values
    if isinstance(beneficiary_profile, dict):
        profile_dict = {
            "education": beneficiary_profile.get("education") or None,
            "skills": beneficiary_profile.get("skills") or [],
            "interests": beneficiary_profile.get("interests") or [],
            "mobility": beneficiary_profile.get("mobility"),
            "employment_preference": beneficiary_profile.get("employment_preference"),
            "district": beneficiary_profile.get("district") or beneficiary_profile.get("location"),
            "work_experience": beneficiary_profile.get("work_experience") or "",
            "current_occupation": beneficiary_profile.get("current_occupation") or "",
            "family_occupation": beneficiary_profile.get("family_occupation") or "",
            "aspirations": beneficiary_profile.get("aspirations") or "",
            "constraints": beneficiary_profile.get("constraints") or ""
        }
    else:
        profile_dict = {
            "education": getattr(beneficiary_profile, "education", "") or "",
            "skills": getattr(beneficiary_profile, "skills", []) or [],
            "interests": getattr(beneficiary_profile, "interests", []) or [],
            "mobility": getattr(beneficiary_profile, "mobility", None),
            "employment_preference": getattr(beneficiary_profile, "employment_preference", None),
            "district": getattr(beneficiary_profile, "district", None) or getattr(beneficiary_profile, "location", None),
            "work_experience": getattr(beneficiary_profile, "work_experience", "") or "",
            "current_occupation": getattr(beneficiary_profile, "current_occupation", "") or "",
            "family_occupation": getattr(beneficiary_profile, "family_occupation", "") or "",
            "aspirations": getattr(beneficiary_profile, "aspirations", "") or "",
            "constraints": getattr(beneficiary_profile, "constraints", "") or ""
        }

    missing_info = {
        "education": "known" if profile_dict.get("education") else "missing",
        "skills": "known" if profile_dict.get("skills") else "missing",
        "interests": "known" if profile_dict.get("interests") else "missing",
        "mobility": "known" if profile_dict.get("mobility") else "missing",
        "employment_preference": "known" if profile_dict.get("employment_preference") else "missing",
        "district": "known" if profile_dict.get("district") else "missing"
    }
    missing_count = sum(1 for v in missing_info.values() if v == "missing")

    recommendations = []

    for job in jobs:
        role_name = job.get("job_role", "")
        sector_name = job.get("sector", "")

        # Check local opportunity match
        opp_match = find_local_opportunity_match(
            profile_dict["district"],
            role_name,
            sector_name,
            opportunities
        )

        # Calculate scores out of 100
        scoring_res = calculate_total_score(
            profile_dict,
            job,
            has_local_opportunity=opp_match["has_opportunity"],
            is_exact_opportunity=opp_match.get("is_exact", False)
        )
        total_score = scoring_res["total_score"]
        confidence = scoring_res.get("confidence", "Weak Match")
        evidence = scoring_res.get("evidence", {"unknown_fields": 0})
        breakdown = scoring_res["breakdown"]

        # Skill Gap Analysis
        gap_res = analyze_skill_gap(profile_dict, job)

        # Build transparent rationale
        why_recommended = []
        for comp, data in breakdown.items():
            if comp == "constraints" and data.get("score", 0) < 0 and data.get("explanation"):
                why_recommended.append("⚠️ " + data.get("explanation"))
            elif data.get("score", 0) > 0 and data.get("explanation"):
                why_recommended.append("✅ " + data.get("explanation"))

        # Determine best fit employment mode
        pref = (profile_dict.get("employment_preference") or "").lower()
        if "self" in pref:
            emp_type = "Self-Employment"
        elif "wage" in pref or "job" in pref or "salaried" in pref:
            emp_type = "Wage-Employment"
        else:
            self_suit = job.get("self_employment_suitability", "Low")
            emp_type = "Self-Employment" if self_suit == "High" else "Wage-Employment"

        rec = {
            "job_role": role_name,
            "sector": sector_name,
            "nsqf_level": int(job.get("nsqf_level", 4)),
            "score": total_score,
            "confidence": confidence,
            "evidence": evidence,
            "score_breakdown": breakdown,  # Include full breakdown
            "matched_skills": gap_res["matched_skills"],
            "missing_skills": gap_res["missing_skills"],
            "skill_coverage": gap_res["skill_coverage_percentage"],
            "why_recommended": why_recommended,
            "employment_type": emp_type,
            "local_opportunity": opp_match["opportunity_info"],
            "local_opportunity_details": opp_match["details"],
            "missing_information": missing_info,
            "job_details": job
        }

        # Threshold Requirement: Do not recommend if score is extremely low or completely unrelated
        has_relevance_signal = (
            breakdown.get("skill", {}).get("score", 0) > 0 or 
            breakdown.get("interest", {}).get("score", 0) > 0
        )
        if total_score >= 45 and has_relevance_signal:
            recommendations.append(rec)

    # Sort descending by total score, then skill coverage, then alphabetically for determinism
    recommendations.sort(key=lambda x: (x["score"], x["skill_coverage"], x["job_role"]), reverse=True)

    # Threshold Check: Genuine missing information
    if missing_count >= 3:
        return [{
            "status": "insufficient_information",
            "missing_information": missing_info,
            "job_role": "Need more information",
            "sector": "Assessment Incomplete",
            "nsqf_level": 0,
            "score": recommendations[0]["score"] if recommendations else 0,
            "score_breakdown": recommendations[0]["score_breakdown"] if recommendations else {},
            "evidence": recommendations[0].get("evidence", {}) if recommendations else {},
            "matched_skills": [],
            "missing_skills": [],
            "skill_coverage": 0,
            "why_recommended": ["Insufficient evidence provided in the profile to make a high-confidence recommendation."],
            "employment_type": "Unknown",
            "local_opportunity": "Please provide more details about your skills, education, or experience.",
            "local_opportunity_details": None,
            "job_details": {}
        }]

    # Threshold Check: No strong match found in dataset despite complete profile
    if (recommendations and recommendations[0]["score"] < 50) or not recommendations:
        return [{
            "status": "no_strong_match",
            "missing_information": missing_info,
            "job_role": "No strong match found in the current NSQF prototype dataset.",
            "sector": "Data Limited",
            "nsqf_level": 0,
            "score": recommendations[0]["score"] if recommendations else 0,
            "score_breakdown": recommendations[0]["score_breakdown"] if recommendations else {},
            "evidence": recommendations[0].get("evidence", {}) if recommendations else {},
            "matched_skills": [],
            "missing_skills": [],
            "skill_coverage": 0,
            "why_recommended": ["The current prototype dataset does not contain a sufficiently aligned role for this profile. No unrelated role was recommended."],
            "employment_type": "Unknown",
            "local_opportunity": "No strong match found.",
            "local_opportunity_details": None,
            "job_details": {}
        }]

    return recommendations[:top_n]
