-- =====================================================================
-- Kaushal Marg: SQLite Database Schema
-- SIH Problem Statement 26097 | Team Binary Minds
-- =====================================================================

-- Enable Foreign Key constraints
PRAGMA foreign_keys = ON;

-- 1. Beneficiaries Table (Stores high-level metadata without sensitive PII)
CREATE TABLE IF NOT EXISTS beneficiaries (
    beneficiary_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    preferred_language TEXT DEFAULT 'hi',
    district TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Profiles Table (Stores extracted skilling & education profile)
CREATE TABLE IF NOT EXISTS profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    beneficiary_id TEXT NOT NULL,
    age INTEGER,
    education TEXT,
    current_occupation TEXT,
    work_experience TEXT,
    family_occupation TEXT,
    skills_json TEXT DEFAULT '[]',
    interests_json TEXT DEFAULT '[]',
    aspirations TEXT,
    district TEXT,
    local_context TEXT,
    mobility TEXT DEFAULT 'Low',
    employment_preference TEXT DEFAULT 'Self-Employment',
    constraints TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries (beneficiary_id) ON DELETE CASCADE
);

-- 3. Conversations Table (Stores interview dialogue turns)
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    beneficiary_id TEXT NOT NULL,
    sender TEXT NOT NULL CHECK (sender IN ('user', 'assistant')),
    message_text TEXT NOT NULL,
    input_mode TEXT DEFAULT 'voice' CHECK (input_mode IN ('voice', 'text')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries (beneficiary_id) ON DELETE CASCADE
);

-- 4. Recommendations Table (Stores NSQF-aligned recommendation results)
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    beneficiary_id TEXT NOT NULL,
    rank_position INTEGER DEFAULT 1,
    job_role TEXT NOT NULL,
    sector TEXT NOT NULL,
    nsqf_level INTEGER NOT NULL,
    match_score REAL NOT NULL,
    skill_gap_json TEXT DEFAULT '{}',
    local_opportunity TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries (beneficiary_id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_profiles_beneficiary ON profiles(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_conversations_beneficiary ON conversations(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_beneficiary ON recommendations(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_district ON beneficiaries(district);
