"""
Kaushal Marg - Main Application
AI-Driven Voice Assistant for Livelihood Mapping and NSQF-Aligned Skilling Recommendations
for SC Communities under GIA component of PM-AJAY.

Team: Binary Minds
Slogan: Your Path to Skills & Livelihood
Problem Statement: SIH 26097
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from pages.beneficiary import render_beneficiary_page
from pages.dashboard import render_dashboard_page
from pages.recommendations import render_recommendations_page

# -----------------------------------------------------------------------------
# 1. Page Configuration & Professional Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Kaushal Marg | Your Path to Skills & Livelihood",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, professional styling without excessive animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Clean Hero Container */
    .hero-container {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 6px solid #1E40AF;
        border-radius: 10px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
    }
    
    .hero-slogan {
        font-size: 1.2rem;
        font-weight: 500;
        color: #047857;
        margin: 0 0 14px 0;
    }
    
    .badge-tag {
        display: inline-block;
        font-size: 0.82rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    .badge-blue {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
    }
    
    .badge-amber {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    
    .badge-gray {
        background-color: #F3F4F6;
        color: #374151;
        border: 1px solid #E5E7EB;
    }

    /* Structured Cards */
    .info-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    .info-card h3 {
        color: #1E3A8A;
        font-size: 1.15rem;
        margin-top: 0;
        margin-bottom: 8px;
    }

    .info-card p {
        color: #4B5563;
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 0;
    }

    .nsqf-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .skill-tag-matched {
        background-color: #DCFCE7;
        color: #166534;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin: 3px 2px;
        border: 1px solid #86EFAC;
    }
    
    .skill-tag-missing {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin: 3px 2px;
        border: 1px solid #FCD34D;
    }

    /* Button Enhancements */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Sidebar Navigation & Branding
# -----------------------------------------------------------------------------
nav_options = [
    "🏠 Home",
    "🎙️ Beneficiary Assistant",
    "🎯 Recommendations",
    "📊 Admin Dashboard"
]

if "active_nav" not in st.session_state:
    st.session_state["active_nav"] = "🏠 Home"
if "selected_lang_code" not in st.session_state:
    st.session_state["selected_lang_code"] = "hi"

def navigate_to(page_name):
    """Safely updates session state and navigates to target page."""
    st.session_state["active_nav"] = page_name
    st.rerun()

with st.sidebar:
    logo_path = os.path.join("assets", "kaushal_marg_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
        st.markdown("""
            <div style="padding-bottom: 15px; border-bottom: 1px solid #E5E7EB; margin-bottom: 15px;">
                <p style="color: #047857; font-size: 0.9rem; font-weight: 600; margin: 2px 0 0 0;">
                    Your Path to Skills & Livelihood
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="padding-bottom: 15px; border-bottom: 1px solid #E5E7EB; margin-bottom: 15px;">
                <h2 style="color: #1E3A8A; margin: 0; font-size: 1.5rem;">🎯 Kaushal Marg</h2>
                <p style="color: #047857; font-size: 0.9rem; font-weight: 600; margin: 2px 0 0 0;">
                    Your Path to Skills & Livelihood
                </p>
            </div>
        """, unsafe_allow_html=True)

    # Global Language Selector in Sidebar
    st.markdown("**Language / भाषा / भाषा निवडा:**")
    global_lang_opts = ["🇮🇳 हिंदी", "🇬🇧 English", "🇮🇳 मराठी"]
    global_lang_map = {"🇮🇳 हिंदी": "hi", "🇬🇧 English": "en", "🇮🇳 मराठी": "mr"}
    inv_global_map = {v: k for k, v in global_lang_map.items()}
    
    cur_lang_code = st.session_state.get("selected_lang_code", "hi")
    cur_lang_lbl = inv_global_map.get(cur_lang_code, "🇮🇳 हिंदी")
    
    selected_sidebar_lang = st.selectbox(
        "Language",
        options=global_lang_opts,
        index=global_lang_opts.index(cur_lang_lbl),
        label_visibility="collapsed",
        key="global_sidebar_lang_select"
    )
    new_global_code = global_lang_map[selected_sidebar_lang]
    if new_global_code != cur_lang_code:
        st.session_state["selected_lang_code"] = new_global_code
        st.rerun()

    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    st.markdown("**Navigation:**")
    
    current_nav = st.session_state.get("active_nav", "🏠 Home")
    current_index = nav_options.index(current_nav) if current_nav in nav_options else 0
    
    selected_page = st.radio(
        "Navigation Menu",
        options=nav_options,
        index=current_index,
        label_visibility="collapsed"
    )
    
    if selected_page != st.session_state["active_nav"]:
        st.session_state["active_nav"] = selected_page
        st.rerun()

    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
    st.markdown("""
        <div style="font-size: 0.85rem; color: #4B5563; line-height: 1.5;">
            <b>Team:</b> Binary Minds<br>
            <b>SIH Problem Statement:</b> 26097<br>
            <b>Scheme:</b> PM-AJAY (GIA Component)<br>
            <b>Beneficiaries:</b> SC Communities
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 3. Section 1: Clean & Professional Home Page
# -----------------------------------------------------------------------------
def render_home_page():
    """Renders the improved, clean, and professional Home page."""
    
    cur_lang = st.session_state.get("selected_lang_code", "hi")

    # Hero Container
    st.markdown('<div class="hero-container">', unsafe_allow_html=True)
    
    logo_path = os.path.join("assets", "kaushal_marg_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    
    st.markdown(f"""
            <h1 class="hero-title">Kaushal Marg</h1>
            <h3 class="hero-slogan">Your Path to Skills & Livelihood</h3>
            <div style="margin-bottom: 16px;">
                <span class="badge-tag badge-blue">SIH Problem Statement 26097</span>
                <span class="badge-tag badge-amber">Team Binary Minds</span>
                <span class="badge-tag badge-gray">PM-AJAY (GIA Component)</span>
            </div>
            <p style="color: #374151; font-size: 1.05rem; line-height: 1.6; margin-bottom: 0;">
                {'अनुसूचित जाति (SC) समुदायों के लिए PM-AJAY योजना (GIA घटक) के अंतर्गत AI-संचालित वॉइस असिस्टेंट एवं NSQF-संरेखित हुनर और आजीविका अनुशंसा प्रणाली।' if cur_lang == 'hi' else ('अनुसूचित जाती (SC) समुदायांसाठी PM-AJAY योजनेअंतर्गत AI-सक्षम व्हॉईस असिस्टंट आणि NSQF-संरेखित कौशल्य व उपजीविका मार्गदर्शन प्लॅटफॉर्म.' if cur_lang == 'mr' else 'AI-driven voice assistant for livelihood mapping and NSQF-aligned skilling recommendations for Scheduled Caste (SC) communities under the Grant-in-Aid (GIA) component of PM-AJAY.')}
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Primary Call to Action: Start My Journey
    start_col1, start_col2, start_col3 = st.columns([1, 2, 1])
    with start_col2:
        cta_label = "🚀 अपनी कौशल यात्रा शुरू करें (Start My Journey)" if cur_lang == 'hi' else ("🚀 माझी कौशल्य यात्रा सुरू करा (Start My Journey)" if cur_lang == 'mr' else "🚀 Start My Journey")
        start_button = st.button(
            cta_label,
            type="primary",
            use_container_width=True,
            key="btn_start_my_journey",
            help="Begin voice assessment to find NSQF-aligned skilling and livelihood opportunities"
        )
        if start_button:
            st.session_state["beneficiary_step"] = 1
            navigate_to("🎙️ Beneficiary Assistant")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3 Key Core Pillars
    st.subheader("Core Capabilities")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="info-card">
                <h3>🎙️ Voice-First Assistant</h3>
                <p>
                    Designed for low digital literacy. Beneficiaries communicate naturally via spoken Hindi or English to articulate skills, education, and aspirations without complex typing.
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="info-card">
                <h3>🧭 NSQF-Aligned Skilling</h3>
                <p>
                    Deterministic, transparent scoring engine evaluated across 23 verified Sector Skill Council job roles with clear skill-gap analysis (matched vs missing skills).
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="info-card">
                <h3>📊 PM-AJAY GIA Linkage</h3>
                <p>
                    Connects beneficiaries with NSQF-aligned training centers, district-level livelihood clusters, and potential micro-enterprise support pathways under the PM-AJAY GIA framework.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # How Kaushal Marg Works
    st.subheader("How It Works")
    step_col1, step_col2, step_col3, step_col4 = st.columns(4)
    
    with step_col1:
        st.info("🗣️ **1. Voice Input**\n\nBeneficiary speaks about education, skills, and interests in Hindi or English.")
    with step_col2:
        st.info("🔍 **2. Profile Mapping**\n\nAI extracts structured data while preserving user privacy and intent.")
    with step_col3:
        st.info("📐 **3. NSQF Scoring**\n\nTransparent 100-point deterministic engine matches top 3 QP-NOS roles.")
    with step_col4:
        st.success("💼 **4. 'My Skill Journey'**\n\nStep-by-step pathway to training, certification, and livelihood pathways.")


# -----------------------------------------------------------------------------
# 4. Application Router
# -----------------------------------------------------------------------------
active_page = st.session_state.get("active_nav", "🏠 Home")

if active_page == "🏠 Home":
    render_home_page()
elif active_page == "🎙️ Beneficiary Assistant":
    render_beneficiary_page()
elif active_page == "🎯 Recommendations":
    render_recommendations_page()
elif active_page == "📊 Admin Dashboard":
    render_dashboard_page()

# -----------------------------------------------------------------------------
# 6. Global Accessible Footer
# -----------------------------------------------------------------------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; color: #6B7280; font-size: 0.85rem; padding: 10px 0;">
        <b>Kaushal Marg</b> • <i>"Your Path to Skills & Livelihood"</i><br>
        Developed for Smart India Hackathon (SIH 26097) by <b>Team Binary Minds</b>
    </div>
""", unsafe_allow_html=True)
