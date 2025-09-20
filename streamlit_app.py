import streamlit as st
import requests
import time
import base64
import io

st.set_page_config(
    page_title="Smart Q/A Tool",
    page_icon="📚",
    layout="wide"
)

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

API_BASE_URL = "http://localhost:5000/api"

def play_audio_base64(audio_base64, format="mp3"):
    """Play base64 encoded audio"""
    audio_bytes = base64.b64decode(audio_base64)
    audio_io = io.BytesIO(audio_bytes)
    st.audio(audio_io, format=f"audio/{format}")

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
    
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(chat["question"])
        
        with st.chat_message("assistant"):
            st.write(chat["answer"])
            
            if st.button("🔊 Speak Answer", key=f"speak_{i}", help="Listen to this answer"):
                with st.spinner("Generating speech..."):
                    try:
                        payload = {"text": chat["answer"]}
                        response = requests.post(f"{API_BASE_URL}/tts", json=payload)
            
                        if response.status_code == 200 and response.headers.get('Content-Type') == 'audio/mpeg':
                            audio_bytes = response.content
                            st.audio(audio_bytes, format="audio/mpeg")
                        else:
                            st.error("Failed to generate speech")
                    except Exception as e:
                        st.error(f"TTS request failed: {str(e)}")
    
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
                
                if st.button("🔊 Speak Answer", key="speak_new"):
                    with st.spinner("Generating speech..."):
                        try:
                            payload = {"text": answer}
                            response = requests.post(f"{API_BASE_URL}/tts", json=payload)  
                            
                            if response.status_code == 200 and response.headers.get('Content-Type') == 'audio/mpeg':
                                audio_bytes = response.content
                                st.audio(audio_bytes, format="audio/mpeg")
                            else:
                                st.error("Failed to generate speech")
                        except Exception as e:
                            st.error(f"TTS request failed: {str(e)}")
            
            st.session_state.chat_history.append({
                "question": question,
                "answer": answer
            })
        else:
            st.error("Failed to get answer. Please try again.")

            
st.markdown("---")
st.subheader("Voice Input")

if st.button("🎤 Start Voice Input", type="secondary"):
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
                
                    with st.chat_message("assistant"):
                        st.write(answer)
                        
                        if st.button("🔊 Speak Answer", key="tts_voice_response"):
                            with st.spinner("Generating speech..."):
                                try:
                                    payload = {"text": answer}
                                    response = requests.post(f"{API_BASE_URL}/tts", json=payload)
            
                                    if response.status_code == 200 and response.headers.get('Content-Type') == 'audio/mpeg':
                                        audio_bytes = response.content
                                        st.audio(audio_bytes, format="audio/mpeg")
                                    else:
                                        st.error("Failed to generate speech")
                                except Exception as e:
                                    st.error(f"TTS error: {str(e)}")
                
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
    
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()