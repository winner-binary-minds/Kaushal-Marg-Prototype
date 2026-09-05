"""
Kaushal Marg - Admin & Counselor Dashboard
PM-AJAY GIA Component Livelihood & Skilling Analytics.
Reads real-time aggregated metrics from SQLite database with multi-dimensional filtering.

Team: Binary Minds | SIH Problem Statement 26097
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
import html

from database.database import get_filtered_dashboard_data, seed_demo_database


def render_dashboard_page():
    """Renders the comprehensive PM-AJAY GIA Skilling & Livelihood Analytics Dashboard."""
    import os
    import hmac
    
    # -------------------------------------------------------------
    # 0. Admin Authentication
    # -------------------------------------------------------------
    expected_password = os.getenv("ADMIN_PASSWORD")
    
    if not expected_password:
        st.error("Admin dashboard cannot be loaded: ADMIN_PASSWORD environment variable is missing.")
        st.info("Please configure the ADMIN_PASSWORD environment variable in your .env file.")
        return
    
    if not st.session_state.get("admin_authenticated", False):
        st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>Admin Login Required</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Please enter the admin password to view the dashboard.")
            pwd = st.text_input("Password", type="password", key="admin_pwd_input")
            if st.button("Login", use_container_width=True):
                if hmac.compare_digest(pwd.encode('utf-8'), expected_password.encode('utf-8')):
                    st.session_state["admin_authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        return
    
    # -------------------------------------------------------------
    # 1. Header & Context & Demo Mode
    # -------------------------------------------------------------
    is_demo_mode = st.session_state.get("dashboard_demo_mode", False)
    
    # Toggle UI
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        if is_demo_mode:
            if st.button("⬅️ Return to Real Data", use_container_width=True):
                st.session_state["dashboard_demo_mode"] = False
                st.rerun()
        else:
            if st.button("🔧 Enter Demo Analytics Mode", use_container_width=True):
                seed_demo_database("demo_kaushal_marg.db")
                st.session_state["dashboard_demo_mode"] = True
                st.rerun()

    header_title = "📊 PM-AJAY GIA: Livelihood & Skilling Dashboard"
    if is_demo_mode:
        header_title = "📊 [DEMO MODE] Livelihood & Skilling Dashboard"
        st.warning("⚠️ **DEMO DATA — Synthetic records for SIH demonstration.** You are currently viewing isolated, synthetic demo data.")
    else:
        st.info("✅ **REAL DATA.** You are currently viewing actual beneficiary records from the Current Prototype Database.")
        
    st.markdown(f"""
        <div style="border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0 0 4px 0;">
                        {header_title}
                    </h1>
                    <p style="color: #4B5563; font-size: 1.05rem; margin: 0;">
                        Aggregated analytics on SC community skilling demand, NSQF alignments, and livelihood mapping under PM-AJAY (GIA Component).
                    </p>
                </div>
                <div>
                    <!-- Logout button on the right -->
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", key="btn_admin_logout"):
        st.session_state["admin_authenticated"] = False
        st.rerun()

    # -------------------------------------------------------------
    # 2. Interactive Multi-Filter Bar
    # -------------------------------------------------------------
    st.markdown("### 🔍 Filter Dashboard Data")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        lang_filter = st.selectbox(
            "🗣️ Language / भाषा:",
            options=["All Languages", "Hindi (हिंदी)", "Marathi (मराठी)", "English"],
            index=0,
            key="dash_filter_lang"
        )
    with f_col2:
        dist_filter = st.selectbox(
            "📍 District / ज़िला:",
            options=["All Districts", "Indore", "Jaipur", "Bhopal", "Lucknow", "Patna", "Udaipur"],
            index=0,
            key="dash_filter_dist"
        )
    with f_col3:
        sector_filter = st.selectbox(
            "🏢 Sector / कार्यक्षेत्र:",
            options=[
                "All Sectors",
                "Agriculture",
                "Green Jobs",
                "Apparel & Home Furnishing",
                "Construction",
                "Electronics",
                "Automotive",
                "Healthcare",
                "IT-ITeS",
                "Handicrafts",
                "Plumbing",
                "Retail",
                "Logistics",
                "Beauty & Wellness",
                "BFSI"
            ],
            index=0,
            key="dash_filter_sec"
        )

    st.markdown("<hr style='margin: 15px 0 22px 0;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 3. Read Aggregated SQLite Data
    # -------------------------------------------------------------
    data = get_filtered_dashboard_data(
        selected_language=lang_filter,
        selected_district=dist_filter,
        selected_sector=sector_filter,
        db_path="demo_kaushal_marg.db" if is_demo_mode else None
    )

    total_beneficiaries = data.get("total_beneficiaries", 0)
    avg_score = data.get("average_match_score", 0.0)
    lang_dist = data.get("language_distribution", {})
    edu_dist = data.get("education_distribution", {})
    sector_dist = data.get("sector_distribution", {})
    top_roles_dist = data.get("top_roles_distribution", {})
    dist_dist = data.get("district_distribution", {})
    pref_dist = data.get("employment_preference_distribution", {})
    common_interests = data.get("common_interests", {})
    missing_skills = data.get("common_missing_skills", {})
    records = data.get("records", [])

    # Calculate Self-Employment Share
    self_emp_count = pref_dist.get("Self-Employment", 0)
    total_pref = sum(pref_dist.values()) if pref_dist else 1
    self_emp_pct = round((self_emp_count / total_pref) * 100, 1) if total_pref > 0 else 0.0

    # -------------------------------------------------------------
    # 4. Top KPI Metric Cards
    # -------------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="👥 Total Beneficiaries Interviewed",
            value=f"{total_beneficiaries:,}",
            delta=f"{len(records)} in active filter" if total_beneficiaries > 0 else None
        )
    with kpi2:
        st.metric(
            label="🎯 Average NSQF Match Score",
            value=f"{avg_score}%" if avg_score > 0 else "N/A",
            delta="Deterministic Fit"
        )
    with kpi3:
        st.metric(
            label="💼 Self-Employment Aspirants",
            value=f"{self_emp_pct}%",
            delta="PM-AJAY Target"
        )
    with kpi4:
        active_dists = len(dist_dist)
        st.metric(
            label="📍 Districts Represented",
            value=f"{active_dists} Districts",
            delta="Priority SC Clusters"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if total_beneficiaries == 0:
        st.warning("⚠️ No beneficiary records found matching the selected filter criteria. Please broaden your selection.")
        return

    # -------------------------------------------------------------
    # 5. Row 1: Sector & Education Distribution Charts
    # -------------------------------------------------------------
    st.subheader("📈 Demand & Demographics")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("##### 🏢 Top Recommended Sectors")
        if sector_dist:
            df_sec = pd.DataFrame(list(sector_dist.items()), columns=["Sector", "Beneficiaries"]).set_index("Sector")
            st.bar_chart(df_sec, color="#2563EB", use_container_width=True)
        else:
            st.info("No sector data available.")

    with c2:
        st.markdown("##### 🎓 Education Distribution")
        if edu_dist:
            df_edu = pd.DataFrame(list(edu_dist.items()), columns=["Education Level", "Beneficiaries"]).set_index("Education Level")
            st.bar_chart(df_edu, color="#16A34A", use_container_width=True)
        else:
            st.info("No education data available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 6. Row 2: District Distribution & Livelihood Preference
    # -------------------------------------------------------------
    c3, c4 = st.columns(2)
    
    with c3:
        st.markdown("##### 📍 District Distribution")
        if dist_dist:
            df_dist = pd.DataFrame(list(dist_dist.items()), columns=["District", "Beneficiaries"]).set_index("District")
            st.bar_chart(df_dist, color="#9333EA", use_container_width=True)
        else:
            st.info("No district data available.")

    with c4:
        st.markdown("##### 💼 Wage vs Self-Employment Preference")
        if pref_dist:
            df_pref = pd.DataFrame(list(pref_dist.items()), columns=["Livelihood Mode", "Beneficiaries"]).set_index("Livelihood Mode")
            st.bar_chart(df_pref, color="#D97706", use_container_width=True)
        else:
            st.info("No preference data available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 7. Row 3: Language, Interests & Priority Skill Gaps
    # -------------------------------------------------------------
    c5, c6, c7 = st.columns(3)
    
    with c5:
        st.markdown("##### 🗣️ Language Distribution")
        if lang_dist:
            for l_name, l_count in lang_dist.items():
                pct = round((l_count / total_beneficiaries) * 100, 1)
                safe_name = html.escape(str(l_name))
                st.markdown(f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                        <b>{safe_name}</b>: {l_count} ({pct}%)
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No language data.")

    with c6:
        st.markdown("##### 💡 Most Common Interests")
        if common_interests:
            for int_name, int_count in common_interests.items():
                safe_int = html.escape(str(int_name))
                st.markdown(f"""
                    <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                        <b>{safe_int}</b>: {int_count} candidates
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No interest data.")

    with c7:
        st.markdown("##### 🛠️ Top Missing Skills (Skill Gaps)")
        if missing_skills:
            for sk_name, sk_count in missing_skills.items():
                safe_sk = html.escape(str(sk_name))
                st.markdown(f"""
                    <div style="background:#FEF3C7; border:1px solid #FDE68A; border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                        <b>{safe_sk}</b>: {sk_count} need training
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No skill gap data.")

    st.markdown("<hr style='margin: 25px 0;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 8. Top Recommended Job Roles Summary
    # -------------------------------------------------------------
    st.subheader("🏆 Top Recommended NSQF Job Roles in Active Filter")
    if top_roles_dist:
        role_cols = st.columns(min(len(top_roles_dist), 4))
        for i, (r_name, r_cnt) in enumerate(list(top_roles_dist.items())[:4]):
            safe_role = html.escape(str(r_name))
            with role_cols[i]:
                st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-top:4px solid #2563EB; border-radius:8px; padding:14px; text-align:center;">
                        <b style="color:#1E3A8A; font-size:1.05rem;">{safe_role}</b><br>
                        <span style="font-size:1.3rem; font-weight:700; color:#047857;">{r_cnt}</span>
                        <div style="font-size:0.85rem; color:#64748B;">Beneficiaries Matched</div>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 9. Beneficiary Registry Table (Privacy-Preserved)
    # -------------------------------------------------------------
    st.subheader("📋 Registered SC Beneficiary Records (Privacy-Preserved)")
    st.caption("Note: Displays non-sensitive anonymized skilling records for PM-AJAY GIA administrative monitoring.")

    if records:
        df_records = pd.DataFrame(records)
        df_records = df_records.rename(columns={
            "beneficiary_id": "Beneficiary ID",
            "language": "Language",
            "district": "District",
            "education": "Education",
            "preference": "Employment Goal",
            "recommended_nsqf_role": "Top Recommended NSQF Role",
            "sector": "Sector",
            "match_score": "Match Score (%)",
            "created_at": "Registration Date"
        })

        st.dataframe(df_records, use_container_width=True, hide_index=True)

        # Export CSV Button
        csv_bytes = df_records.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Beneficiary Data (Prototype Records CSV)",
            data=csv_bytes,
            file_name=f"pm_ajay_prototype_records_{dist_filter.lower()}_{sector_filter.lower()}.csv",
            mime="text/csv",
            key="btn_export_csv"
        )
    else:
        st.info("No records matching the filter.")


if __name__ == "__main__":
    st.set_page_config(page_title="Admin Dashboard | Kaushal Marg", layout="wide")
    render_dashboard_page()
