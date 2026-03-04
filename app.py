import streamlit as st
import os
import base64
import tempfile
import pandas as pd
import docx 
from docx import Document
import numpy as np
import queue
import soundfile as sf
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from gtts import gTTS
from duckduckgo_search import DDGS
from streamlit_webrtc import webrtc_streamer

# -----------------------------------
# LOAD ENV
# -----------------------------------

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
PASSWORD = os.getenv("APP_PASSWORD")

# -----------------------------------
# STREAMLIT SETTINGS
# -----------------------------------

st.set_page_config(page_title="HLAL AI Chatbot", layout="wide")

# -----------------------------------
# SESSION STATES
# -----------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "auth" not in st.session_state:
    st.session_state.auth = False

if "page" not in st.session_state:
    st.session_state.page = "Chat"

if "client" not in st.session_state:
    st.session_state.client = None

if "pending_files" not in st.session_state:
    st.session_state.pending_files = []

if "login_success" not in st.session_state:
    st.session_state.login_success = False

# -----------------------------------
# LOGIN SYSTEM
# -----------------------------------

if not st.session_state.auth:

    st.title("HLAL AI Chatbot")

    method = st.radio("Login Method", ["Password", "API Key (Optional)"])

    if method == "Password":

        pw = st.text_input("Enter Password", type="password")

        if st.button("Login"):

            if pw == PASSWORD:

                st.session_state.client = OpenAI(api_key=API_KEY)
                st.session_state.auth = True
                st.session_state.login_success = True
                st.rerun()

            else:

                st.error("Wrong password")

    else:

        key = st.text_input("Enter API Key", type="password")

        if st.button("Login with API Key"):

            if key.startswith("sk-"):

                st.session_state.client = OpenAI(api_key=key)
                st.session_state.auth = True
                st.session_state.login_success = True
                st.rerun()

            else:

                st.error("Invalid API key format")

    st.stop()

client = st.session_state.client

if st.session_state.login_success:
    st.success("Connected to HLAL AI")
    st.session_state.login_success = False

# -----------------------------------
# SIDEBAR
# -----------------------------------

with st.sidebar:

    st.title("HLAL AI")

    if st.button("💬 Chat"):
        st.session_state.page = "Chat"

    if st.button("📷 Camera"):
        st.session_state.page = "Camera"

    if st.button("🎨 Image Generation"):
        st.session_state.page = "Image"

    if st.button("🎤 Voice Chat"):
        st.session_state.page = "Voice"

    if st.button("🔊 Text to Speech"):
        st.session_state.page = "TTS"

    if st.button("🌐 Web Search"):
        st.session_state.page = "Search"

    st.divider()

    if st.button("🚪 Sign Out"):
        st.session_state.auth = False
        st.session_state.messages = []
        st.rerun()

# -----------------------------------
# WELCOME MESSAGE
# -----------------------------------

if len(st.session_state.messages) == 0:

    welcome = """
### 🤖 You are welcome in Mr. Wael Hlal Chatbot  
How can I assist you today?

---

### 🤖 اهلا وسهلا بك في روبوت السيد وائل هلال للذكاء الاصطناعي  
كيف يمكنني مساعدتك اليوم؟
"""

    st.session_state.messages.append(
        {"role": "assistant", "content": welcome}
    )

# -----------------------------------
# CHAT PAGE
# -----------------------------------

if st.session_state.page == "Chat":

    st.title("HLAL AI Chatbot")

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []

    for msg in st.session_state.messages:

        avatar = "🤖" if msg["role"] == "assistant" else "👤"

        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # -----------------------------------
    # FILE UPLOAD (WAIT BEFORE SEND)
    # -----------------------------------

    uploaded_files = st.file_uploader(
        "📎 Attach file",
        type=["png", "jpg", "jpeg", "pdf", "docx", "xlsx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        for f in uploaded_files:
            st.session_state.pending_files.append(f)

    # -----------------------------------
    # FILE PREVIEW
    # -----------------------------------

    if st.session_state.pending_files:

        st.markdown("### 📎 Attached files")

        for i, file in enumerate(st.session_state.pending_files):

            col1, col2 = st.columns([8,1])

            with col1:

                if file.type.startswith("image"):
                    st.image(file, width=200)

                else:
                    st.write("📄", file.name)

            with col2:

                if st.button("❌", key=f"remove_{i}"):

                    st.session_state.pending_files.pop(i)
                    st.rerun()

    # -----------------------------------
    # MESSAGE INPUT
    # -----------------------------------

    col1, col2 = st.columns([9,1])

    with col1:
        user_input = st.text_input("Type your message")

    with col2:
        send = st.button("➤")

    if send or user_input:

        content = []

        if user_input:
            content.append({"type":"input_text","text":user_input})

        for file in st.session_state.pending_files:

            if file.type.startswith("image"):

                img = file.read()
                base64_img = base64.b64encode(img).decode()

                content.append({
                    "type":"input_image",
                    "image_url":f"data:image/jpeg;base64,{base64_img}"
                })

            elif file.type == "application/pdf":

                reader = PdfReader(file)
                text=""

                for p in reader.pages:
                    text += p.extract_text()

                content.append({"type":"input_text","text":text})

        response = client.responses.create(
            model="gpt-5.2",
            input=[{"role":"user","content":content}]
        )

        reply = response.output_text

        st.session_state.messages.append(
            {"role":"user","content":user_input if user_input else "📎 File sent"}
        )

        st.session_state.messages.append(
            {"role":"assistant","content":reply}
        )

        st.session_state.pending_files = []

        st.rerun()

# -----------------------------------
# CAMERA PAGE
# -----------------------------------

if st.session_state.page == "Camera":

    st.title("Camera Analysis")

    picture = st.camera_input("Take photo")

    if picture:

        img = picture.read()

        st.image(img)

        base64_img = base64.b64encode(img).decode()

        response = client.responses.create(
            model="gpt-5.2",
            input=[{
                "role":"user",
                "content":[
                    {"type":"input_text","text":"Analyze this image"},
                    {"type":"input_image","image_url":f"data:image/jpeg;base64,{base64_img}"}
                ]
            }]
        )

        st.write(response.output_text)

# -----------------------------------
# IMAGE GENERATION
# -----------------------------------

if st.session_state.page == "Image":

    st.title("Image Generation")

    prompt = st.text_input("Image prompt")

    if st.button("Generate"):

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        img = base64.b64decode(result.data[0].b64_json)

        st.image(img)

# -----------------------------------
# VOICE CHAT
# -----------------------------------

if st.session_state.page == "Voice":

    st.title("Voice Chat")

    audio_queue = queue.Queue()

    def audio_callback(frame):

        audio = frame.to_ndarray()
        audio_queue.put(audio)

        return frame

    webrtc_streamer(
        key="voice",
        audio_frame_callback=audio_callback,
        media_stream_constraints={"audio":True,"video":False}
    )

    if st.button("Process Voice"):

        audio_data=[]

        while not audio_queue.empty():
            audio_data.append(audio_queue.get())

        if len(audio_data)==0:

            st.warning("No audio recorded")

        else:

            audio_np=np.concatenate(audio_data)

            temp_audio=tempfile.NamedTemporaryFile(delete=False,suffix=".wav")

            sf.write(temp_audio.name,audio_np,44100)

            with open(temp_audio.name,"rb") as f:

                transcript=client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=f
                )

            text=transcript.text

            st.write("📝",text)

            response=client.responses.create(
                model="gpt-5.2",
                input=text
            )

            st.write("🤖",response.output_text)

# -----------------------------------
# TEXT TO SPEECH
# -----------------------------------

if st.session_state.page == "TTS":

    st.title("Text to Speech")

    text = st.text_area("Enter text")

    if st.button("Generate Voice"):

        tts = gTTS(text)

        tmp = tempfile.NamedTemporaryFile(delete=False)

        tts.save(tmp.name)

        audio = open(tmp.name,"rb")

        st.audio(audio.read())

# -----------------------------------
# WEB SEARCH
# -----------------------------------

if st.session_state.page == "Search":

    st.title("Web Search")

    query = st.text_input("Search")

    if st.button("Search"):

        with DDGS() as ddgs:

            results=list(ddgs.text(query,max_results=5))

        for r in results:

            st.write("###",r["title"])
            st.write(r["body"])
            st.write(r["href"])