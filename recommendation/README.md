# Kaushal Marg: Recommendation Engine Documentation

Welcome to the documentation for the **Skill Intelligence & Recommendation Module** of **Kaushal Marg** (SIH Problem Statement 26097: *"Your Path to Skills & Livelihood"*).

This module is designed to be **simple, explainable, deterministic, and 100% transparent**. It does **NOT** use machine learning or opaque black-box APIs to ensure that every beneficiary and government skill counselor can understand exactly *why* a role was recommended.

---

## 1. System Architecture

```text
               +----------------------------------------+
               |      Beneficiary Profile Input         |
               | (Education, Skills, District, Interest) |
               +----------------------------------------+
                                   |
                                   v
               +----------------------------------------+
               |     Master Recommendation Engine       |
               |      (recommendation/matcher.py)       |
               +----------------------------------------+
                    /              |             \
                   /               |              \
                  v                v               v
      +------------------+  +--------------+  +-----------------------+
      |  data/nsqf_jobs  |  |  scoring.py  |  |  local_opportunities  |
      |   (23 Roles)     |  |  (Max 100)   |  |       (.csv)          |
      +------------------+  +--------------+  +-----------------------+
                  \                |                /
                   \               |               /
                    v              v              v
               +----------------------------------------+
               |   Skill Gap & Pathway Generators       |
               |     (skill_gap.py & pathway.py)        |
               +----------------------------------------+
                                   |
                                   v
               +----------------------------------------+
               |   Top 3 Job Roles + "My Skill Journey" |
               +----------------------------------------+
```

---

## 2. Purpose
The recommendation engine evaluates a beneficiary's profile against official National Skills Qualifications Framework (NSQF) job roles and local market opportunities. Its core goals are to:
1. Recommend the **top 3 best-fitting job roles**.
2. Perform a **skill-gap analysis** showing matched vs missing skills.
3. Generate **"My Skill Journey"**, a step-by-step career progression pathway.

---

## 3. Profile Input
The engine accepts a dictionary or object model containing:

```python
beneficiary_profile = {
    "education": "10th Pass",
    "skills": ["tractor operation", "basic farming"],
    "interests": ["Agriculture", "machinery"],
    "mobility": "Low",
    "employment_preference": "Self-Employment",
    "district": "Indore"
}
```

---

## 4. NSQF Job Dataset (`data/nsqf_jobs.csv`)
Stores 23 verified job roles aligned with official NSDC Sector Skill Councils (Green Jobs, Healthcare, Electronics, Apparel, Agriculture, etc.).

| Field | Description | Example |
| :--- | :--- | :--- |
| `job_role` | Official NSDC Job Role Title | `Solar PV Installer (Suryamitra)` |
| `sector` | Industry Sector | `Green Jobs` |
| `nsqf_level` | Competency Level (2 to 4) | `4` |
| `minimum_education` | Minimum Entry Education | `10th Pass + ITI` |
| `required_skills` | Pipe-delimited skill list | `Solar wiring\|PV module installation` |
| `mobility_requirement` | Required travel level | `District / State` |

---

## 5. Scoring System (Max 100 Points)

The scoring engine ([recommendation/scoring.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/scoring.py)) evaluates candidates across 6 criteria:

$$\text{Total Score} = \text{Education} + \text{Skill} + \text{Interest} + \text{Mobility} + \text{Employment Preference} + \text{Local Opportunity}$$

| Component | Max Points | Evaluation Logic |
| :--- | :---: | :--- |
| **Education Score** | **20** | Compares candidate's formal education rank against minimum role requirement. Full points if candidate meets/exceeds. |
| **Skill Score** | **25** | $\text{round}\left(\frac{\text{Matched Skills}}{\text{Total Required Skills}} \times 25\right)$. Measures percentage skill overlap. |
| **Interest Score** | **20** | Full points if candidate's expressed sector interests align with the job role's sector. |
| **Mobility Score** | **15** | Full points if candidate's travel willingness satisfies job location requirements. |
| **Employment Preference** | **10** | Matches user preference (Self-Employment vs Wage-Employment) with role suitability ratings. |
| **Local Opportunity** | **10** | Awarded ONLY when verified local vacancies or training centers exist in user's district. |

---

## 6. Skill Matching & Normalization

Skill string comparison ([recommendation/scoring.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/scoring.py)) performs:
1. **Normalization (`normalize_skill`):** Lowercases strings, removes extra spaces, and cleans special characters.
2. **Deduplication:** Converts input lists into unique sets.
3. **Domain Token Matching:** Matches skills based on exact equality, substrings, or non-stopword token overlap (e.g., `"tractor operation"` matches `"Tractor driving"` via the core token `"tractor"`).

---

## 7. Skill-Gap Analysis ([recommendation/skill_gap.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/skill_gap.py))

For every candidate role, the gap analyzer calculates:
* `matched_skills`: Skills the candidate already possesses.
* `missing_skills`: Required skills the candidate lacks.
* `skill_coverage_percentage`: Percentage of required skills satisfied ($\frac{\text{matched}}{\text{required}} \times 100$).

---

## 8. Local Opportunity Integration ([data/local_opportunities.csv](file:///d:/binary%20minds/Kaushal-Marg-Prototype/data/local_opportunities.csv))

* Reads candidate's `district` and checks local records.
* If a match is found in the district, adds up to **10 points** to the local opportunity score and includes opportunity metadata.
* If no data exists, outputs `"No verified local opportunity data available"` and awards **0 points**.
* Explicitly distinguishes prototype demonstration data (`"data_source_type": "Prototype Demo Data"`) from live APIs.

---

## 9. Top-3 Recommendation Logic ([recommendation/matcher.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/matcher.py))

1. Loops through all job roles in [data/nsqf_jobs.csv](file:///d:/binary%20minds/Kaushal-Marg-Prototype/data/nsqf_jobs.csv).
2. Computes total score and component breakdowns.
3. Generates transparent natural language explanations (`why_recommended`).
4. Sorts all roles in descending order by **Total Score** (using **Skill Coverage** as tie-breaker).
5. Returns top 3 recommendations.

---

## 10. "My Skill Journey" Pathway ([recommendation/pathway.py](file:///d:/binary%20minds/Kaushal-Marg-Prototype/recommendation/pathway.py))

Generates a structured career progression roadmap:
* `current_state`: Candidate's starting education and background summary.
* `foundation_skills`: Existing skills candidate brings forward.
* `skills_to_build`: Missing target skills required for the role.
* `training_stage`: Classroom theory modules.
* `practical_stage`: Hands-on lab/workshop training.
* `target_role`: Destination NSQF job role and level.

---

## 11. Example Calculation

Candidate from Indore (`10th Pass`, skill: `tractor operation`, goal: `Self-Employment`) evaluated against **Tractor Operator** (`8th Pass`, required skills: `Tractor driving|Implement hitching|Routine maintenance`):

```text
education             = 20/20  (10th Pass >= 8th Pass)
skills                =  8/25  (Matched 1 of 3 skills -> 33.3% * 25 = 8)
interest              = 20/20  (Agriculture sector match)
mobility              = 15/15  (Low mobility >= Local Rural requirement)
employment preference = 10/10  (Self-employment preference matched with High suitability)
local opportunity     = 10/10  (Active micro-enterprise cluster in Indore)

Total                 = 83/100 (RANK #1 RECOMMENDATION)
```

---

## 12. System Limitations
* **Rule-Based:** Uses deterministic scoring logic based on fixed weights rather than machine learning models.
* **Dataset Dependent:** Quality of recommendations depends directly on dataset accuracy in [data/nsqf_jobs.csv](file:///d:/binary%20minds/Kaushal-Marg-Prototype/data/nsqf_jobs.csv).
* **Prototype Data:** [data/local_opportunities.csv](file:///d:/binary%20minds/Kaushal-Marg-Prototype/data/local_opportunities.csv) contains demonstration records until integrated with live government APIs (e.g., Skill India Digital Hub / NCS).
