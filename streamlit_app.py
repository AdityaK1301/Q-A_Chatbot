import streamlit as st
import requests
import time
import base64
import io
from streamlit.components.v1 import html

st.set_page_config(
    page_title="Smart Q/A Tool",
    page_icon="📚",
    layout="wide"
)

# Initialize all session state variables
if 'selected_class' not in st.session_state:
    st.session_state.selected_class = None
if 'selected_subject' not in st.session_state:
    st.session_state.selected_subject = None
if 'syllabus_loaded' not in st.session_state:
    st.session_state.syllabus_loaded = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'listening' not in st.session_state:
    st.session_state.listening = False
if 'voice_answer' not in st.session_state:
    st.session_state.voice_answer = None
if 'speak_buttons_clicked' not in st.session_state:
    st.session_state.speak_buttons_clicked = {}
if 'tts_trigger' not in st.session_state:
    st.session_state.tts_trigger = None

API_BASE_URL = "http://localhost:5000/api"

def speak_text_directly(text):
    """Direct JavaScript TTS without page refresh"""
    if not text:
        return
        
    clean_text = text.replace('"', '\\"').replace("\n", " ").replace("'", "\\'")
    
    js_code = f"""
    <script>
    console.log("Attempting to speak text...");
    if ('speechSynthesis' in window) {{
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();
        
        // Create new speech
        const utterance = new SpeechSynthesisUtterance("{clean_text}");
        utterance.lang = 'en-US';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        // Speak immediately
        window.speechSynthesis.speak(utterance);
        console.log("Speech started successfully");
    }} else {{
        console.log("Speech synthesis not supported");
    }}
    </script>
    """
    html(js_code, height=0)

st.title("📚 Smart Q/A Tool")
st.markdown("Select your class and subject, then ask questions about your syllabus!")

try:
    classes_response = requests.get(f"{API_BASE_URL}/classes")
    subjects_response = requests.get(f"{API_BASE_URL}/subjects")
    
    if classes_response.status_code == 200 and subjects_response.status_code == 200:
        available_classes = classes_response.json()
        available_subjects = subjects_response.json()
    else:
        st.error("Failed to connect to backend. Please make sure the Flask server is running.")
        available_classes = []
        available_subjects = []
except requests.exceptions.ConnectionError:
    st.error("Cannot connect to backend. Please make sure the Flask server is running on port 5000.")
    available_classes = []
    available_subjects = []

col1, col2 = st.columns(2)

with col1:
    selected_class = st.selectbox(
        "Select Your Class",
        options=available_classes,
        index=0 if available_classes else None,
        disabled=not available_classes
    )

with col2:
    selected_subject = st.selectbox(
        "Select Subject",
        options=available_subjects,
        index=0 if available_subjects else None,
        disabled=not available_subjects
    )

if st.button("Load Syllabus", type="primary"):
    if selected_class and selected_subject:
        payload = {
            "class": selected_class,
            "subject": selected_subject
        }
        
        response = requests.post(f"{API_BASE_URL}/select", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "success":
                st.session_state.syllabus_loaded = True
                st.session_state.selected_class = selected_class
                st.session_state.selected_subject = selected_subject
                st.success(result["message"])
            else:
                st.error(result["message"])
        else:
            st.error("Failed to load syllabus. Please try again.")
    else:
        st.error("Please select both class and subject.")

if st.session_state.syllabus_loaded:
    st.divider()
    st.subheader(f"Ask Questions about {st.session_state.selected_class} - {st.session_state.selected_subject}")
    
    for idx, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(chat["question"])
        
        with st.chat_message("assistant"):
            st.write(chat["answer"])
            
            button_key = f"speak_history_{idx}"
            
            if st.button("🔊 Speak Answer", key=button_key):
                speak_text_directly(chat["answer"])
    
    question = st.chat_input("Type your question here...")
    
    if question:
        with st.chat_message("user"):
            st.write(question)
        
        payload = {
            "question": question,
            "use_voice": False
        }
        
        response = requests.post(f"{API_BASE_URL}/ask", json=payload) 
        
        if response.status_code == 200:
            result = response.json()
            answer = result["answer"]
            
            with st.chat_message("assistant"):
                st.write(answer)
                
                if st.button("🔊 Speak Answer", key="speak_new_answer"):
                    st.session_state.tts_trigger = chat["answer"]
                    st.rerun()
            
            st.session_state.chat_history.append({
                "question": question,
                "answer": answer
            })
        else:
            st.error("Failed to get answer. Please try again.")

st.markdown("---")
st.subheader("Voice Input")

voice_input_col1, voice_input_col2 = st.columns([3, 1])

with voice_input_col1:
    if st.button("🎤 Start Voice Input", type="secondary", use_container_width=True):
        st.session_state.listening = True
        listening_placeholder = st.empty()

        with listening_placeholder:
            st.info("🎤 Listening... Please speak your question now")

        payload = {
            "question": "",
            "use_voice": True
        }

        try:
            response = requests.post(f"{API_BASE_URL}/ask", json=payload)
        
            if response.status_code == 200:
                result = response.json()
                voice_question = result.get("voice_input", "")
                is_voice_error = result.get("is_voice_error", False)
            
                listening_placeholder.empty()
            
                if voice_question:
                    if is_voice_error:
                        st.warning(f"Voice recognition: {voice_question}")
                    else:
                        st.success(f"🎤 Recognized: \"{voice_question}\"")
            
                if not is_voice_error and voice_question and not any(x in voice_question.lower() for x in ["error", "sorry", "detected", "couldn't understand"]):
                    with st.chat_message("user"):
                        st.write(voice_question)
                
                    payload = {
                        "question": voice_question,
                        "use_voice": False
                    }
                
                    response = requests.post(f"{API_BASE_URL}/ask", json=payload)
                
                    if response.status_code == 200:
                        result = response.json()
                        answer = result["answer"]
                        
                        st.session_state.voice_answer = answer
                    
                        with st.chat_message("assistant"):
                            st.write(answer)
                            
                            if st.button("🔊 Speak Answer", key="speak_voice_response"):
                                st.session_state.tts_trigger = chat["answer"]
                                st.rerun()
                    
                        st.session_state.chat_history.append({
                            "question": voice_question,
                            "answer": answer
                        })
                    else:
                        st.error("Failed to get answer for voice question. Please try again.")
            else:
                st.error("Failed to process voice input. Please try again.")
            
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend server. Please make sure the Flask server is running.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

        st.session_state.listening = False

if st.session_state.tts_trigger:
    speak_text_directly(st.session_state.tts_trigger)
    st.session_state.tts_trigger = None

with voice_input_col2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.voice_answer = None
        st.session_state.speak_buttons_clicked = {}
        st.rerun()
