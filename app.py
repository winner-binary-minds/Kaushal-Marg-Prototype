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

from ui.beneficiary import render_beneficiary_page
from ui.dashboard import render_dashboard_page
from ui.recommendations import render_recommendations_page

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
st.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Base */
    .stApp {
        background-color: #FDFDFB;
        color: #2D3748;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #2D3748;
    }
    
    /* Clean Hero Container */
    .hero-container {
        background-color: transparent;
        padding: 40px 10px 30px 10px;
        margin-bottom: 20px;
    }
    
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        color: #1A202C;
        margin: 0 0 12px 0;
        letter-spacing: -1px;
        line-height: 1.1;
    }
    
    .hero-slogan {
        font-size: 1.25rem;
        font-weight: 500;
        color: #4A5568;
        margin: 0 0 24px 0;
        line-height: 1.5;
    }
    
    .badge-tag {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 6px 12px;
        border-radius: 20px;
        margin-right: 10px;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-primary {
        background-color: #E8F3EF;
        color: #2D5A4C;
        border: 1px solid #C6E0D5;
    }
    
    .badge-secondary {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #E2E8F0;
    }

    /* Structured Cards */
    .info-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        height: 100%;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .info-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
    }

    .info-card h3 {
        color: #2D5A4C;
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .info-card p {
        color: #4A5568;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 0;
    }

    .nsqf-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
    }
    
    .skill-tag-matched {
        background-color: #E8F3EF;
        color: #2D5A4C;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 6px 14px;
        border-radius: 20px;
        display: inline-block;
        margin: 4px 3px;
        border: 1px solid #C6E0D5;
    }
    
    .skill-tag-missing {
        background-color: #F8FAFC;
        color: #64748B;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 6px 14px;
        border-radius: 20px;
        display: inline-block;
        margin: 4px 3px;
        border: 1px solid #E2E8F0;
    }

    /* Button Enhancements */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 20px;
        border: none;
        transition: all 0.2s ease;
    }
    
    /* Primary Button Override */
    .stButton > button[kind="primary"] {
        background-color: #2D5A4C;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(45, 90, 76, 0.3);
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1F4035;
        box-shadow: 0 6px 8px -1px rgba(45, 90, 76, 0.4);
    }
    
    /* Secondary Button Override */
    .stButton > button[kind="secondary"] {
        background-color: #FFFFFF;
        color: #2D3748;
        border: 1px solid #CBD5E1;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .stButton > button[kind="secondary"]:hover {
        border-color: #94A3B8;
        color: #1A202C;
    }

    /* Sidebar Refinement */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Hide top padding for cleaner look */
    .block-container {
        padding-top: 2rem;
    }
</style>
""")


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
        st.html("""
            <div style="padding-bottom: 15px; border-bottom: 1px solid #E5E7EB; margin-bottom: 15px;">
                <p style="color: #047857; font-size: 0.9rem; font-weight: 600; margin: 2px 0 0 0;">
                    Your Path to Skills & Livelihood
                </p>
            </div>
        """)
    else:
        st.html("""
            <div style="padding-bottom: 15px; border-bottom: 1px solid #E2E8F0; margin-bottom: 15px;">
                <h2 style="color: #2D5A4C; margin: 0; font-size: 1.5rem; font-weight: 800;">Kaushal Marg</h2>
                <p style="color: #4A5568; font-size: 0.85rem; font-weight: 500; margin: 4px 0 0 0;">
                    Your Path to Skills & Livelihood
                </p>
            </div>
        """)

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

    st.html("<hr style='margin: 15px 0;'>")
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

    st.html("<hr style='margin: 20px 0;'>")
    st.html("""
        <div style="font-size: 0.85rem; color: #4B5563; line-height: 1.5;">
            <b>Team:</b> Binary Minds<br>
            <b>SIH Problem Statement:</b> 26097<br>
            <b>Scheme:</b> PM-AJAY (GIA Component)<br>
            <b>Beneficiaries:</b> SC Communities
        </div>
    """)


# -----------------------------------------------------------------------------
# 3. Section 1: Clean & Professional Home Page
# -----------------------------------------------------------------------------
def render_home_page():
    """Renders the improved, clean, and professional Home page."""
    
    cur_lang = st.session_state.get("selected_lang_code", "hi")

    st.html('<div class="hero-container">')
    
    # Restructure Hero with columns
    hero_col1, hero_col2 = st.columns([1.2, 1])
    
    with hero_col1:
        st.html(f"""
            <div style="margin-bottom: 16px;">
                <span style="color: #2D5A4C; font-size: 0.85rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Empowering Communities</span>
            </div>
            <h1 class="hero-title">Your Path to <br>Skills & Livelihood</h1>
            <p class="hero-slogan">
                Kaushal Marg is your personal assistant to discover the right skills, training and livelihood opportunities that match your interests and local needs.
            </p>
            <div style="margin-bottom: 24px;">
                <span class="badge-tag badge-primary">PM-AJAY</span>
                <span class="badge-tag badge-secondary">SIH 26097</span>
            </div>
        """)
        
        btn_col1, btn_col2, _ = st.columns([1, 1, 1])
        with btn_col1:
            cta_label = "🎙️ Start Your Journey" if cur_lang == 'en' else ("🎙️ अपनी यात्रा शुरू करें" if cur_lang == 'hi' else "🎙️ माझी यात्रा सुरू करा")
            if st.button(cta_label, type="primary", use_container_width=True, key="btn_start_journey"):
                st.session_state["beneficiary_step"] = 1
                navigate_to("🎙️ Beneficiary Assistant")
        with btn_col2:
            if st.button("Learn More", type="secondary", use_container_width=True):
                pass
                
    with hero_col2:
        # Use existing assets or leave elegant whitespace if no large hero image exists
        logo_path = os.path.join("assets", "kaushal_marg_logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
            
    st.html('</div>')

    st.html("<br>")

    # 3 Key Core Pillars
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.html("""
            <div class="info-card">
                <h3>🎙️ Voice Assistant</h3>
                <p>Talk in your language. Designed for natural spoken interaction without complex typing.</p>
            </div>
        """)

    with col2:
        st.html("""
            <div class="info-card">
                <h3>🎯 Personalized Recommendations</h3>
                <p>Get matched. Discover NSQF-aligned job roles that fit your skills and interests perfectly.</p>
            </div>
        """)

    with col3:
        st.html("""
            <div class="info-card">
                <h3>📍 Local Opportunities</h3>
                <p>Near you. Connect with training centers and livelihood pathways in your district.</p>
            </div>
        """)

    st.html("<br><br>")

    # How Kaushal Marg Works - Clean horizontal timeline style
    st.html("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h2 style="color: #1A202C; font-size: 1.8rem; font-weight: 700; margin-bottom: 8px;">How Kaushal Marg Works</h2>
            <p style="color: #718096; font-size: 1rem;">Simple steps to a better future</p>
        </div>
    """)
    
    step_col1, step_col2, step_col3, step_col4 = st.columns(4)
    
    with step_col1:
        st.html("""
            <div style="text-align: center; padding: 20px;">
                <div style="background-color: #F8FAFC; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; border: 1px solid #E2E8F0; font-size: 1.2rem;">🎙️</div>
                <h4 style="font-size: 1rem; color: #2D3748; margin-bottom: 8px;">1. Talk to Us</h4>
                <p style="font-size: 0.85rem; color: #718096;">Answer a few simple questions in your language</p>
            </div>
        """)
    with step_col2:
        st.html("""
            <div style="text-align: center; padding: 20px;">
                <div style="background-color: #F8FAFC; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; border: 1px solid #E2E8F0; font-size: 1.2rem;">🎯</div>
                <h4 style="font-size: 1rem; color: #2D3748; margin-bottom: 8px;">2. Get Matched</h4>
                <p style="font-size: 0.85rem; color: #718096;">Based on your skills and interests</p>
            </div>
        """)
    with step_col3:
        st.html("""
            <div style="text-align: center; padding: 20px;">
                <div style="background-color: #F8FAFC; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; border: 1px solid #E2E8F0; font-size: 1.2rem;">🧭</div>
                <h4 style="font-size: 1rem; color: #2D3748; margin-bottom: 8px;">3. Explore Opportunities</h4>
                <p style="font-size: 0.85rem; color: #718096;">See the best training & job options</p>
            </div>
        """)
    with step_col4:
        st.html("""
            <div style="text-align: center; padding: 20px;">
                <div style="background-color: #E8F3EF; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; border: 1px solid #C6E0D5; font-size: 1.2rem; color: #2D5A4C;">📈</div>
                <h4 style="font-size: 1rem; color: #2D5A4C; margin-bottom: 8px;">4. Grow & Succeed</h4>
                <p style="font-size: 0.85rem; color: #718096;">Build your skills and achieve your goals</p>
            </div>
        """)


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
st.html("<br><hr>")
st.html("""
    <div style="text-align: center; color: #6B7280; font-size: 0.85rem; padding: 10px 0;">
        <b>Kaushal Marg</b> • <i>"Your Path to Skills & Livelihood"</i><br>
        Developed for Smart India Hackathon (SIH 26097) by <b>Team Binary Minds</b>
    </div>
""")
