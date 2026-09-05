"""
Kaushal Marg - Beneficiary Assistant Page
Real Browser-Microphone Voice & Text Conversational Assistant.
Connects Real Audio Recording -> AudioTranscriber -> ConversationManager -> ProfileExtractor -> NSQF Matcher.

Team: Binary Minds | SIH Problem Statement 26097
"""

import streamlit as st
import os
import json
import logging
import re
import html
import uuid
import hashlib
from typing import Dict, Any, List, Optional

# Person 1 (AI & Voice) Modules
from ai.conversation import ConversationManager, Language, Message
from ai.profile_extractor import ProfileExtractor, BeneficiaryProfile
from ai.gemini import GeminiConfigError, GeminiAPIError, GeminiQuotaError
from voice.tts import TTSEngine, prepare_utterance
from voice.audio import (
    AudioTranscriber,
    AudioProcessingError,
    UnsupportedLanguageError,
    UnsupportedMimeTypeError,
    TranscriptionResult,
    _MIN_AUDIO_BYTES
)

# Person 2 (Recommendation Engine & Pipeline) Modules
from recommendation.matcher import recommend_jobs
from recommendation.skill_gap import analyze_skill_gap
from recommendation.pathway import generate_skill_pathway
from integration.pipeline import AssessmentPipeline

# Person 3 (Database & Demo Profiles)
from database.database import (
    create_beneficiary,
    save_profile,
    save_conversation,
    save_recommendations_batch
)
from data.demo_profiles import SYNTHETIC_BENEFICIARY_PROFILES

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Trilingual Greetings & Fallbacks
# -----------------------------------------------------------------------------
GREETINGS = {
    "hi": "नमस्ते! मैं कौशल मार्ग सहायक हूँ। 🙏\n\nमैं आपकी पढ़ाई, अनुभव और पसंद के आधार पर सही NSQF-संरेखित हुनर और PM-AJAY योजना से जुड़े रोज़गार खोजने में मदद करूँगा।\n\nकृपया माइक दबाकर बोलें या नीचे लिखें: **आपका नाम, शिक्षा, और अनुभव क्या है?**",
    "en": "Namaste! I am your Kaushal Marg assistant. 🙏\n\nI will help you find official NSQF-aligned skilling pathways and livelihood opportunities under PM-AJAY (GIA Component).\n\nPlease tap the microphone or type below: **What is your name, education, and work experience?**",
    "mr": "नमस्कार! मी कौशल मार्ग सहायक आहे. 🙏\n\nमी तुमचे शिक्षण, अनुभव आणि आवडीनुसार योग्य NSQF-संरेखित कौशल्य आणि PM-AJAY योजनेअंतर्गत रोजगाराच्या संधी शोधण्यात मदत करेन.\n\nकृपया माइक दाबून बोला किंवा खाली लिहा: **तुमचे नाव, शिक्षण आणि अनुभव काय आहे?**"
}

# Removed FALLBACK_PROFILES to ensure real users start with an empty profile.


def init_session_state():
    """Initializes explicit state variables for consistent behavior."""
    if "active_nav" not in st.session_state:
        st.session_state["active_nav"] = "🏠 Home"
    if "selected_lang_code" not in st.session_state:
        st.session_state["selected_lang_code"] = "hi"
    if "beneficiary_step" not in st.session_state:
        st.session_state["beneficiary_step"] = 1
    if "is_demo" not in st.session_state:
        st.session_state["is_demo"] = False
    if "extracted_profile" not in st.session_state:
        st.session_state["extracted_profile"] = {}
    if "demo_profile" not in st.session_state:
        st.session_state["demo_profile"] = {}
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    if "current_beneficiary_id" not in st.session_state:
        st.session_state["current_beneficiary_id"] = None
    if "last_processed_audio_token" not in st.session_state:
        st.session_state["last_processed_audio_token"] = None
    if "api_calls" not in st.session_state:
        st.session_state["api_calls"] = 0
    if "last_api_error" not in st.session_state:
        st.session_state["last_api_error"] = None

def get_conversation_manager(lang_code: str):
    """Initializes or retrieves the ConversationManager from session state."""
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return None
        
    if "conv_manager" not in st.session_state or st.session_state.get("conv_manager_lang") != lang_code:
        try:
            st.session_state["conv_manager"] = ConversationManager(language=lang_code)
        except Exception as e:
            st.error(f"AI Assistant configuration failed: {e}")
            st.session_state["conv_manager"] = None
        st.session_state["conv_manager_lang"] = lang_code
    return st.session_state.get("conv_manager")




def render_tts_player(text: str, lang_code: str, element_key: str):
    """Renders a browser SpeechSynthesis audio read-aloud widget."""
    tts = TTSEngine()
    cfg = tts.prepare_utterance(text, language=lang_code)
    escaped_text = json.dumps(cfg.text)
    
    js_code = f"""
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
            
            function speakText_{element_key}() {{
                var synth = getSynth();
                if (synth) {{
                    synth.cancel();
                    var msg = new SpeechSynthesisUtterance({escaped_text});
                    msg.lang = '{cfg.lang}';
                    msg.rate = {cfg.rate};
                    msg.pitch = {cfg.pitch};
                    synth.speak(msg);
                }} else {{
                    alert('Browser speech synthesis is not supported on this device.');
                }}
            }}
            
            window.onload = function() {{
                if (!getSynth()) {{
                    var btn = document.getElementById('btn_{element_key}');
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
        <button id="btn_{element_key}" onclick="speakText_{element_key}()" style="background:#EFF6FF; border:1px solid #3B82F6; color:#1D4ED8; font-weight:600; padding:5px 10px; border-radius:6px; cursor:pointer; font-size:0.85rem; margin-top:4px;">
            🔊 {'सुनें (Listen)' if lang_code == 'hi' else ('ऐका (Listen)' if lang_code == 'mr' else 'Listen Aloud')}
        </button>
    """
    st.html(js_code)


def restart_interview(lang_code: str):
    """Resets interview state to Step 1."""
    st.session_state["beneficiary_step"] = 1
    
    # Fully clear real beneficiary session state
    st.session_state["current_beneficiary_id"] = None
    st.session_state["extracted_profile"] = {}
    st.session_state["demo_profile"] = {}
    st.session_state["is_demo"] = False
    st.session_state["last_processed_audio_token"] = None
    st.session_state["conv_manager_lang"] = lang_code
    
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        st.error("API Key not configured. Please set GEMINI_API_KEY to use Real AI Mode.")
        st.session_state["chat_messages"] = []
        return
        
    manager = get_conversation_manager(lang_code)
    if manager is None:
        st.session_state["chat_messages"] = []
        return
        
    try:
        greeting = manager.start_conversation()
        st.session_state["chat_messages"] = [{"sender": "assistant", "text": greeting}]
        st.session_state["api_calls"] += 1
    except GeminiQuotaError as e:
        st.session_state["last_api_error"] = f"Quota Exceeded ({e.retry_delay}s delay)"
        logger.error(f"Quota error starting conversation: {e}")
        st.session_state["chat_messages"] = [{"sender": "assistant", "text": GREETINGS.get(lang_code, GREETINGS["hi"])}]
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        st.session_state["chat_messages"] = [{"sender": "assistant", "text": GREETINGS.get(lang_code, GREETINGS["hi"])}]


def render_beneficiary_page():
    """Renders the comprehensive Trilingual Beneficiary Assistant interface."""
    
    active_lang_code = st.session_state.get("selected_lang_code", "hi")
    
    # -------------------------------------------------------------
    # 1. Header & Language Selection
    # -------------------------------------------------------------
    top_col1, top_col2 = st.columns([2.8, 1.2])
    with top_col1:
        if active_lang_code == "hi":
            st.html("""
                <div>
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">🎙️ कौशल सहायक | Beneficiary Assistant</h1>
                    <p style="color: #4B5563; font-size: 1.02rem; margin: 4px 0 0 0;">
                        माइक्रोफ़ोन से बोलकर या लिखकर अपनी जानकारी दें और सही सरकारी हुनर व PM-AJAY आजीविका जानें।
                    </p>
                </div>
            """)
        elif active_lang_code == "mr":
            st.html("""
                <div>
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">🎙️ कौशल्य सहाय्यक | Beneficiary Assistant</h1>
                    <p style="color: #4B5563; font-size: 1.02rem; margin: 4px 0 0 0;">
                        मायक्रोफोनद्वारे बोलून किंवा लिहून माहिती द्या आणि योग्य NSQF कौशल्य व PM-AJAY रोजगार शोधा.
                    </p>
                </div>
            """)
        else:
            st.html("""
                <div>
                    <h1 style="color: #1E3A8A; font-size: 2.1rem; margin: 0;">🎙️ Beneficiary Voice Assistant</h1>
                    <p style="color: #4B5563; font-size: 1.02rem; margin: 4px 0 0 0;">
                        Speak into the microphone or type to find NSQF-aligned skilling pathways and PM-AJAY livelihood opportunities.
                    </p>
                </div>
            """)
    
    with top_col2:
        lang_options = ["🇮🇳 हिंदी", "🇬🇧 English", "🇮🇳 मराठी"]
        lang_map = {"🇮🇳 हिंदी": "hi", "🇬🇧 English": "en", "🇮🇳 मराठी": "mr"}
        inv_lang_map = {v: k for k, v in lang_map.items()}
        
        current_choice = inv_lang_map.get(active_lang_code, "🇮🇳 हिंदी")
        selected_lang_label = st.radio(
            "Language / भाषा / भाषा निवडा:",
            options=lang_options,
            index=lang_options.index(current_choice),
            horizontal=True,
            key="beneficiary_lang_selector"
        )
        new_lang_code = lang_map[selected_lang_label]
        if new_lang_code != active_lang_code:
            st.session_state["selected_lang_code"] = new_lang_code
            active_lang_code = new_lang_code
            restart_interview(new_lang_code)
            st.rerun()

    # Initialize State
    init_session_state()

    if not st.session_state["chat_messages"]:
        manager = get_conversation_manager(active_lang_code)
        if manager is not None:
            try:
                greeting = manager.start_conversation()
                st.session_state["chat_messages"] = [{"sender": "assistant", "text": greeting}]
                st.session_state["api_calls"] += 1
            except GeminiQuotaError as e:
                st.session_state["last_api_error"] = f"Quota Exceeded ({e.retry_delay}s delay)"
                logger.error(f"Quota error starting conversation: {e}")
                st.session_state["chat_messages"] = [{"sender": "assistant", "text": GREETINGS.get(active_lang_code, GREETINGS["hi"])}]
            except Exception as e:
                logger.error(f"Failed to start conversation: {e}")
                st.session_state["chat_messages"] = [{"sender": "assistant", "text": GREETINGS.get(active_lang_code, GREETINGS["hi"])}]

    step = st.session_state["beneficiary_step"]

    # -------------------------------------------------------------
    # 2. Step Progress Indicator
    # -------------------------------------------------------------
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    # Modern horizontal stepper
    def get_step_style(current_step, target_step):
        if current_step > target_step: # Done
            return "background-color: #E8F3EF; color: #2D5A4C; border: 1px solid #C6E0D5;"
        elif current_step == target_step: # Active
            return "background-color: #2D5A4C; color: white; border: 1px solid #2D5A4C;"
        else: # Pending
            return "background-color: #F8FAFC; color: #94A3B8; border: 1px solid #E2E8F0;"
            
    step1_style = get_step_style(step, 1)
    step2_style = get_step_style(step, 2)
    step3_style = get_step_style(step, 3)
    
    st.html(f"""
<div style="display: flex; justify-content: space-between; align-items: center; max-width: 800px; margin: 0 auto 30px auto;">
    <!-- Step 1 -->
    <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
        <div style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; {step1_style} z-index: 2;">1</div>
        <div style="margin-top: 8px; font-size: 0.85rem; font-weight: {600 if step >= 1 else 400}; color: {'#2D3748' if step >= 1 else '#94A3B8'};">Interview</div>
    </div>
    <div style="height: 2px; background-color: {'#C6E0D5' if step > 1 else '#E2E8F0'}; flex: 2; margin-top: -24px;"></div>
    
    <!-- Step 2 -->
    <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
        <div style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; {step2_style} z-index: 2;">2</div>
        <div style="margin-top: 8px; font-size: 0.85rem; font-weight: {600 if step >= 2 else 400}; color: {'#2D3748' if step >= 2 else '#94A3B8'};">Review</div>
    </div>
    <div style="height: 2px; background-color: {'#C6E0D5' if step > 2 else '#E2E8F0'}; flex: 2; margin-top: -24px;"></div>
    
    <!-- Step 3 -->
    <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
        <div style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; {step3_style} z-index: 2;">3</div>
        <div style="margin-top: 8px; font-size: 0.85rem; font-weight: {600 if step >= 3 else 400}; color: {'#2D3748' if step >= 3 else '#94A3B8'};">Recommendations</div>
    </div>
</div>
""")
    
    col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
    with col_reset3:
        if st.button("🔄 " + ("नया असेसमेंट / Restart" if active_lang_code == "hi" else ("नवीन असेसमेंट / Restart" if active_lang_code == "mr" else "Start New Assessment")), key="btn_restart_interview", use_container_width=True):
            restart_interview(active_lang_code)
            st.rerun()

    # -------------------------------------------------------------
    # STEP 1: Conversational Interview (Real Voice & Text)
    # -------------------------------------------------------------
    if step == 1:
        col_input, col_chat = st.columns([1.1, 1])

        with col_input:
            st.html("""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-bottom: 14px;">
                    <h3 style="color: #1E3A8A; margin: 0 0 4px 0; font-size: 1.15rem;">
                        🎙️ Browser Microphone / Voice Input
                    </h3>
                    <p style="color: #64748B; font-size: 0.9rem; margin: 0;">
                        Click the microphone below to record speech. Audio bytes are captured and transcribed via Gemini Multimodal STT.
                    </p>
                </div>
            """)

            # REAL STREAMLIT BROWSER MICROPHONE RECORDING WIDGET
            rec_label = (
                "🎙️ बोलकर उत्तर दें (Click to Record Voice):" if active_lang_code == "hi"
                else ("🎙️ आवाजात उत्तर द्या (Click to Record Voice):" if active_lang_code == "mr"
                else "🎙️ Record Voice Response (Click to Record):")
            )
            
            recorded_audio = st.audio_input(
                label=rec_label,
                key="real_browser_mic_input"
            )

            # Process Live Recorded Audio Bytes
            if recorded_audio is not None:
                audio_bytes = recorded_audio.getvalue()
                raw_mime = getattr(recorded_audio, "type", "audio/wav") or "audio/wav"
                
                # TASK 1: SAFE DIAGNOSTICS DISPLAY
                with st.expander("📊 Audio Pipeline Diagnostics (Live)", expanded=False):
                    diag_c1, diag_c2 = st.columns(2)
                    with diag_c1:
                        st.write("**Audio Object Received:** `True`")
                        st.write(f"**Python Type:** `{type(recorded_audio).__name__}`")
                        transcription_model_ph = st.empty()
                    with diag_c2:
                        st.write(f"**Byte Length:** `{len(audio_bytes):,} bytes` ({len(audio_bytes)/1024:.1f} KB)")
                        st.write(f"**MIME Type:** `{raw_mime}`")
                        transcription_status_ph = st.empty()

                # Unique token to prevent duplicate runs on Streamlit reruns
                audio_token = f"{len(audio_bytes)}_{raw_mime}_{hashlib.sha256(audio_bytes).hexdigest()}"
                if st.session_state.get("last_processed_audio_token") != audio_token:
                    if st.session_state.get("is_demo"):
                        st.error("⚠️ You are currently in Demo Mode. Please click 'Start New Assessment' to record a real profile.")
                    else:
                        st.session_state["last_processed_audio_token"] = audio_token
                        
                        # TASK 2: EXPLICIT SIZE CHECKS
                        if len(audio_bytes) == 0:
                            st.error("⚠️ " + (
                                "ऑडियो रिकॉर्डिंग खाली है। कृपया माइक्रोफ़ोन अनुमति की जाँच करें और पुनः प्रयास करें。" if active_lang_code == "hi"
                                else ("ऑडिओ रेकॉर्डिंग रिकामे आहे. कृपया मायक्रोफोन परवानगी तपासा." if active_lang_code == "mr"
                                else "Audio recording was empty. Please check microphone permission and try again.")
                            ))
                        elif len(audio_bytes) < _MIN_AUDIO_BYTES:
                            st.error("⚠️ " + (
                                f"रिकॉर्डिंग बहुत छोटी है ({len(audio_bytes)} bytes)। कृपया माइक के पास साफ़ आवाज़ में बोलें。" if active_lang_code == "hi"
                                else (f"रेकॉर्डिंग खूप लहान आहे ({len(audio_bytes)} bytes). कृपया पुन्हा स्पष्ट बोला." if active_lang_code == "mr"
                                else f"Audio payload is too small ({len(audio_bytes)} bytes < {_MIN_AUDIO_BYTES} min). Please speak clearly into your microphone.")
                            ))
                        else:
                            spinner_msg = (
                                "आवाज़ को समझा जा रहा है (Transcribing audio via Gemini)..." if active_lang_code == "hi"
                            else ("आवाज समजून घेतला जात आहे (Transcribing audio via Gemini)..." if active_lang_code == "mr"
                            else "Transcribing speech via Gemini Multimodal STT...")
                        )
                        with st.spinner(f"⏳ {spinner_msg}"):
                            try:
                                transcriber = AudioTranscriber()
                                transcription_model_ph.write(f"**Transcription Model:** `{transcriber._gemini.model}`")
                                result = transcriber.transcribe(
                                    audio_bytes=audio_bytes,
                                    language=active_lang_code,
                                    mime_type=raw_mime
                                )
                                
                                # TASK 9: EMPTY TRANSCRIPTION ERROR HANDLING
                                if result.is_empty or not result.text.strip():
                                    transcription_status_ph.write("**Transcription Status:** `EMPTY`")
                                    st.warning("⚠️ " + (
                                        "ऑडियो से कोई स्पष्ट शब्द प्राप्त नहीं हुए। कृपया माइक के पास साफ़ बोलें या नीचे लिखकर बताएं।" if active_lang_code == "hi"
                                        else ("कोणताही स्पष्ट आवाज आढळला नाही. कृपया पुन्हा बोला किंवा लिहून सांगा." if active_lang_code == "mr"
                                        else "No clear speech was detected. Please speak again.")
                                    ))
                                else:
                                    transcription_status_ph.write("**Transcription Status:** `SUCCESS`")
                                    transcribed_text = result.text.strip()
                                    st.session_state["chat_messages"].append({"sender": "user", "text": transcribed_text, "input_mode": "voice"})
                                    

                                    # Formulate conversational assistant response
                                    manager = get_conversation_manager(active_lang_code)
                                    try:
                                        st.session_state["api_calls"] += 1
                                        assistant_reply = manager.send_message(transcribed_text)
                                        st.session_state["chat_messages"].append({"sender": "assistant", "text": assistant_reply})
                                    except GeminiQuotaError as e:
                                        st.session_state["last_api_error"] = f"Quota Exceeded ({e.retry_delay}s delay)"
                                        err_msg = (
                                            f"Gemini API कोटा समाप्त हो गया है। कृपया {e.retry_delay} सेकंड बाद प्रयास करें या डेमो मोड का उपयोग करें।" if active_lang_code == "hi"
                                            else (f"Gemini API कोटा संपला आहे. कृपया {e.retry_delay} सेकंदांनंतर प्रयत्न करा किंवा डेमो मोड वापरा." if active_lang_code == "mr"
                                            else "Gemini quota is temporarily unavailable. You can continue with text input or Demo Mode.")
                                        )
                                        st.error(f"⚠️ {err_msg}")
                                    except Exception as e:
                                        logger.error(f"Failed to get AI response: {e}")
                                        st.error(f"⚠️ " + (
                                            f"Gemini API त्रुटि: {e}. कृपया लिखकर पुनः प्रयास करें。" if active_lang_code == "hi"
                                            else (f"Gemini API त्रुटी: {e}. कृपया लिहून पुन्हा प्रयत्न करा." if active_lang_code == "mr"
                                            else f"Gemini API Error: {e}. Please try again by typing your response.")
                                        ))
                                    st.rerun()

                            except GeminiQuotaError as e:
                                transcription_status_ph.write(f"**Transcription Status:** `FAILED ({type(e).__name__})`")
                                st.session_state["last_api_error"] = f"Quota Exceeded ({e.retry_delay}s delay)"
                                err_msg = (
                                    f"Gemini API कोटा समाप्त हो गया है। कृपया {e.retry_delay} सेकंड बाद प्रयास करें या डेमो मोड का उपयोग करें।" if active_lang_code == "hi"
                                    else (f"Gemini API कोटा संपला आहे. कृपया {e.retry_delay} सेकंदांनंतर प्रयत्न करा किंवा डेमो मोड वापरा." if active_lang_code == "mr"
                                    else "Gemini quota is temporarily unavailable. You can continue with text input or Demo Mode.")
                                )
                                st.error(f"⚠️ {err_msg}")

                            except GeminiAPIError as e:
                                transcription_status_ph.write(f"**Transcription Status:** `FAILED ({type(e).__name__})`")
                                err_msg = (
                                    "ध्वनि प्रतिलेखन सेवा वर्तमान में अनुपलब्ध है। कृपया अपना उत्तर टाइप करें या बाद में पुनः प्रयास करें।" if active_lang_code == "hi"
                                    else ("व्हॉईस ट्रान्सक्रिप्शन सेवा सध्या अनुपलब्ध आहे. कृपया आपले उत्तर टाइप करा किंवा नंतर पुन्हा प्रयत्न करा." if active_lang_code == "mr"
                                    else "The voice transcription service is currently unavailable. Please type your response or try again later.")
                                )
                                st.error(f"⚠️ {err_msg}")

                            except GeminiConfigError as e:
                                transcription_status_ph.write(f"**Transcription Status:** `FAILED ({type(e).__name__})`")
                                st.error("⚠️ " + (
                                    "Gemini API Key सेट नहीं है (GEMINI_API_KEY environment variable is not configured). वास्तविक वॉइस ट्रांसक्रिप्शन के लिए वैध Gemini API Key आवश्यक है। आप नीचे लिखकर उत्तर दे सकते हैं या नमूना प्रोफ़ाइल चुन सकते हैं。" if active_lang_code == "hi"
                                    else ("Gemini API Key सेट नाही. व्हॉईस ट्रान्सक्रिप्शनसाठी GEMINI_API_KEY आवश्यक आहे. आपण खाली लिहू शकता किंवा नमुना प्रोफाईल निवडू शकता." if active_lang_code == "mr"
                                    else "GEMINI_API_KEY is not configured in .env. Real voice transcription requires a valid Gemini API key. Please type your answer or select a demo scenario.")
                                ))
                            except UnsupportedLanguageError as e:
                                transcription_status_ph.write(f"**Transcription Status:** `FAILED ({type(e).__name__})`")
                                st.error(f"⚠️ Unsupported language for voice transcription: {e}")
                            except UnsupportedMimeTypeError as e:
                                transcription_status_ph.write(f"**Transcription Status:** `FAILED ({type(e).__name__})`")
                                st.error(f"⚠️ Unsupported audio MIME type ({raw_mime}): {e}")
                            except AudioProcessingError as e:
                                transcription_status_ph.write(f"**Transcription Status:** `EMPTY`")
                                st.warning("⚠️ " + (
                                    "ऑडियो से कोई स्पष्ट शब्द प्राप्त नहीं हुए। कृपया माइक के पास साफ़ बोलें या नीचे लिखकर बताएं।" if active_lang_code == "hi"
                                    else ("कोणताही स्पष्ट आवाज आढळला नाही. कृपया पुन्हा बोला किंवा लिहून सांगा." if active_lang_code == "mr"
                                    else "No clear speech was detected. Please speak again.")
                                ))
                            except Exception as e:
                                transcription_status_ph.write(f"**Transcription Status:** `FAILED ({type(e).__name__})`")
                                st.error(f"⚠️ Unexpected error processing audio recording.")

            # Text Fallback Input
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### ⌨️ " + ("या लिखकर उत्तर दें (Text Input):" if active_lang_code == "hi" else ("किंवा लिहून उत्तर द्या (Text Input):" if active_lang_code == "mr" else "Or Type Your Response (Text Input):")))
            
            with st.form(key="user_text_form", clear_on_submit=True):
                user_typed = st.text_input(
                    label="Response text",
                    placeholder="उदा. 10वीं पास, सिलाई का अनुभव, भोपाल, स्वरोज़गार..." if active_lang_code == "hi" else ("उदा. 10वी पास, ट्रॅक्टर चालवणे, पुणे..." if active_lang_code == "mr" else "e.g. My name is Suresh, 12th pass, tailoring experience..."),
                    label_visibility="collapsed"
                )
                submit_text = st.form_submit_button("📩 " + ("भेजें / Submit" if active_lang_code == "hi" else ("पाठवा / Submit" if active_lang_code == "mr" else "Send Message")), use_container_width=True)
                
                if submit_text and user_typed.strip():
                    st.session_state["chat_messages"].append({"sender": "user", "text": user_typed.strip(), "input_mode": "text"})
                    

                    # Assistant acknowledgement
                    manager = get_conversation_manager(active_lang_code)
                    try:
                        st.session_state["api_calls"] += 1
                        reply = manager.send_message(user_typed.strip())
                        st.session_state["chat_messages"].append({"sender": "assistant", "text": reply})
                    except GeminiQuotaError as e:
                        st.session_state["last_api_error"] = f"Quota Exceeded ({e.retry_delay}s delay)"
                        err_msg = (
                            f"Gemini API कोटा समाप्त हो गया है। कृपया {e.retry_delay} सेकंड बाद प्रयास करें या डेमो मोड का उपयोग करें。" if active_lang_code == "hi"
                            else (f"Gemini API कोटा संपला आहे. कृपया {e.retry_delay} सेकंदांनंतर प्रयत्न करा किंवा डेमो मोड वापरा." if active_lang_code == "mr"
                            else f"Gemini API quota has been reached. Please try again after approximately {e.retry_delay} seconds, or use text/demo mode.")
                        )
                        st.error(f"⚠️ {err_msg}")
                    except Exception as e:
                        logger.error(f"Failed to get AI response: {e}")
                        st.error(f"⚠️ " + (
                            f"Gemini API त्रुटि: {e}. कृपया पुनः प्रयास करें。" if active_lang_code == "hi"
                            else (f"Gemini API त्रुटी: {e}. कृपया पुन्हा प्रयत्न करा." if active_lang_code == "mr"
                            else f"Gemini API Error: {e}. Please try again.")
                        ))
                    st.rerun()

            # TASK 6: DEVELOPER AUDIO TEST UTILITY
            with st.expander("🛠️ Developer Audio Test (File Upload / Pre-Recorded Sample)", expanded=False):
                st.caption("Test the Gemini audio transcription pipeline with pre-recorded files to isolate browser microphone vs API issues.")
                
                uploaded_test_file = st.file_uploader(
                    "Upload Audio File (.wav, .mp3, .ogg, .webm):",
                    type=["wav", "mp3", "ogg", "webm", "mp4"],
                    key="dev_test_file_uploader"
                )
                
                if uploaded_test_file is not None:
                    file_bytes = uploaded_test_file.getvalue()
                    file_mime = getattr(uploaded_test_file, "type", "audio/wav") or "audio/wav"
                    st.info(f"File: `{uploaded_test_file.name}` | Size: `{len(file_bytes):,} bytes` | MIME: `{file_mime}`")
                    
                    if st.button("🧪 Transcribe Uploaded File", key="btn_transcribe_uploaded_dev"):
                        try:
                            t_dev = AudioTranscriber()
                            res_dev = t_dev.transcribe(file_bytes, language=active_lang_code, mime_type=file_mime)
                            st.success(f"**Transcribed Text:** {res_dev.text}")
                            
                            # Add to conversation
                            st.session_state["chat_messages"].append({"sender": "user", "text": res_dev.text, "input_mode": "voice"})

                            manager = get_conversation_manager(active_lang_code)
                            try:
                                reply = manager.send_message(res_dev.text)
                                st.session_state["chat_messages"].append({"sender": "assistant", "text": reply})
                            except Exception as e:
                                logger.error(f"Dev Test Assistant Error: {e}")
                                st.error(f"Assistant API Error: {e}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Dev Test Error: {e}")

                if os.path.exists("test_speech.wav"):
                    if st.button("▶️ Test with Sample Suresh Tailoring Audio (test_speech.wav)", key="btn_test_suresh_sample"):
                        with open("test_speech.wav", "rb") as sf:
                            sample_bytes = sf.read()
                        try:
                            t_dev = AudioTranscriber()
                            res_dev = t_dev.transcribe(sample_bytes, language="en", mime_type="audio/wav")
                            st.success(f"**Transcribed Text:** {res_dev.text}")
                            
                            st.session_state["chat_messages"].append({"sender": "user", "text": res_dev.text, "input_mode": "voice"})

                            manager = get_conversation_manager("en")
                            try:
                                reply = manager.send_message(res_dev.text)
                                st.session_state["chat_messages"].append({"sender": "assistant", "text": reply})
                            except Exception as e:
                                logger.error(f"Sample Test Assistant Error: {e}")
                                st.error(f"Assistant API Error: {e}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Sample Test Error: {e}")

            # Clearly Labelled Separate Demo Scenario Tool
            st.markdown("<br>", unsafe_allow_html=True)
            st.html("""
                <div style="background-color: #FEF3C7; border: 1px solid #FDE68A; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                    <b style="color: #92400E;">⚡ Demo Scenarios (Pre-Loaded Test Profiles)</b><br>
                    <span style="color: #78350F; font-size: 0.85rem;">
                        Judges & Evaluators can instantly test 10 realistic synthetic profiles across domains without microphone setup.
                    </span>
                </div>
            """)
            
            demo_labels = [
                f"{p['name']} ({p['domain_tag']} • {p['district']} • {p['employment_preference']})"
                for p in SYNTHETIC_BENEFICIARY_PROFILES
            ]
            
            sel_demo_idx = st.selectbox(
                "Select demo scenario:",
                options=range(len(demo_labels)),
                format_func=lambda x: demo_labels[x],
                key="sel_demo_scen",
                label_visibility="collapsed"
            )
            
            if st.button("🚀 " + ("यह नमूना प्रोफ़ाइल लोड करें / Load Demo Scenario" if active_lang_code == "hi" else ("ही नमुना प्रोफाईल लोड करा / Load Demo" if active_lang_code == "mr" else "Load Selected Demo Scenario")), use_container_width=True):
                p_loaded = SYNTHETIC_BENEFICIARY_PROFILES[sel_demo_idx]
                user_msg = f"[Demo Scenario] Name: {p_loaded['name']}, Education: {p_loaded['education']}, Skills: {', '.join(p_loaded['skills'])}, District: {p_loaded['district']}, Goal: {p_loaded['employment_preference']}."
                assist_msg = f"Loaded Demo Profile for **{p_loaded['name']}**.\n- **Education:** {p_loaded['education']}\n- **Skills:** {', '.join(p_loaded['skills'])}\n- **District:** {p_loaded['district']}\n- **Goal:** {p_loaded['employment_preference']}\n\nPlease proceed to review."
                
                st.session_state["chat_messages"] = []
                st.session_state["chat_messages"].append({"sender": "user", "text": user_msg})
                st.session_state["chat_messages"].append({"sender": "assistant", "text": assist_msg})
                st.session_state["extracted_profile"] = {
                    "name": p_loaded.get("name"),
                    "age": p_loaded.get("age"),
                    "education": p_loaded.get("education"),
                    "current_occupation": p_loaded.get("current_occupation"),
                    "work_experience": p_loaded.get("work_experience"),
                    "family_occupation": p_loaded.get("family_occupation"),
                    "skills": list(p_loaded.get("skills") or []),
                    "interests": list(p_loaded.get("interests") or []),
                    "aspirations": p_loaded.get("aspirations"),
                    "district": p_loaded.get("district"),
                    "local_context": p_loaded.get("local_context"),
                    "mobility": p_loaded.get("mobility"),
                    "employment_preference": p_loaded.get("employment_preference"),
                    "constraints": p_loaded.get("constraints")
                }
                st.session_state["is_demo"] = True
                st.session_state["current_beneficiary_id"] = None
                st.session_state["beneficiary_step"] = 2
                st.rerun()

        # Chat Transcript Column
        with col_chat:
            st.html("""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-bottom: 14px;">
                    <h3 style="color: #1E3A8A; margin: 0 0 4px 0; font-size: 1.15rem;">
                        💬 Conversation Transcript / बातचीत का विवरण
                    </h3>
                    <p style="color: #64748B; font-size: 0.9rem; margin: 0;">
                        Live multilingual conversation transcript between assistant and beneficiary.
                    </p>
                </div>
            """)

            # Chat Bubbles
            for i, msg in enumerate(st.session_state["chat_messages"]):
                safe_text = html.escape(str(msg['text']))
                if msg["sender"] == "assistant":
                    st.html(f"""
                        <div style="background-color: #E8F3EF; border: 1px solid #C6E0D5; border-left: 5px solid #2D5A4C; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                            <b style="color: #2D5A4C; display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">🎙️ Kaushal Marg Assistant:</b>
                            <span style="color: #2D3748; font-size: 0.95rem; line-height: 1.5; white-space: pre-line;">{safe_text}</span>
                        </div>
                    """)
                    render_tts_player(msg["text"], active_lang_code, f"chat_tts_{i}")
                else:
                    st.html(f"""
                        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-right: 5px solid #64748B; border-radius: 12px; padding: 16px; margin-bottom: 12px; text-align: right; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                            <b style="color: #475569; display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-bottom: 6px;">👤 You (Beneficiary):</b>
                            <span style="color: #2D3748; font-size: 0.95rem; line-height: 1.5; white-space: pre-line;">{safe_text}</span>
                        </div>
                    """)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➡️ " + ("आगे बढ़ें: प्रोफ़ाइल पुष्टि / Continue to Profile Review" if active_lang_code == "hi" else ("पुढे जा: माहिती खात्री / Continue" if active_lang_code == "mr" else "Continue to Profile Review ➡️")), type="primary", use_container_width=True, key="btn_goto_step2"):
                if st.session_state.get("is_demo"):
                    st.session_state["beneficiary_step"] = 2
                    st.rerun()
                else:
                    with st.spinner("Extracting profile from conversation..."):
                        extractor = ProfileExtractor()
                    try:
                        from ai.conversation import Message
                        # Convert dict messages to Message objects
                        msg_objs = [
                            Message(
                                role="user" if m["sender"] == "user" else "assistant", 
                                content=m["text"], 
                                language=active_lang_code
                            ) 
                            for m in st.session_state["chat_messages"]
                        ]
                        extracted = extractor.extract_profile(msg_objs)
                        if not extracted:
                            raise ValueError("Extraction returned empty profile")
                        st.session_state["extracted_profile"] = extracted
                        st.session_state["extraction_failed"] = False
                        st.session_state["beneficiary_step"] = 2
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Profile extraction failed: {e}")
                        st.session_state["extraction_failed"] = True
            
            if st.session_state.get("extraction_failed"):
                st.error("⚠️ Failed to automatically extract profile from conversation. You can provide more details or enter manually.")
                if st.button("✍️ Enter details manually / मैन्युअल दर्ज करें", key="btn_manual_fallback", use_container_width=True):
                    st.session_state["extracted_profile"] = {}
                    st.session_state["extraction_failed"] = False
                    st.session_state["beneficiary_step"] = 2
                    st.rerun()

            st.info("🔒 **Privacy Notice**: Information provided here is processed solely for NSQF skilling recommendations. Conversation transcripts and assessed profiles are stored securely in your local environment. You may request data deletion at any time via the admin dashboard.")

    # -------------------------------------------------------------
    # STEP 2: Profile Confirmation & Editing
    # -------------------------------------------------------------
    elif step == 2:
        st.subheader("📋 " + ("अपनी जानकारी की पुष्टि करें (Step 2: Profile Confirmation)" if active_lang_code == "hi" else ("आपल्या माहितीची खात्री करा (Step 2: Profile Confirmation)" if active_lang_code == "mr" else "Step 2: Beneficiary Profile Confirmation")))
        st.caption("Review and adjust your skilling attributes before running the NSQF recommendation engine.")
        if st.session_state.get("is_demo"):
            st.warning("⚠️ **Synthetic Demo Data — not a real beneficiary record**. This profile will not be saved to the database.")

        cur_p = st.session_state.get("extracted_profile", {})
        
        # Profile Completion Indicator
        req_fields = [
            bool(cur_p.get("education")),
            bool(cur_p.get("skills") or cur_p.get("work_experience")),
            bool(cur_p.get("district")),
            bool(cur_p.get("employment_preference"))
        ]
        completion = sum(req_fields)
        st.progress(completion / 4.0)
        if completion == 4:
            st.success("🌟 Profile 100% Complete! Ready for precise recommendations.")
        else:
            st.info(f"📊 Profile {completion}/4 Complete. Missing fields may affect recommendation accuracy.")

        with st.form(key="profile_confirm_form"):
            r1_col1, r1_col2 = st.columns(2)
            with r1_col1:
                name_val = st.text_input("👤 Full Name / नाम:", value=cur_p.get("name") or "")
                
                age_str = st.text_input("📅 Age / उम्र:", value=str(cur_p.get("age")) if cur_p.get("age") is not None else "")
                age_val = int(age_str) if age_str.isdigit() else None
                
                edu_options = ["", "5th Pass", "8th Pass", "10th Pass", "12th Pass", "ITI", "Diploma", "Graduate"]
                default_edu = cur_p.get("education") or ""
                edu_idx = edu_options.index(default_edu) if default_edu in edu_options else 0
                edu_val = st.selectbox("🎓 Education Level / शिक्षा:", options=edu_options, index=edu_idx)
                
                occ_val = st.text_input("💼 Current Occupation / वर्तमान पेशा:", value=cur_p.get("current_occupation") or "")
                
                fam_occ_val = st.text_input("👨‍👩‍👦 Family/Traditional Occupation / पारिवारिक पेशा:", value=cur_p.get("family_occupation") or "")
                
                dist_val = st.text_input("📍 District / ज़िला:", value=cur_p.get("district") or "")
                
                mob_options = ["", "Local", "District Level", "State Wide"]
                default_mob = cur_p.get("mobility") or ""
                mob_idx = mob_options.index(default_mob) if default_mob in mob_options else 0
                mob_val = st.selectbox("🚶 Mobility / गतिशीलता:", options=mob_options, index=mob_idx)

            with r1_col2:
                exp_val = st.text_input("⏳ Work Experience / कार्य अनुभव:", value=cur_p.get("work_experience") or "")
                
                pref_options = ["", "Self-Employment", "Wage-Employment", "Any"]
                default_pref = cur_p.get("employment_preference") or ""
                if "Self" in default_pref: default_pref = "Self-Employment"
                elif "Wage" in default_pref: default_pref = "Wage-Employment"
                
                pref_idx = pref_options.index(default_pref) if default_pref in pref_options else 0
                pref_val = st.selectbox("🎯 Employment Goal / पसंद:", options=pref_options, index=pref_idx)
                
                asp_val = st.text_input("🚀 Aspirations / लक्ष्य:", value=cur_p.get("aspirations") or "")
                
                const_val = st.text_input("⚠️ Constraints / बाधाएं:", value=cur_p.get("constraints") or "")
                
                local_ctx_val = st.text_input("🌍 Local Context/Broader Location / स्थानीय संदर्भ:", value=cur_p.get("local_context") or "")

            skills_str = st.text_input("🛠️ Existing Skills (Comma-separated) / हुनर:", value=", ".join(cur_p.get("skills") or []))
            interests_str = st.text_input("💡 Areas of Interest (Comma-separated) / रुचियां:", value=", ".join(cur_p.get("interests") or []))

            submit_confirm = st.form_submit_button("🎯 " + ("कौशल मार्ग और अवसर खोजें / Find My NSQF Opportunities" if active_lang_code == "hi" else ("माझे कौशल्य मार्ग शोधा / Find Opportunities" if active_lang_code == "mr" else "Generate NSQF Recommendations & Pathway 🚀")), type="primary", use_container_width=True)
            
            if submit_confirm:
                parsed_skills = [s.strip() for s in skills_str.split(",") if s.strip()]
                parsed_interests = [i.strip() for i in interests_str.split(",") if i.strip()]
                
                confirmed_profile = {
                    "name": name_val if name_val.strip() else None,
                    "age": age_val,
                    "education": edu_val if edu_val else None,
                    "current_occupation": occ_val if occ_val.strip() else None,
                    "work_experience": exp_val if exp_val.strip() else None,
                    "family_occupation": fam_occ_val if fam_occ_val.strip() else None,
                    "skills": parsed_skills,
                    "interests": parsed_interests,
                    "aspirations": asp_val if asp_val.strip() else None,
                    "district": dist_val if dist_val else None,
                    "local_context": local_ctx_val if local_ctx_val.strip() else None,
                    "mobility": mob_val if mob_val else None,
                    "employment_preference": pref_val if pref_val else None,
                    "constraints": const_val if const_val.strip() else None
                }
                st.session_state["extracted_profile"] = confirmed_profile
                st.session_state["demo_profile"] = confirmed_profile
                
                # Centralized Assessment Pipeline
                pipeline = AssessmentPipeline()
                is_demo_mode = st.session_state.get("is_demo", False)
                
                # Setup current_beneficiary_id if it's not set
                if not is_demo_mode and not st.session_state.get("current_beneficiary_id"):
                    b_id = create_beneficiary(
                        name=name_val,
                        preferred_language=active_lang_code,
                        district=dist_val
                    )
                    st.session_state["current_beneficiary_id"] = b_id
                    
                    # Save conversation history ONLY when creating the beneficiary
                    for msg in st.session_state.get("chat_messages", []):
                        mode = msg.get("input_mode", "text") if msg["sender"] == "user" else "text"
                        save_conversation(
                            beneficiary_id=b_id,
                            sender="user" if msg["sender"] == "user" else "assistant",
                            message_text=msg["text"],
                            input_mode=mode
                        )
                elif is_demo_mode:
                    if "demo_session_id" not in st.session_state:
                        st.session_state["demo_session_id"] = f"DEMO-{uuid.uuid4().hex[:8].upper()}"
                    st.session_state["current_beneficiary_id"] = st.session_state["demo_session_id"]
                
                b_id = st.session_state.get("current_beneficiary_id")
                
                try:
                    # Execute pipeline (handles DB save if not demo, generates recommendations/gaps)
                    results = pipeline.process_verified_profile(confirmed_profile, beneficiary_id=b_id, is_demo=is_demo_mode)
                    
                    st.session_state["beneficiary_step"] = 3
                    
                    # Store results in session state for rendering on recommendations page
                    if "recommendations" not in st.session_state:
                        st.session_state["recommendations"] = {}
                    
                    st.session_state["recommendations"] = {
                        "profile": confirmed_profile,
                        "results": results.get("recommendations", []),
                        "skill_gaps": results.get("skill_gaps", {}),
                        "pathway": results.get("pathway", {})
                    }
                    st.rerun()
                except Exception as e:
                    logger.exception(f"Database or Recommendation pipeline failed: {e}")
                    st.error("⚠️ " + (
                        f"क्षमा करें, आपकी प्रोफ़ाइल सहेजते समय एक तकनीकी समस्या उत्पन्न हुई। कृपया पुनः प्रयास करें। (Error: {e})" if active_lang_code == "hi" else 
                        (f"क्षमस्व, तुमची माहिती जतन करताना काही तांत्रिक अडचण आली. कृपया पुन्हा प्रयत्न करा. (Error: {e})" if active_lang_code == "mr" else 
                        f"Sorry, a technical issue occurred while saving your profile. Please try again. (Error: {e})")
                    ))

    # -------------------------------------------------------------
    # STEP 3: Seamless Transition to Recommendations Page
    # -------------------------------------------------------------
    elif step == 3:
        st.success("✅ " + ("प्रोफ़ाइल सफलतापूर्वक सत्यापित और सहेजी गई! (Profile Verified & Saved to Database)" if active_lang_code == "hi" else ("माहिती यशस्वीरीत्या नोंदवली गेली! (Profile Verified & Saved)" if active_lang_code == "mr" else "Profile Verified & Saved to SQLite Database!")))
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🎯 " + ("सिफ़ारिशें और कौशल मार्ग देखें / View Recommendations" if active_lang_code == "hi" else ("शिफारशी व मार्ग पहा / View Recommendations" if active_lang_code == "mr" else "View My Recommendations Page 🎯")), type="primary", use_container_width=True):
                st.session_state["active_nav"] = "🎯 Recommendations"
                st.rerun()
        with btn_c2:
            if st.button("🔄 " + ("नया साक्षात्कार शुरू करें / New Interview" if active_lang_code == "hi" else ("नवीन मुलाखत सुरू करा / New Interview" if active_lang_code == "mr" else "Start New Interview 🔄")), use_container_width=True):
                restart_interview(active_lang_code)
                st.rerun()

    # -------------------------------------------------------------
    # TASK 10: QUOTA DIAGNOSTICS UI
    # -------------------------------------------------------------
    st.markdown("<hr style='margin: 40px 0 20px 0;'>", unsafe_allow_html=True)
    with st.expander("🛠️ Quota Diagnostics & AI Configuration", expanded=False):
        from config import GEMINI_CHAT_MODEL, GEMINI_TRANSCRIPTION_MODEL, GEMINI_API_KEY
        
        st.write(f"**Chat Model:** `{GEMINI_CHAT_MODEL}`")
        st.write(f"**Transcription Model:** `{GEMINI_TRANSCRIPTION_MODEL}`")
        st.write(f"**API Key Set:** `{'YES' if GEMINI_API_KEY else 'NO'}`")
        st.write(f"**API Calls in Session:** `{st.session_state.get('api_calls', 0)}`")
        st.write(f"**Last API Error:** `{st.session_state.get('last_api_error', 'None')}`")


if __name__ == "__main__":
    st.set_page_config(page_title="Beneficiary Assistant | Kaushal Marg", layout="wide")
    render_beneficiary_page()
