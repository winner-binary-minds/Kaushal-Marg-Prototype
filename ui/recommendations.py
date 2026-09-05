"""
Kaushal Marg - Recommendation Results Page
Displays Top 3 NSQF-aligned job roles, match percentage, rationale, skill gaps,
local district opportunities, livelihood pathway ('My Skill Journey'), and speech synthesis read-aloud.

Team: Binary Minds | SIH Problem Statement 26097
"""

import streamlit as st
import pandas as pd
import json
import logging
import html
from typing import Dict, Any, List

# Person 2 (Recommendation Engine)
from recommendation.matcher import recommend_jobs, load_nsqf_jobs
from recommendation.pathway import generate_skill_pathway
from recommendation.skill_gap import analyze_skill_gap

# Person 1 (AI Explanation & Voice TTS)
from ai.explanation import ExplanationGenerator
from voice.tts import TTSEngine

# Person 3 (Database & Demo Profiles)
from database.database import (
    save_recommendations_batch,
    create_beneficiary,
    save_profile
)
from data.demo_profiles import SYNTHETIC_BENEFICIARY_PROFILES


def render_tts_widget(text: str, lang_code: str, widget_id: str, button_label: str = "🔊 Listen to Summary / सारांश सुनें"):
    """Renders a browser SpeechSynthesis button."""
    tts = TTSEngine()
    cfg = tts.prepare_utterance(text, language=lang_code)
    escaped = json.dumps(cfg.text)
    
    js = f"""
        <script>
            function getSynth() {{
                var synth = null;
                try {{
                    if (window.parent && window.parent.speechSynthesis) {{
                        synth = window.parent.speechSynthesis;
                    }}
                }} catch (e) {{
                    // CORS restricted, fallback
                }}
                if (!synth && window.speechSynthesis) {{
                    synth = window.speechSynthesis;
                }}
                return synth;
            }}
            
            function speak_{widget_id}() {{
                var synth = getSynth();
                if (synth) {{
                    synth.cancel();
                    var u = new SpeechSynthesisUtterance({escaped});
                    u.lang = '{cfg.lang}';
                    u.rate = {cfg.rate};
                    u.pitch = {cfg.pitch};
                    synth.speak(u);
                }} else {{
                    alert('Browser speech synthesis is not supported on this device.');
                }}
            }}
            
            window.onload = function() {{
                if (!getSynth()) {{
                    var btn = document.getElementById('btn_{widget_id}');
                    if (btn) {{
                        btn.disabled = true;
                        btn.innerText = '🚫 TTS Unsupported';
                        btn.title = 'Your browser does not support Speech Synthesis';
                        btn.style.opacity = '0.5';
                        btn.style.cursor = 'not-allowed';
                    }}
                }}
            }};
        </script>
        <button id="btn_{widget_id}" onclick="speak_{widget_id}()" style="background:#2563EB; border:none; color:#FFFFFF; font-weight:600; padding:8px 16px; border-radius:8px; cursor:pointer; font-size:0.95rem;">
            {button_label}
        </button>
    """
    st.html(js)


def render_recommendations_page():
    """Renders the transparent, accessible NSQF recommendations and pathway view."""
    
    active_lang_code = st.session_state.get("selected_lang_code", "hi")
    
    # -------------------------------------------------------------
    # 1. Header & Language Selection
    # -------------------------------------------------------------
    head_col1, head_col2 = st.columns([2.8, 1.2])
    with head_col1:
        if active_lang_code == "hi":
            st.html("""
                <div style="margin-bottom: 8px;">
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">
                        🎯 आपके लिए सरकारी हुनर और रोज़गार | Recommended Pathways
                    </h1>
                    <p style="color: #4B5563; font-size: 1.05rem; margin: 4px 0 0 0;">
                        NSQF-Aligned Skilling Recommendations & "My Skill Journey" under PM-AJAY (GIA Component)
                    </p>
                </div>
            """)
        elif active_lang_code == "mr":
            st.html("""
                <div style="margin-bottom: 8px;">
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">
                        🎯 आपल्यासाठी सरकारी कौशल्य व रोजगार | Recommended Pathways
                    </h1>
                    <p style="color: #4B5563; font-size: 1.05rem; margin: 4px 0 0 0;">
                        NSQF-Aligned Skilling Recommendations & "My Skill Journey" under PM-AJAY (GIA Component)
                    </p>
                </div>
            """)
        else:
            st.html("""
                <div style="margin-bottom: 8px;">
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">
                        🎯 Your NSQF Skilling & Livelihood Pathways
                    </h1>
                    <p style="color: #4B5563; font-size: 1.05rem; margin: 4px 0 0 0;">
                        Official Sector Skill Council Recommendations & 4-Stage Pathway under PM-AJAY (GIA Component)
                    </p>
                </div>
            """)

    with head_col2:
        lang_opts = ["🇮🇳 हिंदी", "🇬🇧 English", "🇮🇳 मराठी"]
        l_map = {"🇮🇳 हिंदी": "hi", "🇬🇧 English": "en", "🇮🇳 मराठी": "mr"}
        inv_map = {v: k for k, v in l_map.items()}
        cur_lbl = inv_map.get(active_lang_code, "🇮🇳 हिंदी")
        
        chosen_lbl = st.radio(
            "Language / भाषा:",
            options=lang_opts,
            index=lang_opts.index(cur_lbl),
            horizontal=True,
            key="rec_lang_radio"
        )
        new_code = l_map[chosen_lbl]
        if new_code != active_lang_code:
            st.session_state["selected_lang_code"] = new_code
            st.rerun()

    st.markdown("<hr style='margin: 10px 0 18px 0;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # PROTOTYPE DATA SOURCE NOTICE
    # -------------------------------------------------------------
    st.info("ℹ️ **Data Source / Prototype Notice:** The district opportunities and NSQF mappings displayed are Prototype Demo Data designed for the SIH 26097 evaluation. This is not a live government API.")

    # -------------------------------------------------------------
    # 2. Active Beneficiary Profile & Evaluated Context
    # -------------------------------------------------------------
    # Fallback to an empty dictionary instead of synthetic defaults
    default_p = st.session_state.get("demo_profile", {})
    profile = st.session_state.get("extracted_profile") or default_p

    # Profile Summary Banner
    with st.container():
        safe_name = html.escape(str(profile.get('name') or 'Unknown'))
        safe_edu = html.escape(str(profile.get('education') or 'None'))
        safe_dist = html.escape(str(profile.get('district') or 'None'))
        safe_skills = html.escape(', '.join(profile.get('skills', [])) if profile.get('skills') else 'None')
        safe_pref = html.escape(str(profile.get('employment_preference') or 'Unknown'))
        st.html(f"""
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 5px solid #3B82F6; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <h4 style="color: #1E3A8A; margin: 0 0 4px 0;">
                            👤 {'मूल्यांकित लाभार्थी प्रोफ़ाइल' if active_lang_code == 'hi' else ('तपासलेली लाभार्थी माहिती' if active_lang_code == 'mr' else 'Evaluated Beneficiary Profile')}: <b>{safe_name}</b>
                        </h4>
                        <span style="color: #475569; font-size: 0.95rem;">
                            🎓 <b>{'शिक्षा' if active_lang_code != 'en' else 'Education'}:</b> {safe_edu} &nbsp;|&nbsp; 
                            📍 <b>{'ज़िला/स्थान' if active_lang_code != 'en' else 'District'}:</b> {safe_dist} &nbsp;|&nbsp; 
                            🛠️ <b>{'हुनर' if active_lang_code != 'en' else 'Skills'}:</b> {safe_skills} &nbsp;|&nbsp; 
                            💼 <b>{'पसंद' if active_lang_code != 'en' else 'Goal'}:</b> {safe_pref}
                        </span>
                    </div>
                </div>
            </div>
        """)

    # 10 Synthetic Demo Profile Switcher
    st.markdown(f"##### {'🔄 10 नमूना प्रोफ़ाइल के अवसर देखें (Switch from 10 Demo Profiles):' if active_lang_code == 'hi' else ('🔄 10 नमुना प्रोफाईल तपासा (Switch Demo Profile):' if active_lang_code == 'mr' else '🔄 Switch from 10 Synthetic Demo Profiles:')}")
    
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
        if st.button("🚀 " + ("यह प्रोफ़ाइल देखें / Evaluate" if active_lang_code != 'en' else "Evaluate Profile"), key="btn_eval_demo_profile", use_container_width=True):
            p_sel = SYNTHETIC_BENEFICIARY_PROFILES[selected_rec_idx]
            new_p = {
                "name": p_sel["name"],
                "education": p_sel["education"],
                "skills": list(p_sel["skills"]),
                "interests": list(p_sel["interests"]),
                "district": p_sel["district"],
                "mobility": p_sel["mobility"],
                "employment_preference": p_sel["employment_preference"]
            }
            st.session_state["extracted_profile"] = new_p
            st.session_state["demo_profile"] = new_p
            st.rerun()

    # -------------------------------------------------------------
    # 3. Generate NSQF Recommendations (Deterministic Engine)
    # -------------------------------------------------------------
    recommendations = recommend_jobs(profile, top_n=3)

    if not recommendations:
        st.warning("⚠️ " + (
            "हमें उपयुक्त मार्ग की अनुशंसा करने के लिए और जानकारी की आवश्यकता है। कृपया अपने कौशल, शिक्षा या रुचियों के बारे में अधिक विवरण प्रदान करें।" if active_lang_code == 'hi' else
            ("आम्हाला योग्य मार्गाची शिफारस करण्यासाठी अधिक माहितीची आवश्यकता आहे. कृपया तुमचे कौशल्य, शिक्षण किंवा आवडीबद्दल अधिक माहिती द्या." if active_lang_code == 'mr' else
            "We need more information to recommend a suitable pathway. Please provide more details about your skills, education, or interests.")
        ))
        return

    top_1 = recommendations[0]
    
    # Handle Need More Information fallback UX
    if top_1.get("status") == "insufficient_information":
        st.warning("⚠️ **More information is needed to make a reliable recommendation.**")
        st.markdown("### Missing Profile Information:")
        
        missing_info = top_1.get("missing_information", {})
        
        # Render a simple visual summary of what's known vs missing
        for key, val in missing_info.items():
            if val == "missing":
                disp_key = key.replace('_', ' ').title()
                st.markdown(f"<span style='color:#b91c1c'>❌ <b>{disp_key}</b>: MISSING</span>", unsafe_allow_html=True)

        st.markdown("<br>Please update your profile to provide the missing details so we can recommend an appropriate pathway.", unsafe_allow_html=True)
            
        if st.button("⬅️ Update Profile & Try Again", use_container_width=True, type="primary"):
            st.session_state["beneficiary_step"] = 2
            st.rerun()
        return

    # Handle No Strong Match UX
    if top_1.get("status") == "no_strong_match":
        st.warning("⚠️ **No strong match found in the current NSQF prototype dataset.**")
        st.markdown("The current prototype dataset does not contain a sufficiently aligned role for this profile. No unrelated role was recommended.")
        if st.button("⬅️ Back to Profile", use_container_width=True, type="primary"):
            st.session_state["beneficiary_step"] = 2
            st.rerun()
        return

    top_2 = recommendations[1] if len(recommendations) > 1 else None
    top_3 = recommendations[2] if len(recommendations) > 2 else None

    # -------------------------------------------------------------
    # 4. Plain-Language Explanation & Speech Read-Aloud
    # -------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("💡 " + ("अनुशंसा सारांश और मार्गदर्शन (Recommendation Narrative)" if active_lang_code == 'hi' else ("शिफारस सारांश व मार्गदर्शन (Recommendation Narrative)" if active_lang_code == 'mr' else "AI Summary & Recommendation Narrative")))
    
    # Initialize cache for explanation
    exp_key = f"exp_{top_1['job_role']}_{active_lang_code}"
    if exp_key not in st.session_state:
        st.session_state[exp_key] = None

    if st.session_state[exp_key] is None:
        if st.button("✨ " + ("AI सारांश जनरेट करें / Generate AI Summary" if active_lang_code == 'hi' else ("AI सारांश तयार करा / Generate AI Summary" if active_lang_code == 'mr' else "Generate AI Summary"))):
            with st.spinner("Generating summary..."):
                try:
                    exp_gen = ExplanationGenerator()
                    st.session_state[exp_key] = exp_gen.generate_explanation(
                        recommendation_result=top_1,
                        language=active_lang_code
                    )
                except Exception as e:
                    from ai.gemini import GeminiQuotaError
                    if isinstance(e, GeminiQuotaError) or "429" in str(e) or "quota" in str(e).lower():
                        st.session_state[exp_key] = f"⚠️ Gemini API Quota Exceeded. Please try again later. Deterministic summary: You are recommended for {top_1['job_role']} as a {top_1['employment_type']} in {top_1['sector']}."
                    else:
                        st.error(f"Error generating explanation: {e}")
            st.rerun()
        else:
            # Deterministic fallback text
            fallback = (
                f"आपको {top_1['sector']} क्षेत्र में {top_1['employment_type']} के लिए {top_1['job_role']} (स्तर {top_1.get('nsqf_level', 4)}) की अनुशंसा की जाती है।" if active_lang_code == 'hi' else
                f"तुम्हाला {top_1['sector']} क्षेत्रात {top_1['employment_type']} साठी {top_1['job_role']} (स्तर {top_1.get('nsqf_level', 4)}) ची शिफारस केली जाते." if active_lang_code == 'mr' else
                f"You are highly recommended for the {top_1['job_role']} role (Level {top_1.get('nsqf_level', 4)}) in the {top_1['sector']} sector for {top_1['employment_type']}."
            )
            st.info(fallback)
            explanation_text = fallback
    else:
        explanation_text = st.session_state[exp_key]
        st.info(explanation_text)

    # Audio Read-Aloud Button
    tts_btn_label = "🔊 यह सारांश सुनें (Listen to Summary)" if active_lang_code == 'hi' else ("🔊 हा सारांश ऐका (Listen to Summary)" if active_lang_code == 'mr' else "🔊 Listen Aloud to Summary")
    render_tts_widget(explanation_text, active_lang_code, "rec_summary", tts_btn_label)

    # -------------------------------------------------------------
    # 5. Top 3 NSQF Recommendations Display
    # -------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏆 " + ("शीर्ष 3 NSQF-संरेखित हुनर (Top 3 NSQF Job Roles)" if active_lang_code == 'hi' else ("सर्वोत्कृष्ट ३ NSQF-संरेखित कौशल्ये (Top 3 NSQF Roles)" if active_lang_code == 'mr' else "Top 3 NSQF-Aligned Job Recommendations")))

    col_r1, col_r2, col_r3 = st.columns(3)

    # RANK #1 CARD (Featured)
    with col_r1:
        st.html(f"""
            <div style="background: #FFFFFF; border: 2px solid #2D5A4C; border-top: 6px solid #2D5A4C; border-radius: 12px; padding: 20px; height: 100%; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05); transition: transform 0.2s ease;">
                <div style="background: #E8F3EF; color: #2D5A4C; font-weight: 700; font-size: 0.85rem; padding: 4px 10px; border-radius: 20px; display: inline-block; margin-bottom: 12px; border: 1px solid #C6E0D5;">
                    🥇 {'शीर्ष 1 चयन / Rank #1 Fit' if active_lang_code != 'en' else '🥇 Rank #1 Best Match'}
                </div>
                <h3 style="color: #1A202C; margin: 0 0 8px 0; font-size: 1.3rem; font-weight: 800;">{top_1['job_role']}</h3>
                <div style="color: #4A5568; font-size: 0.95rem; margin-bottom: 16px;">
                    🏢 <b>Sector:</b> {top_1['sector']}<br>
                    🎖️ <b>NSQF Level:</b> Level {top_1.get('nsqf_level', 4)}
                </div>
                <div style="display: flex; align-items: baseline; margin-bottom: 12px;">
                    <span style="font-size: 2.2rem; font-weight: 800; color: #2D5A4C;">{top_1['score']}%</span>
                    <span style="color: #718096; font-size: 0.95rem; margin-left: 8px; font-weight: 500;">{'योग्यता मेल (Match)' if active_lang_code != 'en' else 'Match Score'}</span>
                </div>
                <div style="font-size: 0.75rem; color: #718096; margin-bottom: 16px; background: #F8FAFC; padding: 6px 8px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <b>Breakdown:</b> Edu: {top_1['score_breakdown']['education']['score']}/{top_1['score_breakdown']['education']['max_score']} | 
                    Skill: {top_1['score_breakdown']['skill']['score']}/{top_1['score_breakdown']['skill']['max_score']} | 
                    Int: {top_1['score_breakdown']['interest']['score']}/{top_1['score_breakdown']['interest']['max_score']} | 
                    Mob: {top_1['score_breakdown']['mobility']['score']}/{top_1['score_breakdown']['mobility']['max_score']} | 
                    Pref: {top_1['score_breakdown']['employment_preference']['score']}/{top_1['score_breakdown']['employment_preference']['max_score']} | 
                    Loc: {top_1['score_breakdown']['local_opportunity']['score']}/{top_1['score_breakdown']['local_opportunity']['max_score']}
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; font-size: 0.9rem; color: #2D3748; margin-bottom: 12px;">
                    💼 <b>{'पसंद:' if active_lang_code != 'en' else 'Goal:'}</b> {top_1['employment_type']}
                </div>
                <div style="font-size: 0.9rem; color: #4A5568; line-height: 1.5;">
                    <b style="color: #2D3748;">💡 {'कारण / Rationale:' if active_lang_code != 'en' else 'Rationale:'}</b><br>
                    {' • '.join(top_1['why_recommended'][:2])}
                </div>
            </div>
        """)

    # RANK #2 CARD
    with col_r2:
        if top_2:
            st.html(f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 6px solid #94A3B8; border-radius: 12px; padding: 20px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <div style="background: #F8FAFC; color: #475569; font-weight: 700; font-size: 0.85rem; padding: 4px 10px; border-radius: 20px; display: inline-block; margin-bottom: 12px; border: 1px solid #E2E8F0;">
                        🥈 {'रैंक #2 / Rank #2' if active_lang_code != 'en' else '🥈 Rank #2'}
                    </div>
                    <h3 style="color: #1A202C; margin: 0 0 8px 0; font-size: 1.2rem; font-weight: 700;">{top_2['job_role']}</h3>
                    <div style="color: #4A5568; font-size: 0.95rem; margin-bottom: 16px;">
                        🏢 <b>Sector:</b> {top_2['sector']}<br>
                        🎖️ <b>NSQF Level:</b> Level {top_2.get('nsqf_level', 4)}
                    </div>
                    <div style="display: flex; align-items: baseline; margin-bottom: 12px;">
                        <span style="font-size: 2.0rem; font-weight: 700; color: #475569;">{top_2['score']}%</span>
                        <span style="color: #718096; font-size: 0.95rem; margin-left: 8px;">{'मेल (Score)' if active_lang_code != 'en' else 'Score'}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #718096; margin-bottom: 16px; background: #F8FAFC; padding: 6px 8px; border-radius: 6px; border: 1px solid #E2E8F0;">
                        <b>Breakdown:</b> Edu: {top_2['score_breakdown']['education']['score']}/{top_2['score_breakdown']['education']['max_score']} | 
                        Skill: {top_2['score_breakdown']['skill']['score']}/{top_2['score_breakdown']['skill']['max_score']} | 
                        Int: {top_2['score_breakdown']['interest']['score']}/{top_2['score_breakdown']['interest']['max_score']} | 
                        Mob: {top_2['score_breakdown']['mobility']['score']}/{top_2['score_breakdown']['mobility']['max_score']} | 
                        Pref: {top_2['score_breakdown']['employment_preference']['score']}/{top_2['score_breakdown']['employment_preference']['max_score']} | 
                        Loc: {top_2['score_breakdown']['local_opportunity']['score']}/{top_2['score_breakdown']['local_opportunity']['max_score']}
                    </div>
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; font-size: 0.9rem; color: #475569; margin-bottom: 12px;">
                        💼 <b>{'पसंद:' if active_lang_code != 'en' else 'Goal:'}</b> {top_2['employment_type']}
                    </div>
                    <div style="font-size: 0.9rem; color: #4A5568; line-height: 1.5;">
                        <b style="color: #2D3748;">💡 {'कारण / Rationale:' if active_lang_code != 'en' else 'Rationale:'}</b><br>
                        {' • '.join(top_2['why_recommended'][:2])}
                    </div>
                </div>
            """)

    # RANK #3 CARD
    with col_r3:
        if top_3:
            st.html(f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 6px solid #CBD5E1; border-radius: 12px; padding: 20px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <div style="background: #F8FAFC; color: #64748B; font-weight: 700; font-size: 0.85rem; padding: 4px 10px; border-radius: 20px; display: inline-block; margin-bottom: 12px; border: 1px solid #E2E8F0;">
                        🥉 {'रैंक #3 / Rank #3' if active_lang_code != 'en' else '🥉 Rank #3'}
                    </div>
                    <h3 style="color: #1A202C; margin: 0 0 8px 0; font-size: 1.2rem; font-weight: 700;">{top_3['job_role']}</h3>
                    <div style="color: #4A5568; font-size: 0.95rem; margin-bottom: 16px;">
                        🏢 <b>Sector:</b> {top_3['sector']}<br>
                        🎖️ <b>NSQF Level:</b> Level {top_3.get('nsqf_level', 4)}
                    </div>
                    <div style="display: flex; align-items: baseline; margin-bottom: 12px;">
                        <span style="font-size: 2.0rem; font-weight: 700; color: #64748B;">{top_3['score']}%</span>
                        <span style="color: #718096; font-size: 0.95rem; margin-left: 8px;">{'मेल (Score)' if active_lang_code != 'en' else 'Score'}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #718096; margin-bottom: 16px; background: #F8FAFC; padding: 6px 8px; border-radius: 6px; border: 1px solid #E2E8F0;">
                        <b>Breakdown:</b> Edu: {top_3['score_breakdown']['education']['score']}/{top_3['score_breakdown']['education']['max_score']} | 
                        Skill: {top_3['score_breakdown']['skill']['score']}/{top_3['score_breakdown']['skill']['max_score']} | 
                        Int: {top_3['score_breakdown']['interest']['score']}/{top_3['score_breakdown']['interest']['max_score']} | 
                        Mob: {top_3['score_breakdown']['mobility']['score']}/{top_3['score_breakdown']['mobility']['max_score']} | 
                        Pref: {top_3['score_breakdown']['employment_preference']['score']}/{top_3['score_breakdown']['employment_preference']['max_score']} | 
                        Loc: {top_3['score_breakdown']['local_opportunity']['score']}/{top_3['score_breakdown']['local_opportunity']['max_score']}
                    </div>
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; font-size: 0.9rem; color: #64748B; margin-bottom: 12px;">
                        💼 <b>{'पसंद:' if active_lang_code != 'en' else 'Goal:'}</b> {top_3['employment_type']}
                    </div>
                    <div style="font-size: 0.9rem; color: #4A5568; line-height: 1.5;">
                        <b style="color: #2D3748;">💡 {'कारण / Rationale:' if active_lang_code != 'en' else 'Rationale:'}</b><br>
                        {' • '.join(top_3['why_recommended'][:2])}
                    </div>
                </div>
            """)

    # -------------------------------------------------------------
    # 6. Skill Gap Analysis & Local Cluster Details
    # -------------------------------------------------------------
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.subheader("🔍 " + ("हुनर मिलान और स्थानीय अवसर (Skill Gap & Local Opportunity)" if active_lang_code != 'en' else "Skill Gap Analysis & Local Cluster Opportunity"))

    g1, g2 = st.columns(2)
    with g1:
        st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 18px;">
                <h4 style="color: #1E3A8A; margin-top: 0;">🛠️ {'मौजूदा हुनर बनाम ज़रूरी प्रशिक्षण' if active_lang_code != 'en' else 'Existing Skills vs Training Gap'}</h4>
                <p style="color: #475569; font-size: 0.95rem;">
                    <b>{'उपलब्ध हुनर (Matched Skills):' if active_lang_code != 'en' else 'Matched Skills:'}</b><br>
                    {''.join([f"<span class='skill-tag-matched'>✓ {s}</span>" for s in top_1['matched_skills']]) if top_1['matched_skills'] else "<span style='color:#64748B;'>None explicitly matched (Entry level)</span>"}
                </p>
                <p style="color: #475569; font-size: 0.95rem; margin-top: 10px;">
                    <b>{'सीखने योग्य हुनर (Training Needed):' if active_lang_code != 'en' else 'Skills to Build (Training Gap):'}</b><br>
                    {''.join([f"<span class='skill-tag-missing'>⚡ {s}</span>" for s in top_1['missing_skills']]) if top_1['missing_skills'] else "<span style='color:#047857;'>✓ 100% skill requirements matched!</span>"}
                </p>
            </div>
        """)

    with g2:
        st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 18px;">
                <h4 style="color: #1E3A8A; margin-top: 0;">📍 {'स्थानीय जिला अवसर और PM-AJAY सहायता' if active_lang_code != 'en' else 'Local District Opportunity & PM-AJAY Support'}</h4>
                <p style="color: #1E293B; font-size: 0.95rem; line-height: 1.5;">
                    🏢 <b>{'क्लस्टर विवरण / Cluster:' if active_lang_code != 'en' else 'Cluster Info:'}</b><br>
                    {top_1['local_opportunity']}
                </p>
                {'''<div style="background: #FEF3C7; border: 1px solid #FDE68A; border-radius: 6px; padding: 10px; font-size: 0.88rem; color: #92400E; margin-top: 10px;">
                    📌 <b>Potential PM-AJAY pathway:</b> Final eligibility and assistance depend on applicable government rules and verification.
                </div>''' if top_1['score_breakdown']['local_opportunity']['score'] > 0 else '''<div style="background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; font-size: 0.88rem; color: #475569; margin-top: 10px;">
                    📌 <b>Note:</b> No verified local opportunity data available for this specific role in your district.
                </div>'''}
            </div>
        """)

    # -------------------------------------------------------------
    # 7. "My Skill Journey" 4-Stage Pathway Roadmap
    # -------------------------------------------------------------
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.subheader("🗺️ " + ("मेरी कौशल यात्रा (My Skill Journey Pathway)" if active_lang_code != 'en' else "My Skill Journey: 4-Stage Actionable Pathway"))

    pathway = generate_skill_pathway(
        beneficiary_profile=profile,
        recommended_job_role=top_1,
        missing_skills=top_1["missing_skills"]
    )

    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

    with p_col1:
        st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #94A3B8; border-radius: 12px; padding: 16px; height: 100%; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                <div style="font-weight: 700; color: #475569; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">📍 1. {'वर्तमान स्थिति' if active_lang_code != 'en' else 'Current State'}</div>
                <p style="font-size: 0.88rem; color: #4A5568; margin: 8px 0 0 0; line-height: 1.4;">
                    {pathway.get('current_state', 'Candidate Profile')}
                </p>
            </div>
        """)

    with p_col2:
        st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #C6E0D5; border-radius: 12px; padding: 16px; height: 100%; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                <div style="font-weight: 700; color: #2D5A4C; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">📚 2. {'तकनीकी प्रशिक्षण' if active_lang_code != 'en' else 'Technical Training'}</div>
                <p style="font-size: 0.88rem; color: #4A5568; margin: 8px 0 0 0; line-height: 1.4;">
                    {' • '.join(pathway.get('training_stage', {}).get('learning_modules', ['NSQF Core Curriculum']))}
                </p>
            </div>
        """)

    with p_col3:
        st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #95CBB3; border-radius: 12px; padding: 16px; height: 100%; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                <div style="font-weight: 700; color: #1F4035; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">🛠️ 3. {'व्यावहारिक अनुभव' if active_lang_code != 'en' else 'Practical Lab'}</div>
                <p style="font-size: 0.88rem; color: #4A5568; margin: 8px 0 0 0; line-height: 1.4;">
                    {' • '.join(pathway.get('practical_stage', {}).get('practical_tasks', ['Hands-on Workshop Practice']))}
                </p>
            </div>
        """)

    with p_col4:
        st.html(f"""
            <div style="background: #E8F3EF; border: 1px solid #C6E0D5; border-top: 4px solid #2D5A4C; border-radius: 12px; padding: 16px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <div style="font-weight: 700; color: #2D5A4C; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">🎯 4. {'लक्ष्य रोजगार' if active_lang_code != 'en' else 'Target Livelihood'}</div>
                <p style="font-size: 0.88rem; color: #1F4035; margin: 8px 0 0 0; line-height: 1.4;">
                    <b style="color: #1A202C;">{top_1['job_role']}</b><br>
                    {top_1['employment_type']} (Potential PM-AJAY Pathway)
                </p>
            </div>
        """)


if __name__ == "__main__":
    st.set_page_config(page_title="Recommendations | Kaushal Marg", layout="wide")
    render_recommendations_page()
