# Kaushal Marg: Recommendation Engine Integration Guide

This guide is for **Person 3 (UI / Streamlit Developer)** to easily connect the **Skill Intelligence & Recommendation Engine** to the Streamlit user interface.

---

## 1. Quick Start: Main Functions to Call

Person 3 can import and use three primary functions from the `recommendation` module:

```python
from recommendation.matcher import recommend_jobs
from recommendation.skill_gap import analyze_skill_gap
from recommendation.pathway import generate_skill_pathway
```

---

## 2. Required Input Format

Pass a standard Python dictionary representing the candidate's profile:

```python
beneficiary_profile = {
    "education": "10th Pass",                  # String e.g. "8th Pass", "10th Pass", "12th Pass", "ITI"
    "skills": ["tractor operation", "farming"], # List of string skills
    "interests": ["Agriculture"],             # List of sector interests e.g. ["Green Jobs", "Healthcare"]
    "mobility": "Low",                        # String e.g. "Local", "District Level", "State Wide"
    "employment_preference": "Self-Employment", # String e.g. "Self-Employment", "Wage-Employment", "Any"
    "district": "Indore"                       # String e.g. "Indore", "Jaipur", "Bhopal"
}
```

---

## 3. Main Function to Call: `recommend_jobs()`

### Signature:
```python
recommend_jobs(beneficiary_profile: dict, top_n: int = 3) -> list[dict]
```

### Streamlit Integration Example:
```python
import streamlit as st
from recommendation.matcher import recommend_jobs
from recommendation.pathway import generate_skill_pathway

# 1. Collect form inputs from Streamlit
user_profile = {
    "education": st.selectbox("Education Level", ["8th Pass", "10th Pass", "12th Pass", "ITI"]),
    "skills": [s.strip() for s in st.text_input("Existing Skills (comma-separated)", "tractor operation").split(",")],
    "interests": [st.selectbox("Interested Sector", ["Agriculture", "Green Jobs", "Apparel", "Healthcare"])],
    "mobility": st.radio("Mobility Preference", ["Local", "District Level", "State Wide"]),
    "employment_preference": st.radio("Goal", ["Self-Employment", "Wage-Employment", "Any"]),
    "district": st.text_input("Home District", "Indore")
}

# 2. Get Top 3 Recommendations
if st.button("Generate Recommendations"):
    recommendations = recommend_jobs(user_profile, top_n=3)
    
    for rank, job in enumerate(recommendations, 1):
        st.subheader(f"#{rank} {job['job_role']} ({job['score']}/100 Score)")
        st.write(f"**Sector:** {job['sector']} | **Mode:** {job['employment_type']}")
        st.write(f"**Local Opportunity:** {job['local_opportunity']}")
        st.write(f"**Matched Skills:** {', '.join(job['matched_skills']) if job['matched_skills'] else 'None'}")
        st.write(f"**Missing Skills:** {', '.join(job['missing_skills'])}")
        
        # 3. Generate Skill Pathway for top job
        pathway = generate_skill_pathway(user_profile, job, job['missing_skills'])
        with st.expander("View My Skill Journey"):
            st.json(pathway)
```

---

## 4. Expected Output Format

`recommend_jobs()` returns a Python list of dictionaries (sorted by score descending):

```python
[
    {
        "job_role": "Tractor Operator",
        "sector": "Agriculture",
        "score": 83,
        "matched_skills": ["Tractor driving"],
        "missing_skills": ["Routine maintenance", "Implement hitching"],
        "skill_coverage": 33.33,
        "why_recommended": [
            "Education (10th Pass) meets or exceeds job requirement (8th Pass).",
            "Matched 1 of 3 required skills (33.3% coverage).",
            "Job sector (Agriculture) matches beneficiary interest (agriculture).",
            "Beneficiary mobility (Low) satisfies job requirement (Local (Rural)).",
            "Beneficiary prefers self-employment; role self-employment suitability is High.",
            "Active local job vacancies or training centers found in beneficiary's district."
        ],
        "employment_type": "Self-Employment",
        "local_opportunity": "Local Micro-Enterprise / Self-Employment available in Indore (High Demand)",
        "local_opportunity_details": {
            "district": "Indore",
            "opportunity_type": "Micro-Enterprise / Self-Employment",
            "demand_level": "High",
            "source": "District Skill Committee Prototype",
            "data_source_type": "Prototype Demo Data",
            "last_updated": "2026-09-01"
        }
    },
    ...
]
```

---

## 5. Secondary Utility Functions

### A. Skill Gap Analysis ([recommendation/skill_gap.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/skill_gap.py))
```python
from recommendation.skill_gap import analyze_skill_gap

gap_report = analyze_skill_gap(user_profile, job_dict)
# Returns: {"job_role": str, "matched_skills": list, "missing_skills": list, "skill_coverage_percentage": float, "summary": str}
```

### B. Skill Journey Pathway ([recommendation/pathway.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/pathway.py))
```python
from recommendation.pathway import generate_skill_pathway

pathway = generate_skill_pathway(user_profile, job_dict, job_dict["missing_skills"])
# Returns: {"current_state": str, "foundation_skills": list, "skills_to_build": list, "training_stage": dict, "practical_stage": dict, "target_role": dict}
```

---

## 6. Required CSV Files

The recommendation module requires these two datasets located in the `data/` folder:
1. **[data/nsqf_jobs.csv](file:///d:/binary%20minds/Kaushal-Marg-Prototype/data/nsqf_jobs.csv):** Verified NSQF job roles and qualification criteria.
2. **[data/local_opportunities.csv](file:///d:/binary%20minds/Kaushal-Marg-Prototype/data/local_opportunities.csv):** Local market vacancies and vocational training center records.

---

## 7. Required Python Dependencies

Uses standard Python built-in modules only:
* `csv`
* `os`
* `sys`
* `typing`

No extra `pip` packages (like scikit-learn, numpy, or pandas) are needed.

---

## 8. Error & Fallback Behavior

* **Missing / Empty Inputs:** If any profile attribute (e.g. `education`, `district`, `skills`) is `None` or empty, the engine handles it safely without crashing.
* **Missing Location Data:** If the candidate's district has no local opportunities recorded, the engine outputs `"No verified local opportunity data available"`, sets `local_opportunity_details: None`, and deducts 10 local points safely.
* **Missing Dataset File:** If a CSV dataset path is invalid or missing, `recommend_jobs()` returns an empty list `[]` instead of raising an unhandled exception.
