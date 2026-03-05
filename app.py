import streamlit as st
import os
import base64
import tempfile
import pandas as pd
import hmac

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from duckduckgo_search import DDGS


# =====================================
# MODELS (تحسين 1: تقليل التكلفة)
# =====================================

CHAT_MODEL = "gpt-4o-mini"
VISION_MODEL = "gpt-4o"

# =====================================
# FILE LIMIT (تحسين 3)
# =====================================

MAX_FILE_SIZE = 10 * 1024 * 1024


# =====================================
# LOAD ENV
# =====================================

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
PASSWORD = os.getenv("APP_PASSWORD")


# =====================================
# STREAMLIT CONFIG
# =====================================

st.set_page_config(
    page_title="HLAL AI",
    page_icon="🤖",
    layout="wide"
)


# =====================================
# SESSION STATES
# =====================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "auth" not in st.session_state:
    st.session_state.auth = False

if "client" not in st.session_state:
    st.session_state.client = None

if "page" not in st.session_state:
    st.session_state.page = "Chat"

if "pending_files" not in st.session_state:
    st.session_state.pending_files = []

if "mode" not in st.session_state:
    st.session_state.mode = "Coding Assistant"


# =====================================
# SIDEBAR
# =====================================

with st.sidebar:

    st.title("🤖 HLAL AI")

    if not st.session_state.auth:

        method = st.radio(
            "Login Method",
            ["Password", "API Key"]
        )

        pw = st.text_input("Password / API Key", type="password")

        if st.button("Login"):

            if method == "Password":

                if hmac.compare_digest(pw, PASSWORD):

                    st.session_state.client = OpenAI(api_key=API_KEY)
                    st.session_state.auth = True
                    st.rerun()

                else:
                    st.error("Wrong password")

            else:

                if pw.startswith("sk-"):

                    st.session_state.client = OpenAI(api_key=pw)
                    st.session_state.auth = True
                    st.rerun()

                else:
                    st.error("Invalid API key")

        st.stop()

    st.divider()

    if st.button("💬 Chat"):
        st.session_state.page = "Chat"

    if st.button("📷 Camera"):
        st.session_state.page = "Camera"

    if st.button("🎤 Voice"):
        st.session_state.page = "Voice"

    if st.button("🎨 Image"):
        st.session_state.page = "Image"

    if st.button("🔊 TTS"):
        st.session_state.page = "TTS"

    st.divider()

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []

    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.session_state.mode = st.radio(
        "Mode",
        ["Coding Assistant", "Code Reviewer"]
    )


client = st.session_state.client


# =====================================
# WEB SEARCH
# =====================================

def web_search(query):

    results = ""

    with DDGS() as ddgs:
        data = list(ddgs.text(query, max_results=5))

    for r in data:
        results += f"{r['title']} - {r['body']}\n"

    return results


# =====================================
# PDF READER
# =====================================

def read_pdf(file):

    reader = PdfReader(file)

    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return text


# =====================================
# FILE EXTENSION
# =====================================

def get_file_extension(filename):
    return filename.split('.')[-1].lower()


# =====================================
# PROCESS FILES
# =====================================

def process_files(files):

    text_content = ""
    images = []

    for file in files:

        if file.size > MAX_FILE_SIZE:
            text_content += f"\nFile too large: {file.name}"
            continue

        ext = get_file_extension(file.name)

        try:

            if ext == "pdf":

                text = read_pdf(file)
                text_content += f"\n\nPDF {file.name}\n{text[:8000]}"

            elif ext == "docx":

                doc = Document(file)
                text = "\n".join([p.text for p in doc.paragraphs])
                text_content += text

            elif ext == "csv":

                df = pd.read_csv(file)
                text_content += df.head(50).to_string()

            elif ext in ["xlsx", "xls"]:

                df = pd.read_excel(file)
                text_content += df.head(50).to_string()

            elif ext in ["png", "jpg", "jpeg"]:

                file_bytes = file.read()
                base64_img = base64.b64encode(file_bytes).decode()

                mime = "image/jpeg" if ext in ["jpg","jpeg"] else "image/png"

                images.append({
                    "type":"image_url",
                    "image_url":{
                        "url":f"data:{mime};base64,{base64_img}"
                    }
                })

        except Exception as e:

            text_content += f"\nError reading {file.name}: {str(e)}"

    return text_content, images


# =====================================
# SYSTEM PROMPTS
# =====================================

system_prompts = {

    "Coding Assistant":
    "You are an expert coding assistant.",

    "Code Reviewer":
    "You are a senior code reviewer."
}


# =====================================
# CHAT PAGE
# =====================================

if st.session_state.page == "Chat":

    st.title("💬 HLAL AI Chatbot")

    for msg in st.session_state.messages:

        avatar = "🤖" if msg["role"] == "assistant" else "👤"

        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    uploaded = st.file_uploader(
        "Attach files",
        accept_multiple_files=True,
        type=["pdf","docx","csv","xlsx","png","jpg","jpeg"]
    )

    if uploaded:

        for f in uploaded:

            if f not in st.session_state.pending_files:

                st.session_state.pending_files.append(f)
                st.success(f"Uploaded: {f.name}")  # تحسين 5

    user_input = st.chat_input("Ask anything...")

    if user_input:

        text, images = process_files(st.session_state.pending_files)

        prompt = user_input + text

        if "search" in user_input.lower():

            prompt += web_search(user_input)

        st.session_state.messages.append(
            {"role":"user","content":user_input}
        )

        response_text = ""

        with st.chat_message("assistant"):

            placeholder = st.empty()

            try:

                messages = [
                    {"role":"system",
                     "content":system_prompts[st.session_state.mode]}
                ]

                # تحسين 4
                for m in st.session_state.messages[-10:]:
                    messages.append(m)

                if images:

                    messages.append({
                        "role":"user",
                        "content":[
                            {"type":"text","text":prompt}
                        ] + images
                    })

                else:

                    messages.append({
                        "role":"user",
                        "content":prompt
                    })

                stream = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    stream=True,
                    max_tokens=1500
                )

                for chunk in stream:

                    if chunk.choices[0].delta.content:

                        response_text += chunk.choices[0].delta.content
                        placeholder.markdown(response_text)

            except Exception as e:

                st.error(str(e))
                response_text = "Error processing request"

        st.session_state.messages.append(
            {"role":"assistant","content":response_text}
        )

        st.session_state.pending_files = []

        st.rerun()


# =====================================
# CAMERA PAGE
# =====================================

if st.session_state.page == "Camera":

    st.title("📷 Camera Vision")

    img = st.camera_input("Take photo")

    question = st.text_input("Ask about image")

    if img and question:

        bytes_img = img.getvalue()

        base64_img = base64.b64encode(bytes_img).decode()

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role":"user",
                    "content":[
                        {"type":"text","text":question},
                        {
                            "type":"image_url",
                            "image_url":{
                                "url":f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ]
        )

        st.write(response.choices[0].message.content)


# =====================================
# VOICE PAGE
# =====================================

if st.session_state.page == "Voice":

    st.title("🎤 Voice Assistant")

    audio = st.audio_input("Speak")

    if audio:

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio
        )

        user_text = transcript.text

        st.write("You:", user_text)

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role":"user","content":user_text}]
        )

        st.write(response.choices[0].message.content)


# =====================================
# IMAGE GENERATOR
# =====================================

if st.session_state.page == "Image":

    st.title("🎨 Image Generator")

    prompt = st.text_input("Describe image")

    if st.button("Generate"):

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        img = base64.b64decode(result.data[0].b64_json)

        st.image(img)


# =====================================
# TEXT TO SPEECH
# =====================================

if st.session_state.page == "TTS":

    st.title("🔊 Text To Speech")

    text = st.text_area("Enter text")

    if st.button("Generate Voice"):

        speech_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )

        speech.stream_to_file(speech_file.name)

        audio = open(speech_file.name, "rb")

        st.audio(audio.read())
