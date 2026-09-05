"""
Kaushal Marg - Database Module (SQLite)
Provides persistent storage for beneficiaries, profiles, conversations, and NSQF recommendations.
Uses parameterized queries to ensure security and clean data integrity.

Team: Binary Minds | SIH Problem Statement 26097
"""

import sqlite3
import json
import os
import random
import string
from datetime import datetime
from typing import List, Dict, Any, Optional

# Default SQLite database path in the project root
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kaushal_marg.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database with Foreign Key support enabled.
    """
    target_path = db_path if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initializes the database schema from schema.sql and handles migrations.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Create a lightweight schema_versions table to track migrations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Read and execute the canonical schema
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)

    # 3. Lightweight schema migration for existing databases
    cursor.execute("SELECT MAX(version) FROM schema_versions")
    row = cursor.fetchone()
    current_version = row[0] if row[0] is not None else 0

    if current_version < 1:
        # Version 1: Add new profile fields if they don't exist
        try:
            cursor.execute("SELECT age FROM profiles LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating profiles schema to include new fields...")
            try:
                # Execute each alter table within the transaction
                cursor.execute("ALTER TABLE profiles ADD COLUMN age INTEGER;")
                cursor.execute("ALTER TABLE profiles ADD COLUMN current_occupation TEXT;")
                cursor.execute("ALTER TABLE profiles ADD COLUMN work_experience TEXT;")
                cursor.execute("ALTER TABLE profiles ADD COLUMN family_occupation TEXT;")
                cursor.execute("ALTER TABLE profiles ADD COLUMN aspirations TEXT;")
                cursor.execute("ALTER TABLE profiles ADD COLUMN local_context TEXT;")
                cursor.execute("ALTER TABLE profiles ADD COLUMN constraints TEXT;")
            except sqlite3.OperationalError as e:
                print(f"Migration error (could be partial): {e}")
        
        cursor.execute("INSERT INTO schema_versions (version) VALUES (1)")

    conn.commit()
    conn.close()


def generate_beneficiary_id(district: Optional[str] = None) -> str:
    """
    Generates a clean, unique, human-readable beneficiary ID.
    Example: 'KM-IND-8421' (for Indore) or 'KM-GIA-3912'.
    """
    prefix = "KM"
    dist_code = "GIA"
    
    if district:
        clean_dist = district.strip().upper()
        if "INDORE" in clean_dist or clean_dist.startswith("IND"):
            dist_code = "IND"
        elif "JAIPUR" in clean_dist or clean_dist.startswith("JAI") or clean_dist.startswith("JPR"):
            dist_code = "JPR"
        elif "BHOPAL" in clean_dist or clean_dist.startswith("BHO") or clean_dist.startswith("BPL"):
            dist_code = "BPL"
        elif "LUCKNOW" in clean_dist or clean_dist.startswith("LUC") or clean_dist.startswith("LKW"):
            dist_code = "LKW"
        elif "PATNA" in clean_dist or clean_dist.startswith("PAT"):
            dist_code = "PAT"
        elif "UDAIPUR" in clean_dist or clean_dist.startswith("UDA"):
            dist_code = "UDA"
        elif len(clean_dist) >= 3:
            dist_code = clean_dist[:3]

    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{dist_code}-{random_suffix}"


def save_assessment_transaction(
    beneficiary_id: str,
    profile_data: Dict[str, Any],
    recommendations_list: List[Dict[str, Any]],
    db_path: Optional[str] = None
) -> None:
    """
    Saves a profile and its recommendations in a single atomic transaction.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        
        # 1. Prepare profile data
        skills_list = profile_data.get("skills", [])
        if not isinstance(skills_list, list): skills_list = []
        interests_list = profile_data.get("interests", [])
        if not isinstance(interests_list, list): interests_list = []
        
        age = profile_data.get("age")
        if age is not None:
            try: age = int(age)
            except (ValueError, TypeError): age = None

        district = profile_data.get("district")
        if district:
            district = str(district).strip()
            
        cursor.execute(
            """
            INSERT INTO profiles (
                beneficiary_id, age, education, current_occupation, work_experience, family_occupation,
                skills_json, interests_json, aspirations, district, local_context, mobility, 
                employment_preference, constraints, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
            """,
            (
                beneficiary_id,
                age,
                str(profile_data.get("education", "")).strip() if profile_data.get("education") else None,
                str(profile_data.get("current_occupation", "")).strip() if profile_data.get("current_occupation") else None,
                str(profile_data.get("work_experience", "")).strip() if profile_data.get("work_experience") else None,
                str(profile_data.get("family_occupation", "")).strip() if profile_data.get("family_occupation") else None,
                json.dumps(skills_list, ensure_ascii=False),
                json.dumps(interests_list, ensure_ascii=False),
                str(profile_data.get("aspirations", "")).strip() if profile_data.get("aspirations") else None,
                district,
                str(profile_data.get("local_context", "")).strip() if profile_data.get("local_context") else None,
                str(profile_data.get("mobility")).strip() if profile_data.get("mobility") else None,
                str(profile_data.get("employment_preference")).strip() if profile_data.get("employment_preference") else None,
                str(profile_data.get("constraints", "")).strip() if profile_data.get("constraints") else None
            )
        )
        
        if district:
            cursor.execute(
                "UPDATE beneficiaries SET district = ?, updated_at = CURRENT_TIMESTAMP WHERE beneficiary_id = ?;",
                (district, beneficiary_id)
            )

        # 2. Insert Recommendations
        for idx, rec in enumerate(recommendations_list, start=1):
            job_role = str(rec.get("job_role", "Unknown Role")).strip()
            sector = str(rec.get("sector", "General")).strip()
            
            try: nsqf_level = int(rec.get("nsqf_level", 4))
            except (ValueError, TypeError): nsqf_level = 4
            
            try: match_score = float(rec.get("score", rec.get("total_score", rec.get("match_score", 0.0))))
            except (ValueError, TypeError): match_score = 0.0
            
            skill_gap = rec.get("skill_gap", {})
            if not isinstance(skill_gap, dict): skill_gap = {}
            skill_gap_json = json.dumps(skill_gap, ensure_ascii=False)
            
            local_opp = str(rec.get("local_opportunity", "")).strip() if rec.get("local_opportunity") else None

            cursor.execute(
                """
                INSERT INTO recommendations (
                    beneficiary_id, rank_position, job_role, sector, nsqf_level, match_score, skill_gap_json, local_opportunity, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
                """,
                (beneficiary_id, idx, job_role, sector, nsqf_level, match_score, skill_gap_json, local_opp)
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_beneficiary(
    name: str,
    preferred_language: str = "hi",
    district: Optional[str] = None,
    beneficiary_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> str:
    """
    Registers a new beneficiary in the database using parameterized SQL.
    Returns the unique beneficiary_id.
    """
    if not beneficiary_id:
        beneficiary_id = generate_beneficiary_id(district)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO beneficiaries (beneficiary_id, name, preferred_language, district, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """,
            (beneficiary_id, name.strip(), preferred_language, district.strip() if district else None)
        )
        
        conn.commit()
    finally:
        conn.close()
    return beneficiary_id


def save_profile(
    beneficiary_id: str,
    age: Optional[int] = None,
    education: Optional[str] = None,
    current_occupation: Optional[str] = None,
    work_experience: Optional[str] = None,
    family_occupation: Optional[str] = None,
    skills: Optional[List[str]] = None,
    interests: Optional[List[str]] = None,
    aspirations: Optional[str] = None,
    district: Optional[str] = None,
    local_context: Optional[str] = None,
    mobility: Optional[str] = None,
    employment_preference: Optional[str] = None,
    constraints: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    """
    Saves or updates a beneficiary's skilling profile using parameterized SQL.
    Returns the profile_id.
    """
    skills_list = skills if isinstance(skills, list) else []
    interests_list = interests if isinstance(interests, list) else []
    
    skills_json = json.dumps(skills_list, ensure_ascii=False)
    interests_json = json.dumps(interests_list, ensure_ascii=False)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO profiles (
                beneficiary_id, age, education, current_occupation, work_experience, family_occupation,
                skills_json, interests_json, aspirations, district, local_context, mobility, 
                employment_preference, constraints, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
            """,
            (
                beneficiary_id, age, education, current_occupation, work_experience, family_occupation,
                skills_json, interests_json, aspirations, district, local_context,
                mobility, employment_preference, constraints
            )
        )
        profile_id = cursor.lastrowid

        # Also update district in beneficiaries table if supplied
        if district:
            cursor.execute(
                "UPDATE beneficiaries SET district = ?, updated_at = CURRENT_TIMESTAMP WHERE beneficiary_id = ?;",
                (district, beneficiary_id)
            )

        conn.commit()
    finally:
        conn.close()
    return profile_id


def get_profile(beneficiary_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the latest skilling profile for a beneficiary.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.*, b.name, b.preferred_language 
            FROM profiles p
            JOIN beneficiaries b ON p.beneficiary_id = b.beneficiary_id
            WHERE p.beneficiary_id = ?
            ORDER BY p.profile_id DESC
            LIMIT 1;
            """,
            (beneficiary_id,)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    try:
        skills = json.loads(row["skills_json"])
    except Exception:
        skills = []

    try:
        interests = json.loads(row["interests_json"])
    except Exception:
        interests = []

    return {
        "profile_id": row["profile_id"],
        "beneficiary_id": row["beneficiary_id"],
        "name": row["name"],
        "preferred_language": row["preferred_language"],
        "age": row["age"],
        "education": row["education"],
        "current_occupation": row["current_occupation"],
        "work_experience": row["work_experience"],
        "family_occupation": row["family_occupation"],
        "skills": skills,
        "interests": interests,
        "aspirations": row["aspirations"],
        "district": row["district"],
        "local_context": row["local_context"],
        "mobility": row["mobility"],
        "employment_preference": row["employment_preference"],
        "constraints": row["constraints"],
        "created_at": row["created_at"]
    }


def save_conversation(
    beneficiary_id: str,
    sender: str,
    message_text: str,
    input_mode: str = "voice",
    db_path: Optional[str] = None
) -> int:
    """
    Saves an interview conversation turn (voice/text) using parameterized SQL.
    Returns the conversation_id.
    """
    if sender not in ("user", "assistant"):
        sender = "user"
    if input_mode not in ("voice", "text"):
        input_mode = "voice"

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversations (beneficiary_id, sender, message_text, input_mode, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
            """,
            (beneficiary_id, sender, message_text.strip(), input_mode)
        )
        conv_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return conv_id


def get_conversation_history(beneficiary_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves full conversation history for a beneficiary in chronological order.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT conversation_id, beneficiary_id, sender, message_text, input_mode, timestamp
            FROM conversations
            WHERE beneficiary_id = ?
            ORDER BY conversation_id ASC;
            """,
            (beneficiary_id,)
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [
        {
            "conversation_id": row["conversation_id"],
            "beneficiary_id": row["beneficiary_id"],
            "sender": row["sender"],
            "message_text": row["message_text"],
            "input_mode": row["input_mode"],
            "timestamp": row["timestamp"]
        }
        for row in rows
    ]


def save_recommendation(
    beneficiary_id: str,
    job_role: str,
    sector: str,
    nsqf_level: int,
    match_score: float,
    rank_position: int = 1,
    skill_gap: Optional[Dict[str, Any]] = None,
    local_opportunity: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    """
    Saves a single NSQF recommendation for a beneficiary using parameterized SQL.
    """
    skill_gap_json = json.dumps(skill_gap if skill_gap else {}, ensure_ascii=False)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO recommendations (
                beneficiary_id, rank_position, job_role, sector, nsqf_level, match_score, skill_gap_json, local_opportunity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
            """,
            (beneficiary_id, rank_position, job_role, sector, nsqf_level, match_score, skill_gap_json, local_opportunity)
        )
        rec_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return rec_id


def save_recommendations_batch(
    beneficiary_id: str,
    recommendations_list: List[Dict[str, Any]],
    db_path: Optional[str] = None
) -> List[int]:
    """
    Saves a batch of top recommendations for a beneficiary.
    """
    inserted_ids = []
    for idx, rec in enumerate(recommendations_list, start=1):
        job_role = rec.get("job_role", "Unknown Role")
        sector = rec.get("sector", "General")
        nsqf_level = int(rec.get("nsqf_level", 4))
        match_score = float(rec.get("score", rec.get("total_score", rec.get("match_score", 0.0))))
        skill_gap = rec.get("skill_gap", {})
        local_opp = rec.get("local_opportunity", "")
        
        rec_id = save_recommendation(
            beneficiary_id=beneficiary_id,
            job_role=job_role,
            sector=sector,
            nsqf_level=nsqf_level,
            match_score=match_score,
            rank_position=idx,
            skill_gap=skill_gap,
            local_opportunity=local_opp,
            db_path=db_path
        )
        inserted_ids.append(rec_id)
    return inserted_ids


def get_recommendations(beneficiary_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all recommendations stored for a beneficiary, ordered by rank.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT recommendation_id, beneficiary_id, rank_position, job_role, sector, nsqf_level, match_score, skill_gap_json, local_opportunity, created_at
        FROM recommendations
        WHERE beneficiary_id = ?
        ORDER BY rank_position ASC;
        """,
        (beneficiary_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        try:
            skill_gap = json.loads(row["skill_gap_json"])
        except Exception:
            skill_gap = {}
            
        results.append({
            "recommendation_id": row["recommendation_id"],
            "beneficiary_id": row["beneficiary_id"],
            "rank_position": row["rank_position"],
            "job_role": row["job_role"],
            "sector": row["sector"],
            "nsqf_level": row["nsqf_level"],
            "match_score": row["match_score"],
            "skill_gap": skill_gap,
            "local_opportunity": row["local_opportunity"],
            "created_at": row["created_at"]
        })
    return results


def seed_demo_database(db_path: str = "demo_kaushal_marg.db") -> int:
    """
    Seeds a separate demo SQLite database with realistic synthetic beneficiary records
    for demonstration. Never touches the real production database.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM beneficiaries;")
    count = cursor.fetchone()[0]
    conn.close()

    if count >= 24: # We insert 24 records below
        return count

    # 24 Realistic Synthetic SC Beneficiary Profiles for Prototype Demonstration
    sample_cohort = [
        {"name": "Ramesh Kumar", "lang": "hi", "dist": "Indore", "edu": "10th Pass", "skills": ["Tractor operation", "Basic farming"], "interests": ["Agriculture", "Machinery"], "pref": "Self-Employment", "role": "Tractor Operator", "sec": "Agriculture", "nsqf": 4, "score": 83.0, "gap": {"matched_skills": ["Tractor driving"], "missing_skills": ["Implement hitching", "Routine maintenance"]}},
        {"name": "Sunita Devi", "lang": "hi", "dist": "Jaipur", "edu": "12th Pass", "skills": ["Basic electrical wiring", "Tool handling"], "interests": ["Green Jobs", "Solar Energy"], "pref": "Wage-Employment", "role": "Solar PV Installer (Suryamitra)", "sec": "Green Jobs", "nsqf": 4, "score": 78.0, "gap": {"matched_skills": ["Electrical wiring"], "missing_skills": ["PV module installation", "Inverter setup"]}},
        {"name": "Pooja Verma", "lang": "hi", "dist": "Bhopal", "edu": "8th Pass", "skills": ["Hand embroidery", "Basic tailoring"], "interests": ["Apparel & Handicrafts"], "pref": "Self-Employment", "role": "Self Employed Tailor", "sec": "Apparel & Home Furnishing", "nsqf": 4, "score": 85.0, "gap": {"matched_skills": ["Hand embroidery", "Basic stitching"], "missing_skills": ["Pattern drafting"]}},
        {"name": "Amit Paswan", "lang": "hi", "dist": "Lucknow", "edu": "10th Pass", "skills": ["House wiring", "Appliance repair"], "interests": ["Construction / Power"], "pref": "Wage-Employment", "role": "Assistant Electrician", "sec": "Construction", "nsqf": 3, "score": 82.0, "gap": {"matched_skills": ["House wiring"], "missing_skills": ["Safety grounding", "Conduit laying"]}},
        {"name": "Manoj Meghwal", "lang": "en", "dist": "Jaipur", "edu": "10th Pass", "skills": ["Pipe fitting", "Plumbing tools"], "interests": ["Plumbing", "Sanitation"], "pref": "Self-Employment", "role": "Plumber General", "sec": "Plumbing", "nsqf": 3, "score": 80.0, "gap": {"matched_skills": ["Pipe cutting"], "missing_skills": ["PVC jointing", "Pressure testing"]}},
        {"name": "Kavita Jatav", "lang": "hi", "dist": "Indore", "edu": "12th Pass", "skills": ["Basic healthcare", "Patient care"], "interests": ["Healthcare"], "pref": "Wage-Employment", "role": "General Duty Assistant (GDA)", "sec": "Healthcare", "nsqf": 4, "score": 86.0, "gap": {"matched_skills": ["Patient care"], "missing_skills": ["Vital signs recording", "Infection control"]}},
        {"name": "Rajesh Ahirwar", "lang": "hi", "dist": "Bhopal", "edu": "10th Pass", "skills": ["Two wheeler repair", "Engine oil change"], "interests": ["Automotive"], "pref": "Self-Employment", "role": "Auto Service Technician (2W/3W)", "sec": "Automotive", "nsqf": 4, "score": 79.0, "gap": {"matched_skills": ["Oil change", "Brake tuning"], "missing_skills": ["Electrical diagnosis", "EFI tuning"]}},
        {"name": "Rekha Baitha", "lang": "hi", "dist": "Patna", "edu": "8th Pass", "skills": ["Hand embroidery", "Crochet work"], "interests": ["Handicrafts"], "pref": "Self-Employment", "role": "Hand Embroiderer", "sec": "Handicrafts", "nsqf": 3, "score": 88.0, "gap": {"matched_skills": ["Hand embroidery"], "missing_skills": ["Color composition"]}},
        {"name": "Vikram Kori", "lang": "en", "dist": "Lucknow", "edu": "12th Pass", "skills": ["Computer typing", "MS Excel"], "interests": ["IT-ITeS"], "pref": "Wage-Employment", "role": "Data Entry Operator (DEO)", "sec": "IT-ITeS", "nsqf": 4, "score": 84.0, "gap": {"matched_skills": ["Typing speed"], "missing_skills": ["Data cleansing", "Form formatting"]}},
        {"name": "Deepak Valmiki", "lang": "hi", "dist": "Indore", "edu": "10th Pass", "skills": ["Masonry", "Cement plastering"], "interests": ["Construction"], "pref": "Wage-Employment", "role": "Mason General", "sec": "Construction", "nsqf": 3, "score": 81.0, "gap": {"matched_skills": ["Plastering"], "missing_skills": ["Brick alignment", "Tile fixing"]}},
        {"name": "Priyanka Sonkar", "lang": "hi", "dist": "Lucknow", "edu": "12th Pass", "skills": ["Sales talk", "Inventory counting"], "interests": ["Retail"], "pref": "Wage-Employment", "role": "Retail Sales Associate", "sec": "Retail", "nsqf": 4, "score": 76.0, "gap": {"matched_skills": ["Customer greeting"], "missing_skills": ["POS terminal operation", "Stock display"]}},
        {"name": "Suresh Bunkar", "lang": "hi", "dist": "Udaipur", "edu": "10th Pass", "skills": ["Organic composting", "Crop harvesting"], "interests": ["Agriculture"], "pref": "Self-Employment", "role": "Organic Grower", "sec": "Agriculture", "nsqf": 4, "score": 85.0, "gap": {"matched_skills": ["Composting"], "missing_skills": ["Organic certification", "Bio-pest management"]}},
        {"name": "Anjali Gautam", "lang": "en", "dist": "Patna", "edu": "12th Pass", "skills": ["Client communication", "Calling skills"], "interests": ["IT-ITeS"], "pref": "Wage-Employment", "role": "Customer Care Executive", "sec": "IT-ITeS", "nsqf": 4, "score": 77.0, "gap": {"matched_skills": ["Voice clarity"], "missing_skills": ["CRM software handling", "Query ticketing"]}},
        {"name": "Dinesh Chamar", "lang": "hi", "dist": "Bhopal", "edu": "10th Pass", "skills": ["Dairy cattle care", "Milk testing"], "interests": ["Agriculture"], "pref": "Self-Employment", "role": "Dairy Farmer / Milk Collector", "sec": "Agriculture", "nsqf": 3, "score": 82.0, "gap": {"matched_skills": ["Milking"], "missing_skills": ["Fat testing meter", "Cold chain storage"]}},
        {"name": "Geeta Bharti", "lang": "hi", "dist": "Jaipur", "edu": "10th Pass", "skills": ["Makeup basics", "Threading"], "interests": ["Beauty & Wellness"], "pref": "Self-Employment", "role": "Beauty Therapist", "sec": "Beauty & Wellness", "nsqf": 4, "score": 84.0, "gap": {"matched_skills": ["Threading"], "missing_skills": ["Skin therapy", "Equipment sterilization"]}},
        {"name": "Ravi Shastri", "lang": "hi", "dist": "Indore", "edu": "12th Pass", "skills": ["CCTV wiring", "Drill handling"], "interests": ["Electronics"], "pref": "Wage-Employment", "role": "CCTV Installation Technician", "sec": "Electronics", "nsqf": 4, "score": 80.0, "gap": {"matched_skills": ["Drill handling"], "missing_skills": ["IP camera networking", "NVR configuration"]}},
        {"name": "Neetu Bairwa", "lang": "hi", "dist": "Udaipur", "edu": "8th Pass", "skills": ["Garment sewing", "Button fixing"], "interests": ["Apparel & Home Furnishing"], "pref": "Self-Employment", "role": "Sewing Machine Operator", "sec": "Apparel & Home Furnishing", "nsqf": 3, "score": 87.0, "gap": {"matched_skills": ["Basic stitching"], "missing_skills": ["Overlock machine operation"]}},
        {"name": "Santosh Katheria", "lang": "hi", "dist": "Lucknow", "edu": "10th Pass", "skills": ["Package scanning", "Bike driving"], "interests": ["Logistics"], "pref": "Wage-Employment", "role": "Courier Delivery Executive", "sec": "Logistics", "nsqf": 3, "score": 78.0, "gap": {"matched_skills": ["Route navigation"], "missing_skills": ["Delivery app cash collection", "Barcode scanning"]}},
        {"name": "Kamla Dhobi", "lang": "hi", "dist": "Patna", "edu": "5th Pass", "skills": ["House cleaning", "Linen washing"], "interests": ["Domestic Services"], "pref": "Wage-Employment", "role": "Housekeeping Executive", "sec": "Domestic Workers", "nsqf": 2, "score": 81.0, "gap": {"matched_skills": ["Cleaning"], "missing_skills": ["Chemical dilution safety", "Vacuum operation"]}},
        {"name": "Mahesh Sankhla", "lang": "en", "dist": "Jaipur", "edu": "Graduate", "skills": ["Loan assessment", "Field recovery"], "interests": ["BFSI"], "pref": "Wage-Employment", "role": "Microfinance Executive", "sec": "BFSI", "nsqf": 4, "score": 79.0, "gap": {"matched_skills": ["Basic math"], "missing_skills": ["Credit appraisal norms", "SHG group formation"]}},
        {"name": "Seema Arya", "lang": "hi", "dist": "Bhopal", "edu": "12th Pass", "skills": ["Home appliance checking", "Multimeter use"], "interests": ["Electronics"], "pref": "Wage-Employment", "role": "Field Technician - Home Appliances", "sec": "Electronics", "nsqf": 4, "score": 83.0, "gap": {"matched_skills": ["Multimeter use"], "missing_skills": ["Refrigerator gas charging", "PCB fault finding"]}},
        {"name": "Mohan Lal", "lang": "hi", "dist": "Indore", "edu": "10th Pass", "skills": ["Food service", "Table setting"], "interests": ["Tourism & Hospitality"], "pref": "Wage-Employment", "role": "Food & Beverage Service Associate", "sec": "Tourism & Hospitality", "nsqf": 4, "score": 75.0, "gap": {"matched_skills": ["Table setting"], "missing_skills": ["Menu presentation", "Order taking etiquette"]}},
        {"name": "Gita Devi", "lang": "hi", "dist": "Patna", "edu": "8th Pass", "skills": ["Package sorting", "Box labeling"], "interests": ["Logistics"], "pref": "Wage-Employment", "role": "Warehouse Packer", "sec": "Logistics", "nsqf": 3, "score": 80.0, "gap": {"matched_skills": ["Box folding"], "missing_skills": ["Shrink wrap machine", "Inventory counting"]}},
        {"name": "Arun Kumar", "lang": "hi", "dist": "Udaipur", "edu": "10th Pass", "skills": ["Solar panel mounting", "Basic tools"], "interests": ["Green Jobs"], "pref": "Self-Employment", "role": "Solar PV Installer (Suryamitra)", "sec": "Green Jobs", "nsqf": 4, "score": 81.0, "gap": {"matched_skills": ["Panel mounting"], "missing_skills": ["Inverter wiring", "Safety earthing"]}}
    ]

    for item in sample_cohort:
        b_id = create_beneficiary(
            name=item["name"],
            preferred_language=item["lang"],
            district=item["dist"],
            db_path=db_path
        )
        save_profile(
            beneficiary_id=b_id,
            education=item["edu"],
            skills=item["skills"],
            interests=item["interests"],
            district=item["dist"],
            employment_preference=item["pref"],
            db_path=db_path
        )
        save_recommendation(
            beneficiary_id=b_id,
            job_role=item["role"],
            sector=item["sec"],
            nsqf_level=item["nsqf"],
            match_score=item["score"],
            rank_position=1,
            skill_gap=item["gap"],
            local_opportunity=f"Active cluster in {item['dist']} (Potential PM-AJAY Pathway)",
            db_path=db_path
        )

    return len(sample_cohort)


def get_filtered_dashboard_data(
    selected_language: Optional[str] = None,
    selected_district: Optional[str] = None,
    selected_sector: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves filtered aggregated metrics and distributions for the Admin Dashboard using parameterized SQL.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Build WHERE conditions
    where_clauses = []
    params = []

    if selected_language and selected_language not in ("All Languages", "All", ""):
        if "हिंदी" in selected_language or "hi" in selected_language.lower():
            code = "hi"
        elif "मराठी" in selected_language or "marathi" in selected_language.lower() or "mr" in selected_language.lower():
            code = "mr"
        else:
            code = "en"
        where_clauses.append("b.preferred_language = ?")
        params.append(code)

    if selected_district and selected_district not in ("All Districts", "All", ""):
        clean_dist = selected_district.split(" ")[0].strip()
        where_clauses.append("b.district LIKE ?")
        params.append(f"%{clean_dist}%")

    if selected_sector and selected_sector not in ("All Sectors", "All", ""):
        where_clauses.append("r.sector = ?")
        params.append(selected_sector.strip())

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # 1. Total Filtered Beneficiaries
    query_total = f"""
        SELECT COUNT(DISTINCT b.beneficiary_id)
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql};
    """
    cursor.execute(query_total, params)
    total_beneficiaries = cursor.fetchone()[0]

    # 2. Language Distribution
    query_lang = f"""
        SELECT 
            CASE 
                WHEN b.preferred_language = 'hi' THEN 'Hindi (हिंदी)' 
                WHEN b.preferred_language = 'mr' THEN 'Marathi (मराठी)' 
                ELSE 'English' 
            END as lang_label,
            COUNT(DISTINCT b.beneficiary_id) as count
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        GROUP BY lang_label
        ORDER BY count DESC;
    """
    cursor.execute(query_lang, params)
    language_dist = {row["lang_label"]: row["count"] for row in cursor.fetchall()}

    # 3. Education Distribution
    query_edu = f"""
        SELECT 
            COALESCE(p.education, 'Not Specified') as edu_level,
            COUNT(DISTINCT b.beneficiary_id) as count
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        GROUP BY edu_level
        ORDER BY count DESC;
    """
    cursor.execute(query_edu, params)
    education_dist = {row["edu_level"]: row["count"] for row in cursor.fetchall()}

    # 4. Top Recommended Sectors
    query_sec = f"""
        SELECT 
            COALESCE(r.sector, 'General') as sec_name,
            COUNT(DISTINCT b.beneficiary_id) as count
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        GROUP BY sec_name
        ORDER BY count DESC;
    """
    cursor.execute(query_sec, params)
    sector_dist = {row["sec_name"]: row["count"] for row in cursor.fetchall()}

    # 5. Top Recommended Job Roles
    query_roles = f"""
        SELECT 
            COALESCE(r.job_role, 'Pending Assessment') as role_name,
            COUNT(DISTINCT b.beneficiary_id) as count
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        GROUP BY role_name
        ORDER BY count DESC
        LIMIT 6;
    """
    cursor.execute(query_roles, params)
    top_roles_dist = {row["role_name"]: row["count"] for row in cursor.fetchall()}

    # 6. District Distribution
    query_dist = f"""
        SELECT 
            COALESCE(b.district, 'Unspecified') as dist_name,
            COUNT(DISTINCT b.beneficiary_id) as count
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        GROUP BY dist_name
        ORDER BY count DESC;
    """
    cursor.execute(query_dist, params)
    district_dist = {row["dist_name"]: row["count"] for row in cursor.fetchall()}

    # 7. Employment Preference (Self-Employment vs Wage-Employment)
    query_pref = f"""
        SELECT 
            CASE 
                WHEN p.employment_preference LIKE '%Self%' THEN 'Self-Employment'
                WHEN p.employment_preference LIKE '%Wage%' OR p.employment_preference LIKE '%Job%' OR p.employment_preference LIKE '%Salaried%' THEN 'Wage-Employment'
                WHEN p.employment_preference LIKE '%Any%' THEN 'Any'
                ELSE 'Unknown'
            END as pref_label,
            COUNT(DISTINCT b.beneficiary_id) as count
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        GROUP BY pref_label
        ORDER BY count DESC;
    """
    cursor.execute(query_pref, params)
    pref_dist = {row["pref_label"]: row["count"] for row in cursor.fetchall()}

    # 8. Average Match Score & Average Missing Skills (Skill Gap)
    query_gap = f"""
        SELECT 
            AVG(r.match_score) as avg_score,
            r.skill_gap_json
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql};
    """
    cursor.execute(query_gap, params)
    gap_rows = cursor.fetchall()
    
    # Calculate average match score and most common missing skills
    avg_score = 0.0
    missing_skill_counts = {}
    interests_counts = {}

    if gap_rows and gap_rows[0]["avg_score"] is not None:
        avg_score = round(gap_rows[0]["avg_score"], 1)

    # 9. Extract Common Interests and Missing Skills from raw JSON in filtered subset
    query_raw_json = f"""
        SELECT p.interests_json, r.skill_gap_json
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql};
    """
    cursor.execute(query_raw_json, params)
    for row in cursor.fetchall():
        # Interests
        if row["interests_json"]:
            try:
                ints = json.loads(row["interests_json"])
                for i in ints:
                    clean_i = i.strip()
                    interests_counts[clean_i] = interests_counts.get(clean_i, 0) + 1
            except Exception:
                pass
        # Missing skills
        if row["skill_gap_json"]:
            try:
                sg = json.loads(row["skill_gap_json"])
                for ms in sg.get("missing_skills", []):
                    clean_ms = ms.strip()
                    missing_skill_counts[clean_ms] = missing_skill_counts.get(clean_ms, 0) + 1
            except Exception:
                pass

    # Sort interests and missing skills
    sorted_interests = dict(sorted(interests_counts.items(), key=lambda x: x[1], reverse=True)[:6])
    sorted_missing_skills = dict(sorted(missing_skill_counts.items(), key=lambda x: x[1], reverse=True)[:6])

    # 10. Filtered Beneficiary Registry Table (Non-sensitive columns)
    query_records = f"""
        SELECT 
            b.beneficiary_id,
            CASE 
                WHEN b.preferred_language = 'hi' THEN 'Hindi' 
                WHEN b.preferred_language = 'mr' THEN 'Marathi' 
                ELSE 'English' 
            END as language,
            b.district,
            COALESCE(p.education, 'N/A') as education,
            CASE 
                WHEN p.employment_preference LIKE '%Self%' THEN 'Self-Employment'
                WHEN p.employment_preference LIKE '%Wage%' OR p.employment_preference LIKE '%Job%' OR p.employment_preference LIKE '%Salaried%' THEN 'Wage-Employment'
                WHEN p.employment_preference LIKE '%Any%' THEN 'Any'
                ELSE 'Unknown'
            END as preference,
            COALESCE(r.job_role, 'Pending Assessment') as recommended_nsqf_role,
            COALESCE(r.sector, 'General') as sector,
            COALESCE(ROUND(r.match_score, 1), 0.0) as match_score,
            b.created_at
        FROM beneficiaries b
        LEFT JOIN profiles p ON b.beneficiary_id = p.beneficiary_id
        LEFT JOIN recommendations r ON b.beneficiary_id = r.beneficiary_id AND r.rank_position = 1
        {where_sql}
        ORDER BY b.created_at DESC
        LIMIT 25;
    """
    cursor.execute(query_records, params)
    records = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_beneficiaries": total_beneficiaries,
        "average_match_score": avg_score,
        "language_distribution": language_dist,
        "education_distribution": education_dist,
        "sector_distribution": sector_dist,
        "top_roles_distribution": top_roles_dist,
        "district_distribution": district_dist,
        "employment_preference_distribution": pref_dist,
        "common_interests": sorted_interests,
        "common_missing_skills": sorted_missing_skills,
        "recent_beneficiaries": records,
        "total_profiles": total_beneficiaries,
        "self_employment_percentage": round(
            (pref_dist.get("Self-Employment", 0) / max(sum(pref_dist.values()), 1)) * 100, 1
        ),
        "records": records
    }


def get_dashboard_statistics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience wrapper returning aggregated metrics for tests and general monitoring.
    """
    return get_filtered_dashboard_data(db_path=db_path)

