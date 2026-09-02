"""
Kaushal Marg - Synthetic Demo Profiles Dataset
Contains 10 fictional, realistic beneficiary profiles covering priority sectors
under the PM-AJAY (GIA Component) scheme for testing and demonstration.

IMPORTANT: All data is 100% synthetic/fictional. No real personal information is used.

Team: Binary Minds | SIH Problem Statement 26097
"""

from typing import List, Dict, Any

SYNTHETIC_BENEFICIARY_PROFILES: List[Dict[str, Any]] = [
    {
        "id": "DEMO-AGRI-01",
        "name": "Ramesh Kumar (रमेश कुमार)",
        "domain_tag": "Agriculture & Machinery",
        "education": "10th Pass",
        "skills": ["Tractor operation", "Basic farming"],
        "interests": ["Agriculture", "Machinery"],
        "mobility": "Low (Local Rural)",
        "employment_preference": "Self-Employment",
        "district": "Indore",
        "notes": "Experienced in farm machinery, seeking PM-AJAY GIA grant for custom hiring center."
    },
    {
        "id": "DEMO-ELEC-02",
        "name": "Sunita Devi (सुनीता देवी)",
        "domain_tag": "Electrical & Renewable Energy",
        "education": "12th Pass",
        "skills": ["Basic electrical wiring", "Tool handling"],
        "interests": ["Green Jobs", "Solar Energy"],
        "mobility": "Moderate (District)",
        "employment_preference": "Wage-Employment",
        "district": "Jaipur",
        "notes": "Interested in rooftop solar installation and government Suryamitra certification."
    },
    {
        "id": "DEMO-TAIL-03",
        "name": "Pooja Verma (पूजा वर्मा)",
        "domain_tag": "Tailoring & Apparel",
        "education": "8th Pass",
        "skills": ["Hand embroidery", "Basic tailoring"],
        "interests": ["Apparel & Home Furnishing"],
        "mobility": "Low (Local Village)",
        "employment_preference": "Self-Employment",
        "district": "Bhopal",
        "notes": "Member of village SHG seeking self-employment tailoring micro-enterprise."
    },
    {
        "id": "DEMO-CONS-04",
        "name": "Deepak Valmiki (दीपक वाल्मीकि)",
        "domain_tag": "Construction & Masonry",
        "education": "10th Pass",
        "skills": ["Bricklaying", "Cement plastering"],
        "interests": ["Construction", "Masonry"],
        "mobility": "Low (Local / District)",
        "employment_preference": "Wage-Employment",
        "district": "Indore",
        "notes": "Skilled in foundational masonry, aiming for formal CSDCI NSQF Level 3 certification."
    },
    {
        "id": "DEMO-RETL-05",
        "name": "Priyanka Sonkar (प्रियंका सोनकर)",
        "domain_tag": "Retail & Customer Service",
        "education": "12th Pass",
        "skills": ["Sales communication", "Inventory display"],
        "interests": ["Retail", "Customer Service"],
        "mobility": "Moderate",
        "employment_preference": "Wage-Employment",
        "district": "Lucknow",
        "notes": "High communicative aptitude for modern organized retail and billing counters."
    },
    {
        "id": "DEMO-FOOD-06",
        "name": "Mohan Lal (मोहन लाल)",
        "domain_tag": "Food & Hospitality",
        "education": "10th Pass",
        "skills": ["Food serving", "Hygiene maintenance"],
        "interests": ["Tourism & Hospitality", "Food Service"],
        "mobility": "Low (Local City)",
        "employment_preference": "Wage-Employment",
        "district": "Indore",
        "notes": "Seeking formal skilling in catering, food service operations, and hospitality."
    },
    {
        "id": "DEMO-AUTO-07",
        "name": "Rajesh Ahirwar (राजेश अहिरवार)",
        "domain_tag": "Automotive Mechanics",
        "education": "10th Pass",
        "skills": ["Two wheeler repair", "Brake tuning"],
        "interests": ["Automotive", "Vehicle Mechanics"],
        "mobility": "Low (Local Rural)",
        "employment_preference": "Self-Employment",
        "district": "Bhopal",
        "notes": "Aspirant for setting up a village 2-wheeler/3-wheeler garage under PM-AJAY GIA."
    },
    {
        "id": "DEMO-HAND-08",
        "name": "Rekha Baitha (रेखा बैठा)",
        "domain_tag": "Handicrafts & Zardozi",
        "education": "8th Pass",
        "skills": ["Zardozi work", "Hand stitching"],
        "interests": ["Handicrafts", "Apparel"],
        "mobility": "Low (Local Rural Only)",
        "employment_preference": "Self-Employment",
        "district": "Patna",
        "notes": "Traditional artisan seeking direct market linkage and artisan tool grant."
    },
    {
        "id": "DEMO-WAGE-09",
        "name": "Vikram Kori (विक्रम कोरी)",
        "domain_tag": "IT & Data Operations",
        "education": "12th Pass",
        "skills": ["Fast typing", "Basic Excel"],
        "interests": ["IT-ITeS", "Data Management"],
        "mobility": "Low (District Level)",
        "employment_preference": "Wage-Employment",
        "district": "Lucknow",
        "notes": "Seeking formal office IT skilling for government/private data operations."
    },
    {
        "id": "DEMO-ORGN-10",
        "name": "Suresh Bunkar (सुरेश बुनकर)",
        "domain_tag": "Organic Farming & Low Mobility",
        "education": "8th Pass",
        "skills": ["Organic composting", "Soil preparation"],
        "interests": ["Agriculture", "Organic Farming"],
        "mobility": "Low (Local Rural Only)",
        "employment_preference": "Self-Employment",
        "district": "Udaipur",
        "notes": "Dedicated organic farmer with zero inter-state mobility preference."
    }
]


def get_demo_profile_by_id(profile_id: str) -> Dict[str, Any]:
    """Retrieves a synthetic demo profile by its ID."""
    for p in SYNTHETIC_BENEFICIARY_PROFILES:
        if p["id"] == profile_id:
            return p
    return SYNTHETIC_BENEFICIARY_PROFILES[0]
