"""
Kaushal Marg - Recommendation Results Page
Displays Top 3 NSQF-aligned job roles, match percentage, rationale, skill gaps,
local district opportunities, livelihood pathway ('My Skill Journey'), and employment suitability.

Team: Binary Minds | SIH Problem Statement 26097
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from recommendation.matcher import recommend_jobs, load_nsqf_jobs
from recommendation.pathway import generate_skill_pathway


def render_recommendations_page():
    """Renders the transparent, accessible NSQF recommendations and pathway view."""
    
    # -------------------------------------------------------------
    # 1. Header & Context
    # -------------------------------------------------------------
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown("""
            <div style="margin-bottom: 10px;">
                <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">
                    🎯 आपके लिए सरकारी हुनर और रोज़गार | Recommended Pathways
                </h1>
                <p style="color: #4B5563; font-size: 1.05rem; margin: 4px 0 0 0;">
                    NSQF-Aligned Skilling Recommendations & "My Skill Journey" under PM-AJAY (GIA Component)
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    with head_col2:
        lang = st.session_state.get("beneficiary_lang", "हिंदी")
        lang_choice = st.radio(
            "Language / भाषा:",
            options=["🇮🇳 हिंदी", "🇬🇧 English"],
            index=0 if lang == "हिंदी" else 1,
            horizontal=True,
            key="recs_lang_radio"
        )
        is_hindi = "हिंदी" in lang_choice
        st.session_state["beneficiary_lang"] = "हिंदी" if is_hindi else "English"

    st.markdown("<hr style='margin: 12px 0 20px 0;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. Active Beneficiary Profile & Sample Selector
    # -------------------------------------------------------------
    # Retrieve profile from session state or use default demo profile
    profile = st.session_state.get("demo_profile", {
        "name": "रमेश कुमार (Ramesh Kumar)",
        "education": "10th Pass",
        "skills": ["Tractor operation", "Basic farming"],
        "interests": ["Agriculture", "Machinery"],
        "district": "Indore",
        "mobility": "Low (District Level)",
        "employment_preference": "Self-Employment (GIA PM-AJAY)"
    })

    # Profile Bar
    with st.container():
        st.markdown(f"""
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 5px solid #3B82F6; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <h4 style="color: #1E3A8A; margin: 0 0 4px 0;">
                            👤 {'मूल्यांकित लाभार्थी प्रोफ़ाइल' if is_hindi else 'Evaluated Beneficiary Profile'}: <b>{profile.get('name', 'Beneficiary')}</b>
                        </h4>
                        <span style="color: #475569; font-size: 0.95rem;">
                            🎓 <b>{'शिक्षा' if is_hindi else 'Education'}:</b> {profile.get('education', 'N/A')} &nbsp;|&nbsp; 
                            📍 <b>{'ज़िला' if is_hindi else 'District'}:</b> {profile.get('district', 'N/A')} &nbsp;|&nbsp; 
                            🛠️ <b>{'वर्तमान हुनर' if is_hindi else 'Current Skills'}:</b> {', '.join(profile.get('skills', [])) if profile.get('skills') else 'None'} &nbsp;|&nbsp; 
                            💼 <b>{'पसंद' if is_hindi else 'Goal'}:</b> {profile.get('employment_preference', profile.get('preference', 'Self-Employment'))}
                        </span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 10 Synthetic Demo Profile Switcher
    st.markdown(f"##### {'🔄 10 नमूना प्रोफ़ाइल के अवसर देखें (Switch from 10 Demo Profiles):' if is_hindi else '🔄 Switch from 10 Synthetic Demo Profiles:'}")
    
    from data.demo_profiles import SYNTHETIC_BENEFICIARY_PROFILES
    
    recs_demo_labels = [
        f"{p['name']} ({p['domain_tag']} • {p['district']} • {p['employment_preference']})"
        for p in SYNTHETIC_BENEFICIARY_PROFILES
    ]
    
    sw_col1, sw_col2 = st.columns([3, 1])
    with sw_col1:
        selected_rec_idx = st.selectbox(
            "Select Beneficiary Profile:",
            options=range(len(recs_demo_labels)),
            format_func=lambda x: recs_demo_labels[x],
            key="recs_profile_select",
            label_visibility="collapsed"
        )
    with sw_col2:
        if st.button("🚀 " + ("यह प्रोफ़ाइल देखें / Evaluate" if is_hindi else "Evaluate Profile"), key="btn_eval_demo_profile", use_container_width=True):
            p_sel = SYNTHETIC_BENEFICIARY_PROFILES[selected_rec_idx]
            st.session_state["demo_profile"] = {
                "name": p_sel["name"],
                "education": p_sel["education"],
                "skills": p_sel["skills"],
                "interests": p_sel["interests"],
                "district": p_sel["district"],
                "mobility": p_sel["mobility"],
                "employment_preference": p_sel["employment_preference"]
            }
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 3. Execute Pure Recommendation Algorithm
    # -------------------------------------------------------------
    # Call the unmodified deterministic matcher
    top_recommendations = recommend_jobs(profile, top_n=3)

    if not top_recommendations:
        st.warning("⚠️ No NSQF job role recommendations found. Please verify the profile details.")
        return

    # Load raw NSQF dataset to cross-reference full metadata for pathway generator
    all_jobs_raw = load_nsqf_jobs()
    jobs_map = {job["job_role"].strip().lower(): job for job in all_jobs_raw}

    # -------------------------------------------------------------
    # 4. Display Top 3 Recommendations
    # -------------------------------------------------------------
    st.subheader(f"🏆 {'आपके लिए शीर्ष 3 अनुशंसित NSQF जॉब रोल' if is_hindi else 'Top 3 NSQF-Aligned Job Recommendations'}")

    rank_colors = [
        {"border": "#16A34A", "bg_badge": "#DCFCE7", "text_badge": "#166534", "label": "🥇 #1 Best Fit / सर्वोत्तम चयन"},
        {"border": "#2563EB", "bg_badge": "#DBEAFE", "text_badge": "#1E40AF", "label": "🥈 #2 Strong Match / उत्तम चयन"},
        {"border": "#9333EA", "bg_badge": "#F3E8FF", "text_badge": "#6B21A8", "label": "🥉 #3 Alternative Match / वैकल्पिक चयन"}
    ]

    for idx, rec in enumerate(top_recommendations):
        style = rank_colors[idx] if idx < len(rank_colors) else rank_colors[-1]
        score_val = int(round(rec.get("score", 0)))
        role_title = rec.get("job_role", "")
        sector_name = rec.get("sector", "")
        matched_skills = rec.get("matched_skills", [])
        missing_skills = rec.get("missing_skills", [])
        emp_type = rec.get("employment_type", "Self-Employment")
        why_list = rec.get("why_recommended", [])
        local_opp_info = rec.get("local_opportunity", "")
        local_opp_details = rec.get("local_opportunity_details", None)

        # Lookup raw job to get exact NSQF Level and minimum education
        raw_job = jobs_map.get(role_title.strip().lower(), {})
        nsqf_lvl = raw_job.get("nsqf_level", "4")
        min_edu = raw_job.get("minimum_education", "8th Pass")
        self_suitability = raw_job.get("self_employment_suitability", "High")

        # Top Card Container
        st.markdown(f"""
            <div style="background:#FFFFFF; border: 2px solid {style['border']}; border-radius: 12px; padding: 22px; margin-bottom: 22px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <!-- Header with Title and Match Score -->
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 12px;">
                    <div>
                        <span style="font-size: 0.85rem; font-weight: 700; color: {style['text_badge']}; text-transform: uppercase;">
                            {style['label']}
                        </span>
                        <h2 style="color: #0F172A; margin: 4px 0 0 0; font-size: 1.55rem;">
                            {role_title}
                        </h2>
                    </div>
                    <div style="text-align: right; margin-top: 6px;">
                        <span style="background: {style['bg_badge']}; color: {style['text_badge']}; font-weight: 700; padding: 8px 18px; border-radius: 24px; font-size: 1.25rem; border: 1px solid {style['border']};">
                            🎯 {score_val}% {'अनुकूल' if is_hindi else 'Match Score'}
                        </span>
                    </div>
                </div>

                <!-- Metadata Row -->
                <div style="background: #F8FAFC; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; font-size: 0.95rem; color: #334155;">
                    🏢 <b>{'क्षेत्र (Sector)' if is_hindi else 'Sector'}:</b> {sector_name} &nbsp;|&nbsp; 
                    🎖️ <b>NSQF Level:</b> Level {nsqf_lvl} &nbsp;|&nbsp; 
                    🎓 <b>{'न्यूनतम शिक्षा' if is_hindi else 'Min Education'}:</b> {min_edu} &nbsp;|&nbsp; 
                    💼 <b>{'रोज़गार प्रकार' if is_hindi else 'Suitability'}:</b> {emp_type} ({'स्वरोज़गार अनुकूलता' if is_hindi else 'Self-Emp'}: {self_suitability})
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 2-Column Details: (Left: Skill-Gap & Rationale, Right: Local Opportunity & Suitability)
        col_d1, col_d2 = st.columns([1.2, 1])

        with col_d1:
            st.markdown(f"#### 🛠️ {'कौशल तुलना (Skill-Gap Analysis):' if is_hindi else 'Skill-Gap Analysis:'}")
            
            # Matched Skills (Green)
            if matched_skills:
                matched_html = " ".join([f"<span style='background-color:#DCFCE7; color:#166534; font-weight:600; font-size:0.88rem; padding:4px 10px; border-radius:6px; display:inline-block; margin:3px 2px; border:1px solid #86EFAC;'>✅ {s}</span>" for s in matched_skills])
                st.markdown(f"**{'आपके पास पहले से हुनर (Existing Skills):' if is_hindi else 'Existing Matched Skills:'}**<br>{matched_html}", unsafe_allow_html=True)
            else:
                st.markdown(f"*{'प्रारंभिक स्तर (No direct prior skill overlap)' if is_hindi else 'No direct prior skill overlap'}*")

            # Missing Skills (Amber/Orange)
            st.write("")
            if missing_skills:
                missing_html = " ".join([f"<span style='background-color:#FEF3C7; color:#92400E; font-weight:600; font-size:0.88rem; padding:4px 10px; border-radius:6px; display:inline-block; margin:3px 2px; border:1px solid #FCD34D;'>🔄 {s}</span>" for s in missing_skills])
                st.markdown(f"**{'सीखने योग्य हुनर (Skills to Learn in Training):' if is_hindi else 'Skills to Build During Training:'}**<br>{missing_html}", unsafe_allow_html=True)
            else:
                st.success("✅ " + ("आपके पास सभी आवश्यक हुनर पहले से मौजूद हैं!" if is_hindi else "You already possess all required skills for this role!"))

            # Transparent Rationale (Why Recommended)
            st.write("")
            st.markdown(f"**💡 {'यह सिफ़ारिश क्यों चुनी गई (Why Recommended):' if is_hindi else 'Why This Role Was Recommended:'}**")
            for reason in why_list:
                st.markdown(f"- {reason}")

        with col_d2:
            # Local Opportunity Box
            st.markdown(f"#### 📍 {'स्थानीय अवसर व ट्रेनिंग सेंटर:' if is_hindi else 'Local Opportunity & Cluster:'}")
            if local_opp_details:
                st.markdown(f"""
                    <div style="background:#F0FDF4; border:1px solid #86EFAC; border-left: 4px solid #16A34A; border-radius:8px; padding:14px; margin-bottom:12px;">
                        <h4 style="color:#166534; margin:0 0 6px 0; font-size:1.05rem;">
                            📍 {local_opp_details.get('district')} ({local_opp_details.get('opportunity_type', 'Training & Placement')})
                        </h4>
                        <p style="color:#14532D; font-size:0.92rem; margin:0; line-height:1.5;">
                            <b>{'मांग स्तर (Demand)' if is_hindi else 'Demand Level'}:</b> {local_opp_details.get('demand_level', 'High')} Demand<br>
                            <b>{'योजना सहायता' if is_hindi else 'Scheme Grant'}:</b> PM-AJAY GIA Component Eligible<br>
                            <small style="color:#4B5563;">🏷️ {local_opp_details.get('data_source_type', 'Prototype Demo Data')}</small>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px; margin-bottom:12px;">
                        <p style="color:#64748B; font-size:0.92rem; margin:0;">
                            ℹ️ {local_opp_info}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

            # Employment / Self-Employment Suitability Card
            st.markdown(f"""
                <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-left:4px solid #2563EB; border-radius:8px; padding:14px;">
                    <h4 style="color:#1E40AF; margin:0 0 6px 0; font-size:1.05rem;">
                        💼 {'रोज़गार / स्वरोज़गार अनुकूलता' if is_hindi else 'Livelihood & Grant Suitability'}
                    </h4>
                    <p style="color:#1E293B; font-size:0.92rem; margin:0; line-height:1.5;">
                        <b>{'श्रेणी' if is_hindi else 'Category'}:</b> {emp_type}<br>
                        <b>PM-AJAY GIA Fit:</b> {'उच्च (स्वरोज़गार व टूलकिट सहायता के लिए पात्र)' if 'Self' in emp_type else 'उद्योग आधारित रोज़गार (Wage-Employment)'}
                    </p>
                </div>
            """, unsafe_allow_html=True)

        # ---------------------------------------------------------
        # Suggested Livelihood / Training Pathway ("My Skill Journey")
        # ---------------------------------------------------------
        pathway_data = generate_skill_pathway(
            beneficiary_profile=profile,
            recommended_job_role=raw_job if raw_job else {"job_role": role_title, "sector": sector_name, "nsqf_level": nsqf_lvl, "required_skills": "|".join(matched_skills + missing_skills)},
            missing_skills=missing_skills
        )

        with st.expander(f"🗺️ {'मेरी कौशल यात्रा (My Skill Journey) - ' + role_title + ' के लिए चरणबद्ध मार्ग' if is_hindi else f'My Skill Journey Pathway for {role_title}'}", expanded=(idx == 0)):
            st.markdown(f"**{'प्रारंभिक स्थिति (Starting Point):' if is_hindi else 'Starting Point:'}** *{pathway_data.get('current_state')}*")
            st.markdown("<br>", unsafe_allow_html=True)

            pw1, pw2, pw3, pw4 = st.columns(4)
            
            with pw1:
                st.markdown("""
                    <div style="background:#F1F5F9; border:1px solid #CBD5E1; border-top:4px solid #64748B; border-radius:8px; padding:12px; height:100%;">
                        <b style="color:#334155; font-size:0.95rem;">🌱 चरण 1: वर्तमान स्थिति</b><br>
                        <span style="font-size:0.85rem; color:#475569;">मौजूदा अनुभव और बुनियादी शिक्षा का मूल्यांकन।</span>
                    </div>
                """, unsafe_allow_html=True)

            with pw2:
                train_info = pathway_data.get("training_stage", {})
                train_mods = "<br>• ".join(train_info.get("learning_modules", [])[:2])
                st.markdown(f"""
                    <div style="background:#FFFBEB; border:1px solid #FDE68A; border-top:4px solid #D97706; border-radius:8px; padding:12px; height:100%;">
                        <b style="color:#92400E; font-size:0.95rem;">📚 चरण 2: थ्योरी ट्रेनिंग</b><br>
                        <span style="font-size:0.85rem; color:#78350F;">क्लासरूम प्रशिक्षण:<br>• {train_mods}</span>
                    </div>
                """, unsafe_allow_html=True)

            with pw3:
                prac_info = pathway_data.get("practical_stage", {})
                prac_tasks = "<br>• ".join(prac_info.get("practical_tasks", [])[:2])
                st.markdown(f"""
                    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-top:4px solid #16A34A; border-radius:8px; padding:12px; height:100%;">
                        <b style="color:#166534; font-size:0.95rem;">🛠️ चरण 3: प्रैक्टिकल वर्कशॉप</b><br>
                        <span style="font-size:0.85rem; color:#14532D;">लैब/कार्यशाला अभ्यास:<br>• {prac_tasks}</span>
                    </div>
                """, unsafe_allow_html=True)

            with pw4:
                st.markdown(f"""
                    <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-top:4px solid #2563EB; border-radius:8px; padding:12px; height:100%;">
                        <b style="color:#1E40AF; font-size:0.95rem;">🏆 चरण 4: NSQF प्रमाणन</b><br>
                        <span style="font-size:0.85rem; color:#1E3A8A;"><b>{role_title}</b> (Level {nsqf_lvl}) सर्टिफ़िकेशन व PM-AJAY GIA अनुदान से आजीविका।</span>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 25px 0;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 5. Action Buttons & Disclaimer
    # -------------------------------------------------------------
    act_col1, act_col2, act_col3 = st.columns([1, 1, 1])
    with act_col1:
        if st.button("🔄 " + ("नई बातचीत शुरू करें / Start New Profile" if is_hindi else "Start New Profile"), use_container_width=True, key="btn_recs_new_interview"):
            st.session_state["beneficiary_step"] = 1
            st.session_state["active_nav"] = "🎙️ Beneficiary Assistant"
            st.session_state["sidebar_radio"] = "🎙️ Beneficiary Assistant"
            st.rerun()

    with act_col2:
        if st.button("📊 " + ("प्रशासक डैशबोर्ड देखें / Admin Dashboard" if is_hindi else "View Admin Dashboard"), use_container_width=True, key="btn_recs_goto_dash"):
            st.session_state["active_nav"] = "📊 Admin Dashboard"
            st.session_state["sidebar_radio"] = "📊 Admin Dashboard"
            st.rerun()

    with act_col3:
        st.download_button(
            label="📥 " + ("कौशल रिपोर्ट डाउनलोड करें (PDF/Text)" if is_hindi else "Download Skill Report"),
            data=f"KAUSHAL MARG BENEFICIARY REPORT\nBeneficiary: {profile.get('name')}\nDistrict: {profile.get('district')}\nTop Role: {top_recommendations[0].get('job_role')}\nMatch Score: {top_recommendations[0].get('score')}%\nSector: {top_recommendations[0].get('sector')}\nScheme: PM-AJAY (GIA Component)\nTeam: Binary Minds",
            file_name=f"kaushal_marg_report_{profile.get('name', 'beneficiary').replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True,
            key="btn_download_report"
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("🏷️ **" + ("डेटा डिस्क्लेमर / Prototype Notice:" if is_hindi else "Data Notice:") + "** " + ("सभी 23 जॉब रोल आधिकारिक राष्ट्रीय कौशल योग्यता फ्रेमवर्क (NSQF) के सेक्टर स्किल काउंसिल QP-NOS मानकों पर आधारित हैं। स्थानीय अवसर डेटा प्रोटोटाइप प्रदर्शन के लिए है।" if is_hindi else "All 23 job roles are aligned with official National Skills Qualifications Framework (NSQF) QP-NOS standards. Local vacancy data is simulated for prototype demonstration."))


if __name__ == "__main__":
    st.set_page_config(page_title="Recommendations | Kaushal Marg", layout="wide")
    render_recommendations_page()
