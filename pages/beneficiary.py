"""
Kaushal Marg - Beneficiary Assistant Page
Voice-first, accessible interface with language selection, text fallback,
conversation transcript, progress indicator, continue button, and restart option.

Team: Binary Minds | SIH Problem Statement 26097
"""

import streamlit as st

def get_default_messages(is_hindi: bool):
    """Returns initial greeting message based on selected language."""
    if is_hindi:
        return [
            {
                "sender": "assistant",
                "text": "नमस्ते! मैं कौशल मार्ग सहायक हूँ। 🙏\n\nमैं आपको आपकी पढ़ाई, अनुभव और पसंद के आधार पर सही सरकारी हुनर (NSQF) और PM-AJAY योजना से जुड़े रोज़गार खोजने में मदद करूँगा।\n\nकृपया माइक दबाकर या नीचे लिखकर बताएं: **आपका नाम क्या है और आपकी क्या पढ़ाई हुई है?**"
            }
        ]
    else:
        return [
            {
                "sender": "assistant",
                "text": "Namaste! I am your Kaushal Marg assistant. 🙏\n\nI will help you find official government-certified skilling pathways (NSQF) and livelihood opportunities under PM-AJAY (GIA Component).\n\nPlease tap the microphone or type below: **What is your name, and what is your education level?**"
            }
        ]

def restart_interview(is_hindi: bool):
    """Resets conversation state to initial step."""
    st.session_state["beneficiary_step"] = 1
    st.session_state["chat_messages"] = get_default_messages(is_hindi)
    st.session_state["extracted_profile"] = {
        "name": "",
        "education": "",
        "skills": [],
        "interests": [],
        "district": "",
        "preference": "Self-Employment (GIA PM-AJAY)"
    }
    st.session_state["recording_active"] = False

def render_beneficiary_page():
    """Renders the accessible Beneficiary Voice Assistant page."""
    
    # -------------------------------------------------------------
    # 1. Header & Language Selection
    # -------------------------------------------------------------
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.markdown("""
            <div style="margin-bottom: 5px;">
                <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">
                    🎙️ कौशल सहायक | Beneficiary Assistant
                </h1>
                <p style="color: #4B5563; font-size: 1.05rem; margin: 4px 0 0 0;">
                    बोलकर या लिखकर अपनी जानकारी दें और अपने लिए सही सरकारी हुनर और रोज़गार जानें
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    with top_col2:
        # Language Selector
        lang = st.radio(
            "Language / भाषा:",
            options=["🇮🇳 हिंदी", "🇬🇧 English"],
            index=0 if st.session_state.get("beneficiary_lang", "हिंदी") == "हिंदी" else 1,
            horizontal=True,
            key="beneficiary_lang_radio"
        )
        is_hindi = "हिंदी" in lang
        st.session_state["beneficiary_lang"] = "हिंदी" if is_hindi else "English"

    # Initialize State
    if "beneficiary_step" not in st.session_state:
        st.session_state["beneficiary_step"] = 1
    if "chat_messages" not in st.session_state or not st.session_state["chat_messages"]:
        st.session_state["chat_messages"] = get_default_messages(is_hindi)
    if "extracted_profile" not in st.session_state:
        st.session_state["extracted_profile"] = {
            "name": "रमेश कुमार (Ramesh Kumar)",
            "education": "10th Pass",
            "skills": ["Tractor operation", "Basic farming"],
            "interests": ["Agriculture", "Machinery"],
            "district": "Indore",
            "preference": "Self-Employment (GIA PM-AJAY)"
        }

    step = st.session_state["beneficiary_step"]

    # -------------------------------------------------------------
    # 2. Step Progress Indicator & Controls
    # -------------------------------------------------------------
    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
    
    prog_col1, prog_col2, prog_col3, prog_col4 = st.columns([1, 1, 1, 0.8])
    with prog_col1:
        if step == 1:
            st.info("🔹 **1. बातचीत / Speak**\n\nअपनी जानकारी बताएं")
        else:
            st.success("✅ **1. बातचीत / Speak**\n\nपूर्ण (Completed)")
    with prog_col2:
        if step == 2:
            st.info("🔹 **2. पुष्टि / Review**\n\nप्रोफ़ाइल की जांच करें")
        elif step > 2:
            st.success("✅ **2. पुष्टि / Review**\n\nपूर्ण (Completed)")
        else:
            st.markdown("⚪ **2. पुष्टि / Review**\n\nप्रतीक्षारत (Pending)")
    with prog_col3:
        if step == 3:
            st.info("🔹 **3. अवसर / Pathway**\n\nहुनर और रोज़गार")
        else:
            st.markdown("⚪ **3. अवसर / Pathway**\n\nप्रतीक्षारत (Pending)")
    with prog_col4:
        st.write("")
        if st.button("🔄 " + ("रीस्टार्ट" if is_hindi else "Restart"), key="btn_restart_top", use_container_width=True, help="Reset conversation and start fresh"):
            restart_interview(is_hindi)
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Step 1: Active Spoken / Text Conversation
    # -------------------------------------------------------------
    if step == 1:
        layout_left, layout_right = st.columns([1.1, 1])

        # LEFT COLUMN: Voice Input & Text Fallback
        with layout_left:
            st.markdown(f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-bottom: 16px;">
                    <h3 style="color: #1E3A8A; margin: 0 0 4px 0; font-size: 1.15rem;">
                        {'🎙️ माइक्रोफ़ोन क्षेत्र (Voice Input)' if is_hindi else '🎙️ Microphone Area (Voice Input)'}
                    </h3>
                    <p style="color: #64748B; font-size: 0.9rem; margin: 0;">
                        {'माइक दबाकर बोलें या नीचे टेक्स्ट में लिखें' if is_hindi else 'Tap to speak or type in the box below'}
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # Prominent Microphone Button
            mic_active = st.session_state.get("recording_active", False)
            
            if not mic_active:
                if st.button("🔴 " + ("बोलना शुरू करें / Tap to Speak" if is_hindi else "Tap to Speak (Start Recording)"), type="primary", use_container_width=True, key="btn_mic_start"):
                    st.session_state["recording_active"] = True
                    st.rerun()
            else:
                st.warning("🟢 " + ("सुन रहे हैं... अपनी बात पूरी होने पर 'रोकें' दबाएं" if is_hindi else "Listening... Click Stop when finished speaking."))
                if st.button("⏹️ " + ("बोलना पूरा हुआ / Stop & Process" if is_hindi else "Stop Recording & Submit"), type="secondary", use_container_width=True, key="btn_mic_stop"):
                    st.session_state["recording_active"] = False
                    # Add dummy user spoken response
                    user_text = "मेरा नाम रमेश कुमार है, 10वीं पास हूँ। मुझे ट्रैक्टर चलाने और खेती के उपकरणों का अनुभव है। मैं इंदौर ज़िले में स्वरोज़गार शुरू करना चाहता हूँ।" if is_hindi else "My name is Ramesh Kumar, 10th pass. I have experience in tractor driving and farm equipment. I want to do self-employment in Indore district."
                    st.session_state["chat_messages"].append({"sender": "user", "text": user_text})
                    
                    # Assistant response
                    reply_text = "धन्यवाद रमेश जी! हमने आपकी जानकारी दर्ज कर ली है:\n- **शिक्षा:** 10वीं पास\n- **कौशल:** ट्रैक्टर संचालन और कृषि उपकरण\n- **ज़िला:** इंदौर (मध्य प्रदेश)\n- **लक्ष्य:** PM-AJAY GIA स्वरोज़गार\n\nकृपया पुष्टि के लिए आगे बढ़ें।" if is_hindi else "Thank you Ramesh! We have recorded your details:\n- **Education:** 10th Pass\n- **Skills:** Tractor operation & farm machinery\n- **District:** Indore (MP)\n- **Goal:** PM-AJAY GIA Self-Employment\n\nPlease proceed to review your profile."
                    st.session_state["chat_messages"].append({"sender": "assistant", "text": reply_text})
                    st.session_state["extracted_profile"] = {
                        "name": "रमेश कुमार (Ramesh Kumar)",
                        "education": "10th Pass",
                        "skills": ["Tractor operation", "Basic farming"],
                        "interests": ["Agriculture", "Machinery"],
                        "district": "Indore",
                        "preference": "Self-Employment (GIA PM-AJAY)"
                    }
                    st.rerun()

            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

            # TEXT FALLBACK
            st.markdown(f"##### {'⌨️ लिखकर बताएं (Text Fallback):' if is_hindi else '⌨️ Type Your Response (Text Fallback):'}")
            text_input_val = st.text_input(
                "Type message",
                placeholder="उदा: 10वीं पास, सिलाई का काम, जयपुर..." if is_hindi else "e.g. 10th pass, tailoring experience, Jaipur...",
                label_visibility="collapsed",
                key="beneficiary_text_input"
            )
            
            if st.button("💬 " + ("संदेश भेजें / Send" if is_hindi else "Send Message"), use_container_width=True, key="btn_send_text"):
                if text_input_val.strip():
                    st.session_state["chat_messages"].append({"sender": "user", "text": text_input_val})
                    # Dummy assistant confirmation
                    reply = "बहुत अच्छा! आपकी जानकारी दर्ज कर ली गई है। आप नीचे दिए गए 'आगे बढ़ें' बटन से अपनी प्रोफ़ाइल की पुष्टि कर सकते हैं।" if is_hindi else "Great! Your information has been noted. You can now proceed to review your profile summary."
                    st.session_state["chat_messages"].append({"sender": "assistant", "text": reply})
                    st.rerun()

            # QUICK PRESET DEMO PROFILES (10 Domains for Low Digital Literacy testing)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"##### {'⚡ 10 नमूना प्रोफ़ाइल चुनें (Pick from 10 Demo Profiles):' if is_hindi else '⚡ Pick from 10 Synthetic Demo Profiles:'}")
            
            from data.demo_profiles import SYNTHETIC_BENEFICIARY_PROFILES
            
            demo_labels = [
                f"{p['name']} ({p['domain_tag']} • {p['district']} • {p['employment_preference']})"
                for p in SYNTHETIC_BENEFICIARY_PROFILES
            ]
            
            selected_demo_idx = st.selectbox(
                "Select Demo Profile / नमूना प्रोफ़ाइल चुनें:",
                options=range(len(demo_labels)),
                format_func=lambda x: demo_labels[x],
                key="beneficiary_demo_profile_select"
            )
            
            if st.button("🚀 " + ("यह प्रोफ़ाइल लोड करें / Load Profile" if is_hindi else "Load This Demo Profile"), use_container_width=True, key="btn_load_demo_profile"):
                selected_p = SYNTHETIC_BENEFICIARY_PROFILES[selected_demo_idx]
                st.session_state["chat_messages"].append({
                    "sender": "user",
                    "text": f"नमस्ते! मेरा नाम {selected_p['name'].split(' ')[0]} है, {selected_p['education']}। मुझे {', '.join(selected_p['skills'])} का अनुभव है और मैं {selected_p['district']} में {selected_p['employment_preference']} के अवसर चाहता हूँ।"
                })
                st.session_state["chat_messages"].append({
                    "sender": "assistant",
                    "text": f"धन्यवाद! हमने आपकी जानकारी दर्ज कर ली है:\n- **शिक्षा:** {selected_p['education']}\n- **हुनर:** {', '.join(selected_p['skills'])}\n- **ज़िला:** {selected_p['district']}\n- **प्राथमिकता:** {selected_p['employment_preference']}\n\nकृपया आगे बढ़कर अपनी प्रोफ़ाइल की पुष्टि करें।"
                })
                st.session_state["extracted_profile"] = {
                    "name": selected_p["name"],
                    "education": selected_p["education"],
                    "skills": selected_p["skills"],
                    "interests": selected_p["interests"],
                    "district": selected_p["district"],
                    "mobility": selected_p["mobility"],
                    "employment_preference": selected_p["employment_preference"]
                }
                st.session_state["demo_profile"] = st.session_state["extracted_profile"]
                st.rerun()

        # RIGHT COLUMN: Interactive Conversation Transcript & Continue Button
        with layout_right:
            st.markdown(f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-bottom: 16px;">
                    <h3 style="color: #1E3A8A; margin: 0 0 4px 0; font-size: 1.15rem;">
                        {'💬 बातचीत का विवरण (Conversation)' if is_hindi else '💬 Conversation Transcript'}
                    </h3>
                    <p style="color: #64748B; font-size: 0.9rem; margin: 0;">
                        {'सहायक और आपके बीच हुई बातचीत' if is_hindi else 'Live transcript of the voice/text interaction'}
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # Chat Message Bubbles
            chat_container = st.container(height=340)
            with chat_container:
                for msg in st.session_state.get("chat_messages", []):
                    if msg["sender"] == "assistant":
                        st.markdown(f"""
                            <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 12px 16px; margin-bottom: 12px;">
                                <b style="color: #1E40AF;">🤖 कौशल सहायक (Assistant):</b><br>
                                <span style="color: #1E293B; font-size: 0.95rem; line-height: 1.5;">{msg["text"]}</span>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 12px 16px; margin-bottom: 12px; text-align: right;">
                                <b style="color: #166534;">👤 आप (Beneficiary):</b><br>
                                <span style="color: #14532D; font-size: 0.95rem; line-height: 1.5;">{msg["text"]}</span>
                            </div>
                        """, unsafe_allow_html=True)

            # Prominent Continue Button to Step 2
            st.write("")
            if st.button("👉 " + ("आगे बढ़ें: प्रोफ़ाइल की पुष्टि करें / Continue to Profile" if is_hindi else "Continue to Profile Summary 👉"), type="primary", use_container_width=True, key="btn_continue_to_step2"):
                st.session_state["beneficiary_step"] = 2
                st.rerun()

    # -------------------------------------------------------------
    # Step 2: Profile Review & Verification
    # -------------------------------------------------------------
    elif step == 2:
        profile = st.session_state.get("extracted_profile", {})
        
        st.markdown(f"""
            <div style="background-color: #EFF6FF; border: 1px solid #93C5FD; border-left: 5px solid #2563EB; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
                <h3 style="color: #1E40AF; margin-top: 0; font-size: 1.25rem;">
                    {'📋 आपकी जानकारी की पुष्टि (Verified Profile Summary)' if is_hindi else '📋 Profile Verification'}
                </h3>
                <p style="color: #334155; font-size: 1rem; margin-bottom: 0;">
                    {'कौशल सहायक ने बातचीत से यह विवरण तैयार किया है। कृपया जांचें:' if is_hindi else 'The voice assistant compiled the following details from your conversation:'}
                </p>
            </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"**👤 नाम / Name:** {profile.get('name', 'N/A')}")
            st.markdown(f"**🎓 शिक्षा / Education:** {profile.get('education', 'N/A')}")
            st.markdown(f"**📍 ज़िला / District:** {profile.get('district', 'N/A')}")
        with col_p2:
            st.markdown(f"**🛠️ पूर्व अनुभव / Skills:** {', '.join(profile.get('skills', [])) if profile.get('skills') else 'N/A'}")
            st.markdown(f"**💡 पसंदीदा क्षेत्र / Sector:** {', '.join(profile.get('interests', [])) if profile.get('interests') else 'N/A'}")
            st.markdown(f"**💼 रोज़गार प्राथमिकता / Preference:** {profile.get('preference', 'N/A')}")

        st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🔄 " + ("दोबारा बोलें / Edit & Speak Again" if is_hindi else "Edit & Speak Again"), use_container_width=True, key="btn_edit_again"):
                st.session_state["beneficiary_step"] = 1
                st.rerun()
        with btn_c2:
            if st.button("🚀 " + ("मेरा कौशल मार्ग देखें / Show Recommendations" if is_hindi else "Show Recommendations & Pathway 🚀"), type="primary", use_container_width=True, key="btn_show_recs_final"):
                st.session_state["demo_profile"] = profile
                st.session_state["active_nav"] = "🎯 Recommendations"
                st.session_state["sidebar_radio"] = "🎯 Recommendations"
                st.rerun()

    # -------------------------------------------------------------
    # Step 3: Transition to Recommendations
    # -------------------------------------------------------------
    elif step == 3:
        st.success("✅ " + ("आपकी प्रोफ़ाइल के आधार पर सरकारी NSQF हुनर और रोज़गार मार्ग तैयार हैं!" if is_hindi else "Your NSQF skilling pathway and livelihood options are ready!"))
        btn_a, btn_b = st.columns(2)
        with btn_a:
            if st.button("🔄 " + ("नई बातचीत शुरू करें / Start New Interview" if is_hindi else "Start New Interview"), use_container_width=True, key="btn_start_fresh"):
                restart_interview(is_hindi)
                st.rerun()
        with btn_b:
            if st.button("👉 " + ("सिफ़ारिशें और ट्रेनिंग देखें / View Recommendations" if is_hindi else "View Recommendations & Pathway 👉"), type="primary", use_container_width=True, key="btn_view_recs_now"):
                st.session_state["active_nav"] = "🎯 Recommendations"
                st.session_state["sidebar_radio"] = "🎯 Recommendations"
                st.rerun()


if __name__ == "__main__":
    st.set_page_config(page_title="Beneficiary Assistant | Kaushal Marg", layout="wide")
    render_beneficiary_page()
